
from pathlib import Path
import io
import json
import sqlite3
import re
import os
import time
import base64
import hmac
import hashlib
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import uuid
import math
from datetime import datetime
from xml.sax.saxutils import escape
from fastapi import (
    FastAPI,
    UploadFile,
    Query,
    HTTPException,
    Depends,
    Form,
    File,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from pydantic import BaseModel

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    UnidentifiedImageError,
)

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as PDFImage,
    PageBreak,
)

from ultralytics import YOLO

from .history import (
    init_db,
    save_inspection,

    get_inspections,
    get_inspection_by_id,
    delete_inspection,
    save_report,
    get_reports,
    get_report_by_id,
    get_report_status_history,
    update_report_status,
    create_citizen,
    get_citizen_by_login,
    verify_citizen_password,
    get_citizen_by_username,
    get_reports_by_citizen,
    get_citizen_profile,
        get_citizen_notifications,
    mark_notification_as_read,

        add_report_support,
    get_report_support_count,
)


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
MODEL_PATH = PROJECT_ROOT / "models" / "best.pt"

ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

MAX_IMAGE_BYTES = 10 * 1024 * 1024

security = HTTPBearer(auto_error=False)

def send_bbmp_notification(report):
    recipient = os.getenv("BBMP_EMAIL")
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD", "").replace(" ", "")
    email_from = os.getenv("EMAIL_FROM")

    # Skip if email configuration is incomplete
    if not all([
        recipient,
        smtp_host,
        smtp_username,
        smtp_password,
        email_from,
    ]):
        print("BBMP email notification skipped: Email configuration missing.")
        return False

    # Get and validate location
    latitude = report.get("latitude")
    longitude = report.get("longitude")

    location = "Location not provided"

    try:
        if latitude is not None and longitude is not None:
            lat = float(latitude)
            lon = float(longitude)

            if lat != 0 or lon != 0:
                location = (
                    f"Latitude: {lat}, "
                    f"Longitude: {lon}"
                )
    except (ValueError, TypeError):
        location = "Location not provided"

    # Get report details
    description = (
        report.get("description") or "No description provided"
    )

    severity = (
        report.get("prediction_status") or "Not available"
    )

    if severity == "no_detections":
        severity = "No damage detections returned by the AI model"

    detection_count = report.get("detection_count", 0)

    submitted_at = report.get("created_at") or "Not available"

    # Create email
    message = EmailMessage()

    message["Subject"] = (
        f"New Verified Road Damage Report - {report['report_id']}"
    )

    message["From"] = email_from
    message["To"] = recipient

    message.set_content(
        f"""
RoadRescue Vision - Verified Road Damage Notification

A road damage report has been verified by the staff.

Report ID: {report['report_id']}
Location: {location}
Severity: {severity}
Description: {description}
Detection Count: {detection_count}
Submitted At: {submitted_at}
Status: Verified

Please review this report for inspection and necessary action.

This is an automated demonstration notification from RoadRescue Vision.
"""
    )

    # Attach the original uploaded road image
    try:
        saved_image_path = report.get("image_path")

        if saved_image_path:
            reports_directory = (
                PROJECT_ROOT / "data" / "reports"
            ).resolve()

            image_path = Path(saved_image_path)

            if not image_path.is_absolute():
                image_path = PROJECT_ROOT / image_path

            image_path = image_path.resolve()

            if (
                image_path.is_relative_to(reports_directory)
                and image_path.is_file()
            ):
                message.add_attachment(
                    image_path.read_bytes(),
                    maintype="image",
                    subtype="jpeg",
                    filename=image_path.name,
                )

                print("Original road image attached to email.")

            else:
                print("Email attachment skipped: Image not found.")

        else:
            print("Email attachment skipped: No image path.")

    except Exception as error:
        print(f"Image attachment failed: {error}")


    # Send email
    try:
        with smtplib.SMTP(
            smtp_host,
            smtp_port,
            timeout=20
        ) as server:

            server.starttls()

            server.login(
                smtp_username,
                smtp_password
            )

            server.send_message(message)

        print(
            f"BBMP demo notification sent for {report['report_id']}"
        )

        return True

    except Exception as error:
        print(f"BBMP email notification failed: {error}")
        return False

# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class StaffLoginRequest(BaseModel):
    username: str
    password: str


class CitizenRegisterRequest(BaseModel):
    full_name: str
    email: str
    username: str
    password: str


class CitizenLoginRequest(BaseModel):
    login: str
    password: str
class DuplicateCheckRequest(BaseModel):
    latitude: float
    longitude: float

# --------------------------------------------------
# TOKEN HELPERS
# --------------------------------------------------

def encode_token_payload(payload):
    payload_bytes = json.dumps(payload).encode("utf-8")

    return base64.urlsafe_b64encode(
        payload_bytes
    ).decode("utf-8").rstrip("=")


def create_token_signature(encoded_payload):
    secret_key = os.getenv("ROADRESCUE_SECRET_KEY")

    if not secret_key:
        raise HTTPException(
            status_code=500,
            detail="Authentication is not configured."
        )

    signature = hmac.new(
        secret_key.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return base64.urlsafe_b64encode(
        signature
    ).decode("utf-8").rstrip("=")


def create_staff_token(username: str):
    payload = {
        "username": username,
        "exp": int(time.time()) + (8 * 60 * 60),
    }

    encoded_payload = encode_token_payload(payload)
    signature = create_token_signature(encoded_payload)

    return f"{encoded_payload}.{signature}"


def create_citizen_token(username: str):
    payload = {
        "username": username,
        "role": "citizen",
        "exp": int(time.time()) + (8 * 60 * 60),
    }

    encoded_payload = encode_token_payload(payload)
    signature = create_token_signature(encoded_payload)

    return f"{encoded_payload}.{signature}"


def decode_and_verify_token(token):
    secret_key = os.getenv("ROADRESCUE_SECRET_KEY")

    if not secret_key:
        raise HTTPException(
            status_code=500,
            detail="Authentication is not configured."
        )

    try:
        encoded_payload, encoded_signature = token.split(".")

        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            encoded_payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        expected_encoded_signature = base64.urlsafe_b64encode(
            expected_signature
        ).decode("utf-8").rstrip("=")

        if not hmac.compare_digest(
            encoded_signature,
            expected_encoded_signature,
        ):
            raise ValueError("Invalid signature")

        padded_payload = encoded_payload + "=" * (
            -len(encoded_payload) % 4
        )

        payload_bytes = base64.urlsafe_b64decode(padded_payload)

        payload = json.loads(
            payload_bytes.decode("utf-8")
        )

        if not isinstance(payload, dict):
            raise ValueError("Invalid payload")

        expiry = payload.get("exp")

        if (
            not isinstance(expiry, (int, float))
            or isinstance(expiry, bool)
            or expiry <= time.time()
        ):
            raise ValueError("Expired token")

        return payload

    except (
        ValueError,
        TypeError,
        KeyError,
        json.JSONDecodeError,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# --------------------------------------------------
# STAFF AUTHENTICATION
# --------------------------------------------------

def get_current_staff(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
    ):
        raise HTTPException(
            status_code=401,
            detail="Staff authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_and_verify_token(
        credentials.credentials
    )

    username = payload.get("username")
    saved_username = os.getenv("ROADRESCUE_STAFF_USERNAME")

    if (
        not username
        or not saved_username
        or username != saved_username
        or payload.get("role") == "citizen"
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid staff token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return username


# --------------------------------------------------
# CITIZEN AUTHENTICATION
# --------------------------------------------------

def get_current_citizen(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
    ):
        raise HTTPException(
            status_code=401,
            detail="Citizen authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_and_verify_token(
        credentials.credentials
    )

    username = payload.get("username")

    if (
        not username
        or payload.get("role") != "citizen"
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid citizen token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return username


# --------------------------------------------------
# APPLICATION SETUP
# --------------------------------------------------

app = FastAPI(
    title="RoadRescue Vision API",
    description="AI-powered road damage detection API",
    version="1.4.0",
)


@app.on_event("startup")
def startup_event():
    init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# MODEL SETUP
# --------------------------------------------------

if not MODEL_PATH.is_file():
    raise FileNotFoundError(
        f"Model checkpoint not found: {MODEL_PATH}"
    )

model = YOLO(str(MODEL_PATH))


# --------------------------------------------------
# IMAGE VALIDATION
# --------------------------------------------------

async def read_image(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Upload a JPG, PNG, or WEBP image.",
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Image size must be 10 MB or less.",
        )

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        image = image.convert("RGB")

    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
    ):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid or supported image.",
        )

    return image


# --------------------------------------------------
# YOLO ROAD DAMAGE DETECTION
# --------------------------------------------------

async def run_prediction(image, conf=0.10):
    results = await run_in_threadpool(
        model.predict,
        source=image,
        imgsz=640,
        conf=conf,
        verbose=False,
    )

    result = results[0]
    detections = []

    if result.boxes is None:
        return detections

    for box in result.boxes:
        class_id = int(box.cls.item())
        confidence = float(box.conf.item())

        x1, y1, x2, y2 = [
            round(float(value), 2)
            for value in box.xyxy[0].tolist()
        ]

        detections.append({
            "class_id": class_id,
            "class_name": model.names[class_id],
            "confidence": round(confidence, 4),
            "box": {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
            },
        })

    return detections


# --------------------------------------------------
# ANNOTATED IMAGE
# --------------------------------------------------

def create_annotated_image(image, detections):
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    font = ImageFont.load_default()

    for detection in detections:
        box = detection["box"]

        x1 = box["x1"]
        y1 = box["y1"]
        x2 = box["x2"]
        y2 = box["y2"]

        draw.rectangle(
            (x1, y1, x2, y2),
            outline="lime",
            width=3,
        )

        label = (
            f'{detection["class_name"]} '
            f'{detection["confidence"]:.1%}'
        )

        draw.text(
            (x1, max(0, y1 - 16)),
            label,
            fill="black",
            font=font,
            stroke_width=2,
            stroke_fill="lime",
        )

    return annotated


# --------------------------------------------------
# STANDARD PREDICTION RESPONSE
# --------------------------------------------------

def build_prediction_response(
    filename,
    image,
    detections,
    conf,
):
    detected = len(detections) > 0
    for detection in detections:
        box = detection["box"]
        box_width = max(0, box["x2"] - box["x1"])
        box_height = max(0, box["y2"] - box["y1"])

        box_area = box_width * box_height
        image_area = image.width * image.height

        detection["area_percentage"] = round(
        (box_area / image_area) * 100,
        2
    )

    return {
        "filename": filename,
        "prediction_status": (
            "damage_detected" if detected else "no_detections"
        ),
        "image_width": image.width,
        "image_height": image.height,
        "confidence_threshold": conf,
        "summary": (
            f"Model returned {len(detections)} detection(s). "
            "Please verify the result visually."
        ),
        "detection_count": len(detections),
        "detections": detections,
        "note": (
            "Predictions are uncertain and require verification."
            if not detected
            else (
                "Model predictions are not a verified "
                "road-safety assessment."
            )
        ),
    }


# --------------------------------------------------
# STAFF LOGIN
# --------------------------------------------------

@app.post("/staff/login")
def staff_login(credentials: StaffLoginRequest):
    saved_username = os.getenv("ROADRESCUE_STAFF_USERNAME")
    saved_password = os.getenv("ROADRESCUE_STAFF_PASSWORD")

    if not saved_username or not saved_password:
        raise HTTPException(
            status_code=500,
            detail="Staff login credentials are not configured.",
        )

    username_valid = hmac.compare_digest(
        credentials.username,
        saved_username,
    )

    password_valid = hmac.compare_digest(
        credentials.password,
        saved_password,
    )

    if not username_valid or not password_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )

    token = create_staff_token(credentials.username)

    return {
        "message": "Staff login successful",
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 28800,
    }


# --------------------------------------------------
# CITIZEN REGISTRATION
# --------------------------------------------------

@app.post("/citizen/register")
def citizen_register(credentials: CitizenRegisterRequest):
    full_name = credentials.full_name.strip()
    email = credentials.email.strip().lower()
    username = credentials.username.strip().lower()
    password = credentials.password

    if not full_name:
        raise HTTPException(
            status_code=400,
            detail="Full name is required.",
        )

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(
            status_code=400,
            detail="Enter a valid email address.",
        )

    if not re.fullmatch(r"[a-z0-9_.]{3,30}", username):
        raise HTTPException(
            status_code=400,
            detail=(
                "Username must be 3â€“30 characters and use "
                "letters, numbers, dots or underscores."
            ),
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters.",
        )

    try:
        create_citizen(
            full_name=full_name,
            email=email,
            username=username,
            password=password,
        )

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="That email or username is already registered.",
        )

    token = create_citizen_token(username)

    return {
        "message": "Citizen account created successfully.",
        "access_token": token,
        "token_type": "bearer",
        "username": username,
        "full_name": full_name,
        "expires_in": 28800,
    }


# --------------------------------------------------
# CITIZEN LOGIN
# --------------------------------------------------

@app.post("/citizen/login")
def citizen_login(credentials: CitizenLoginRequest):
    login = credentials.login.strip().lower()

    if not login or not credentials.password:
        raise HTTPException(
            status_code=400,
            detail="Username/email and password are required.",
        )

    citizen = get_citizen_by_login(login)

    if citizen is None or not verify_citizen_password(
        credentials.password,
        citizen["password_hash"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username/email or password.",
        )

    token = create_citizen_token(citizen["username"])

    return {
        "message": "Citizen login successful.",
        "access_token": token,
        "token_type": "bearer",
        "username": citizen["username"],
        "full_name": citizen["full_name"],
        "expires_in": 28800,
    }


# --------------------------------------------------
# CITIZEN PROFILE
# --------------------------------------------------

@app.get("/citizen/me")
def get_my_profile(
    citizen_username: str = Depends(get_current_citizen),
):
    citizen = get_citizen_profile(citizen_username)

    if citizen is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen profile not found.",
        )

    return citizen

# --------------------------------------------------
# CITIZEN NOTIFICATIONS
# --------------------------------------------------

@app.get("/citizen/notifications")
def get_my_notifications(
    citizen_username: str = Depends(get_current_citizen),
):
    citizen = get_citizen_by_username(citizen_username)

    if citizen is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen account not found.",
        )

    notifications = get_citizen_notifications(
        citizen_id=citizen["id"],
        limit=50,
    )

    unread_count = sum(
        1 for notification in notifications
        if not notification["is_read"]
    )

    return {
        "total": len(notifications),
        "unread_count": unread_count,
        "notifications": notifications,
    }
# --------------------------------------------------
# CITIZEN: MARK NOTIFICATION AS READ
# --------------------------------------------------

@app.patch("/citizen/notifications/{notification_id}/read")
def mark_my_notification_as_read(
    notification_id: int,
    citizen_username: str = Depends(get_current_citizen),
):
    citizen = get_citizen_by_username(citizen_username)

    if citizen is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen account not found.",
        )

    updated = mark_notification_as_read(
        notification_id=notification_id,
        citizen_id=citizen["id"],
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Notification not found.",
        )

    return {
        "message": "Notification marked as read."
    }
# --------------------------------------------------
# CITIZEN DASHBOARD STATISTICS
# --------------------------------------------------

@app.get("/citizen/dashboard")
def get_citizen_dashboard(
    citizen_username: str = Depends(get_current_citizen),
):
    citizen = get_citizen_by_username(citizen_username)

    if citizen is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen account not found.",
        )

    reports = get_reports_by_citizen(
        citizen_id=citizen["id"],
        limit=500,
    )

    total_reports = len(reports)

    resolved = sum(
        1 for report in reports
        if report["status"] == "Resolved"
    )

    pending = sum(
        1 for report in reports
        if report["status"] in {
            "Submitted",
            "Verified",
            "Assigned",
            "In Progress",
        }
    )

    rejected = sum(
        1 for report in reports
        if report["status"] == "Rejected"
    )

    return {
        "total_reports": total_reports,
        "pending_reports": pending,
        "resolved_reports": resolved,
        "rejected_reports": rejected,
        "recent_reports": reports[:5],
    }


# --------------------------------------------------
# CITIZEN MY REPORTS
# --------------------------------------------------

@app.get("/citizen/reports")
def get_my_reports(
    limit: int = Query(default=100, ge=1, le=500),
    citizen_username: str = Depends(get_current_citizen),
):
    citizen = get_citizen_by_username(citizen_username)

    if citizen is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen account not found.",
        )

    reports = get_reports_by_citizen(
        citizen_id=citizen["id"],
        limit=limit,
    )

    return {
        "total": len(reports),
        "reports": reports,
    }


# --------------------------------------------------
# CITIZEN REPORT DETAILS
# --------------------------------------------------

@app.get("/citizen/reports/{report_id}")
def get_my_report_details(
    report_id: str,
    citizen_username: str = Depends(get_current_citizen),
):
    citizen = get_citizen_by_username(citizen_username)

    if citizen is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen account not found.",
        )

    report = get_report_by_id(report_id)

    if (
        report is None
        or report["citizen_id"] != citizen["id"]
    ):
        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    return report

# --------------------------------------------------
# CITIZEN REPORT PROGRESS TIMELINE
# --------------------------------------------------

@app.get("/citizen/reports/{report_id}/timeline")
def get_my_report_timeline(
    report_id: str,
    citizen_username: str = Depends(get_current_citizen),
):
    citizen = get_citizen_by_username(citizen_username)

    if citizen is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen account not found.",
        )

    report = get_report_by_id(report_id)

    if (
        report is None
        or report["citizen_id"] != citizen["id"]
    ):
        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    timeline = get_report_status_history(report_id)

    return {
        "report_id": report_id,
        "current_status": report["status"],
        "timeline": timeline,
    }
# --------------------------------------------------
# CITIZEN REPORT IMAGE
# --------------------------------------------------

# --------------------------------------------------
# CITIZEN: NEARBY ROAD DAMAGE REPORTS
# --------------------------------------------------

@app.get("/citizen/nearby-reports")
def get_nearby_road_reports(
    citizen_username: str = Depends(get_current_citizen),
):
    # Verify the logged-in citizen.
    citizen = get_citizen_by_username(citizen_username)

    if citizen is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen account not found.",
        )

    # Retrieve reports submitted by all citizens.
    all_reports = get_reports(limit=500)

    map_reports = []

    for report in all_reports:
        latitude = report.get("latitude")
        longitude = report.get("longitude")

        # Only include reports with GPS coordinates.
        if latitude is None or longitude is None:
            continue
        if latitude == 0 and longitude == 0:
            continue

        map_reports.append({
            "report_id": report["report_id"],
            "latitude": latitude,
            "longitude": longitude,
            "description": report.get("description"),
            "created_at": report.get("created_at"),
            "status": report.get("status"),
            "detection_count": report.get("detection_count", 0),
            "detections": report.get("detections", []),
            "prediction_status": report.get("prediction_status"),
            "severity": calculate_report_severity(report)
        })

    return {
        "total": len(map_reports),
        "reports": map_reports,
    }

def calculate_report_severity(report):
    detections = report.get("detections") or []

    if not detections:
        return "Not Estimated"

    largest_area = max(
        (
            float(detection.get("area_percentage") or 0)
            for detection in detections
        ),
        default=0,
    )

    if largest_area >= 15:
        return "High"
    if largest_area >= 5:
        return "Medium"
    if largest_area > 0:
        return "Low"

    return "Not Estimated"

@app.get("/citizen/reports/{report_id}/image")
def get_my_report_image(
    report_id: str,
    citizen_username: str = Depends(get_current_citizen),
):
    citizen = get_citizen_by_username(citizen_username)

    if citizen is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen account not found.",
        )

    report = get_report_by_id(report_id)

    if (
        report is None
        or report["citizen_id"] != citizen["id"]
    ):
        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    if not report["image_path"]:
        raise HTTPException(
            status_code=404,
            detail="Report image not found.",
        )

    reports_directory = (
        PROJECT_ROOT / "data" / "reports"
    ).resolve()

    image_path = Path(report["image_path"])

    if not image_path.is_absolute():
        image_path = PROJECT_ROOT / image_path

    image_path = image_path.resolve()

    if not image_path.is_relative_to(reports_directory):
        raise HTTPException(
            status_code=403,
            detail="Invalid report image path.",
        )

    if not image_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Report image not found.",
        )

    return FileResponse(
        path=str(image_path),
        media_type="image/jpeg",
    )
def calculate_distance_m(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two GPS coordinates
    using the Haversine formula.
    """

    earth_radius = 6371000  # metres

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius * c

@app.post("/reports/check-duplicate")
def check_duplicate_reports(
    request: DuplicateCheckRequest,
    citizen_username: str = Depends(get_current_citizen),
):
    # Verify the authenticated citizen
    citizen = get_citizen_by_username(citizen_username)

    if citizen is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen account not found."
        )

    latitude = request.latitude
    longitude = request.longitude

    # Validate GPS coordinates
    if not (-90 <= latitude <= 90):
        raise HTTPException(
            status_code=400,
            detail="Invalid latitude."
        )

    if not (-180 <= longitude <= 180):
        raise HTTPException(
            status_code=400,
            detail="Invalid longitude."
        )

    unresolved_statuses = {
        "Submitted",
        "Verified",
        "Assigned",
        "In Progress",
    }

    matches = []

    # Check recent reports
    existing_reports = get_reports(limit=500)

    for report in existing_reports:

        # Ignore resolved and rejected reports
        if report.get("status") not in unresolved_statuses:
            continue

        # Ignore reports without GPS coordinates
        if (
            report.get("latitude") is None
            or report.get("longitude") is None
        ):
            continue



        distance = calculate_distance_m(
            latitude,
            longitude,
            report["latitude"],
            report["longitude"],
        )

        # Possible duplicate within 50 metres
        if distance <= 50:

            detections = report.get("detections") or []

            largest_area = max(
                (
                    float(d.get("area_percentage") or 0)
                    for d in detections
                ),
                default=0,
            )

            if largest_area >= 15:
                severity = "High"
            elif largest_area >= 5:
                severity = "Medium"
            elif largest_area > 0:
                severity = "Low"
            else:
                severity = "Not Estimated"

            matches.append({
                "report_id": report["report_id"],
                "distance_m": round(distance, 1),
                "status": report["status"],
                "created_at": report["created_at"],
                "description": report.get("description") or "",
                "detection_count": report.get("detection_count", 0),
                "severity": severity,
                "support_count": get_report_support_count(
                    report["report_id"]
                ),
            })

    # Show nearest possible duplicate first
    matches.sort(key=lambda item: item["distance_m"])

    return {
        "has_duplicates": len(matches) > 0,
        "matches": matches,
    }
# --------------------------------------------------
# CITIZEN REPORT SUBMISSION
# --------------------------------------------------

@app.post("/reports")
async def submit_citizen_report(
    file: UploadFile = File(...),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    description: str = Form(default=""),
    citizen_username: str = Depends(get_current_citizen),
):
    # Confirm the authenticated citizen exists.
    citizen = get_citizen_by_username(citizen_username)

    if citizen is None:
        raise HTTPException(
            status_code=401,
            detail="Citizen account not found.",
        )

    # Validate GPS coordinates.
    if latitude is not None and not -90 <= latitude <= 90:
        raise HTTPException(
            status_code=400,
            detail="Invalid latitude.",
        )

    if longitude is not None and not -180 <= longitude <= 180:
        raise HTTPException(
            status_code=400,
            detail="Invalid longitude.",
        )

    # GPS must be supplied as a pair.
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=400,
            detail="Both latitude and longitude are required together.",
        )

    image = await read_image(file)

    detections = await run_prediction(
        image,
        conf=0.10,
    )

    response = build_prediction_response(
        filename=file.filename,
        image=image,
        detections=detections,
        conf=0.10,
    )

    reports_directory = (
        PROJECT_ROOT / "data" / "reports"
    )

    reports_directory.mkdir(
        parents=True,
        exist_ok=True,
    )
    print("PROJECT ROOT:", PROJECT_ROOT)
    print("REPORTS DIRECTORY:", reports_directory.resolve())
    print("DIRECTORY EXISTS:", reports_directory.exists())

    image_filename = f"report_{uuid.uuid4().hex}.jpg"
    image_path = reports_directory / image_filename

    image.save(
        image_path,
        format="JPEG",
        quality=90,
    )
    annotated_image = create_annotated_image(
    image,
    detections,
)
    annotated_filename = f"annotated_{image_filename}"
    annotated_path = reports_directory / annotated_filename
    annotated_image.save(
    annotated_path,
    format="JPEG",
    quality=90,
)

    inspection_id = save_inspection(
        filename=file.filename,
        image_width=image.width,
        image_height=image.height,
        confidence_threshold=0.10,
        detections=detections,
        prediction_status=response["prediction_status"],
    )

    report_id = save_report(
        filename=file.filename,
        image_path=str(image_path.relative_to(PROJECT_ROOT)),
        latitude=latitude,
        longitude=longitude,
        description=description.strip(),
        detection_count=len(detections),
        detections=detections,
        prediction_status=response["prediction_status"],
        inspection_id=inspection_id,
        citizen_id=citizen["id"],
    )

    return {
        "message": "Road damage report submitted successfully.",
        "report_id": report_id,
        "inspection_id": inspection_id,
        "status": "Submitted",
        "filename": file.filename,
        "latitude": latitude,
        "longitude": longitude,
        "description": description.strip(),
        "detection_count": len(detections),
        "detections": detections,
        "prediction_status": response["prediction_status"],
    }


# --------------------------------------------------
# STAFF REPORT IMAGE
# --------------------------------------------------
@app.get("/citizen/reports/{report_id}/annotated-image")
def get_my_annotated_report_image(
    report_id: str,
    citizen_username: str = Depends(get_current_citizen),
):
    citizen = get_citizen_by_username(citizen_username)

    if citizen is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen account not found.",
        )

    report = get_report_by_id(report_id)

    if (
        report is None
        or report["citizen_id"] != citizen["id"]
    ):
        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    if not report["image_path"]:
        raise HTTPException(
            status_code=404,
            detail="Report image not found.",
        )

    reports_directory = (
        PROJECT_ROOT / "data" / "reports"
    ).resolve()

    original_path = Path(report["image_path"])

    if not original_path.is_absolute():
        original_path = PROJECT_ROOT / original_path

    original_path = original_path.resolve()

    if not original_path.is_relative_to(reports_directory):
        raise HTTPException(
            status_code=403,
            detail="Invalid report image path.",
        )

    annotated_path = original_path.with_name(
        f"annotated_{original_path.name}"
    )

    if not annotated_path.is_relative_to(reports_directory):
        raise HTTPException(
            status_code=403,
            detail="Invalid annotated image path.",
        )

    if not annotated_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Annotated image not found.",
        )

    return FileResponse(
        path=str(annotated_path),
        media_type="image/jpeg",
    )
@app.get("/reports/{report_id}/image")
def get_report_image(
    report_id: str,
    staff: str = Depends(get_current_staff),
):
    report = get_report_by_id(report_id)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    if not report["image_path"]:
        raise HTTPException(
            status_code=404,
            detail="Report image not found.",
        )

    reports_directory = (
        PROJECT_ROOT / "data" / "reports"
    ).resolve()

    image_path = Path(report["image_path"])

    if not image_path.is_absolute():
        image_path = PROJECT_ROOT / image_path

    image_path = image_path.resolve()

    if not image_path.is_relative_to(reports_directory):
        raise HTTPException(
            status_code=403,
            detail="Invalid report image path.",
        )

    if not image_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Report image not found.",
        )

    return FileResponse(
        path=str(image_path),
        media_type="image/jpeg",
    )


# --------------------------------------------------
# STAFF: ALL REPORTS
# --------------------------------------------------

@app.get("/reports")
def list_citizen_reports(
    limit: int = Query(default=100, ge=1, le=500),
    staff: str = Depends(get_current_staff),
):
    reports = get_reports(limit=limit)

    for report in reports:
        report["support_count"] = get_report_support_count(
            report["report_id"]
        )

    return {
        "total": len(reports),
        "reports": reports,
    }


# --------------------------------------------------
# STAFF: REPORT DETAILS
# --------------------------------------------------
# --------------------------------------------------
# STAFF: REPORT DETAILS
# --------------------------------------------------

@app.get("/reports/{report_id}")
def get_citizen_report(
    report_id: str,
    staff: str = Depends(get_current_staff),
):
    report = get_report_by_id(report_id)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen report not found.",
        )

    # Get the number of citizens supporting this report.
    report["support_count"] = get_report_support_count(
        report["report_id"]
    )

    return report

# --------------------------------------------------
# STAFF: UPDATE REPORT STATUS
# --------------------------------------------------

@app.patch("/reports/{report_id}/status")
def change_report_status(
    report_id: str,
    status: str = Form(...),
    staff: str = Depends(get_current_staff),
):
    allowed_statuses = {
        "Submitted",
        "Verified",
        "Assigned",
        "In Progress",
        "Resolved",
        "Rejected",
    }

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid report status.",
        )

    updated, should_notify = update_report_status(
        report_id=report_id,
        new_status=status,
        return_transition=True,
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Citizen report not found.",
        )

    notification_status = "not_required"

    if should_notify:
        report = get_report_by_id(report_id)

        if report:
            email_sent = send_bbmp_notification(report)

            notification_status = (
                "sent" if email_sent else "failed"
            )

    return {
        "message": "Report status updated successfully.",
        "report_id": report_id,
        "status": status,
        "email_notification": notification_status,
    }


# --------------------------------------------------
# INSPECTION HISTORY
# --------------------------------------------------

@app.get("/history")
def inspection_history(
    limit: int = Query(default=50, ge=1, le=100),
):
    history = get_inspections(limit=limit)

    return {
        "total": len(history),
        "inspections": history,
    }


@app.get("/history/{inspection_id}")
def inspection_details(inspection_id: int):
    inspection = get_inspection_by_id(inspection_id)

    if inspection is None:
        raise HTTPException(
            status_code=404,
            detail="Inspection not found.",
        )

    return inspection


@app.delete("/history/{inspection_id}")
def remove_inspection(inspection_id: int):
    deleted = delete_inspection(inspection_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Inspection not found.",
        )

    return {
        "message": "Inspection deleted successfully.",
        "inspection_id": inspection_id,
    }


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.post("/reports/{report_id}/support")
def support_existing_report(
    report_id: str,
    citizen_username: str = Depends(get_current_citizen),
):
    citizen = get_citizen_by_username(citizen_username)

    if citizen is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen account not found."
        )

    try:
        added = add_report_support(
            report_id,
            citizen["id"]
        )

        if not added:
            return {
                "success": True,
                "message": "You have already supported this report."
            }

        return {
            "success": True,
            "message": "Your support has been recorded."
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

@app.get("/")
def home():
    return {
        "message": "RoadRescue Vision API is running!",
        "status": "success",
    }


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "project": "RoadRescue Vision",
        "model_loaded": True,
        "classes": model.names,
    }


# --------------------------------------------------
# PREDICT ROAD DAMAGE - JSON
# --------------------------------------------------

@app.post("/predict")
async def predict_road_damage(
    file: UploadFile = File(...),
    conf: float = Query(
        default=0.10,
        ge=0.01,
        le=1.0,
        description="Minimum detection confidence threshold",
    ),
):
    image = await read_image(file)

    detections = await run_prediction(
        image,
        conf=conf,
    )

    response = build_prediction_response(
        filename=file.filename,
        image=image,
        detections=detections,
        conf=conf,
    )

    inspection_id = save_inspection(
        filename=file.filename,
        image_width=image.width,
        image_height=image.height,
        confidence_threshold=conf,
        detections=detections,
        prediction_status=response["prediction_status"],
    )

    response["inspection_id"] = inspection_id

    return response


# --------------------------------------------------
# PREDICT ROAD DAMAGE - ANNOTATED IMAGE
# --------------------------------------------------

@app.post("/predict/visual")
async def predict_road_damage_visual(
    file: UploadFile = File(...),
    conf: float = Query(
        default=0.10,
        ge=0.01,
        le=1.0,
        description="Minimum detection confidence threshold",
    ),
):
    image = await read_image(file)

    detections = await run_prediction(
        image,
        conf=conf,
    )

    annotated = create_annotated_image(
        image,
        detections,
    )

    output = io.BytesIO()
    annotated.save(output, format="PNG")
    output.seek(0)

    metadata = build_prediction_response(
        filename=file.filename,
        image=image,
        detections=detections,
        conf=conf,
    )

    return StreamingResponse(
        output,
        media_type="image/png",
        headers={
            "X-RoadRescue-Metadata": json.dumps(
                metadata,
                separators=(",", ":"),
            ),
            "Content-Disposition": (
                'inline; filename="roadrescue-annotated.png"'
            ),
        },
    )


# --------------------------------------------------
# GENERATE PDF INSPECTION REPORT
# --------------------------------------------------

@app.post("/predict/report")
async def generate_prediction_report(
    file: UploadFile = File(...),
    conf: float = Query(
        default=0.10,
        ge=0.01,
        le=1.0,
        description="Minimum detection confidence threshold",
    ),
):
    image = await read_image(file)

    detections = await run_prediction(
        image,
        conf=conf,
    )

    annotated = create_annotated_image(
        image,
        detections,
    )

    image_buffer = io.BytesIO()
    annotated.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    # PDF colors.
    navy = colors.HexColor("#111827")
    dark = colors.HexColor("#1F2937")
    green = colors.HexColor("#84CC16")
    light = colors.HexColor("#F3F6F2")
    muted = colors.HexColor("#64748B")
    white = colors.white
    border = colors.HexColor("#DCE5D8")

    page_width, page_height = A4

    pdf_buffer = io.BytesIO()

    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=25 * mm,
        bottomMargin=18 * mm,
        title="RoadRescue Vision Inspection Report",
        author="RoadRescue Vision",
    )

    # Header and footer.
    def draw_page_chrome(canvas, doc):
        canvas.saveState()

        canvas.setFillColor(navy)
        canvas.rect(
            0,
            page_height - 18 * mm,
            page_width,
            18 * mm,
            fill=1,
            stroke=0,
        )

        canvas.setFillColor(green)
        canvas.rect(
            0,
            page_height - 18 * mm,
            4 * mm,
            18 * mm,
            fill=1,
            stroke=0,
        )

        canvas.setFillColor(white)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(
            18 * mm,
            page_height - 11.5 * mm,
            "ROADRESCUE VISION",
        )

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#CBD5E1"))
        canvas.drawRightString(
            page_width - 18 * mm,
            page_height - 11.5 * mm,
            "AI ROAD INSPECTION",
        )

        canvas.setStrokeColor(
            colors.HexColor("#D9E0E5")
        )

        canvas.line(
            18 * mm,
            13 * mm,
            page_width - 18 * mm,
            13 * mm,
        )

        canvas.setFillColor(muted)
        canvas.setFont("Helvetica", 7.5)

        canvas.drawString(
            18 * mm,
            8.5 * mm,
            "AI-generated results | Visual verification required",
        )

        canvas.drawRightString(
            page_width - 18 * mm,
            8.5 * mm,
            f"Page {doc.page}",
        )

        canvas.restoreState()

    # Text styles.
    title_style = ParagraphStyle(
        "ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=navy,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=muted,
    )

    section_style = ParagraphStyle(
        "Section",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=navy,
        spaceBefore=3,
        spaceAfter=6,
    )

    normal_style = ParagraphStyle(
        "NormalCustom",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=dark,
    )

    small_style = ParagraphStyle(
        "SmallCustom",
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=muted,
    )

    card_style = ParagraphStyle(
        "Card",
        fontName="Helvetica",
        fontSize=19,
        leading=23,
        textColor=white,
        alignment=TA_CENTER,
    )

    card_label_style = ParagraphStyle(
        "CardLabel",
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#CBD5E1"),
        alignment=TA_CENTER,
    )

    story = []

    # PAGE 1: REPORT OVERVIEW

    story.append(
        Paragraph("Road Inspection Report", title_style)
    )

    story.append(
        Paragraph(
            "AI-assisted road damage detection and visual analysis",
            subtitle_style,
        )
    )

    story.append(Spacer(1, 8))

    filename = escape(file.filename or "uploaded_image")

    report_date = datetime.now().astimezone().strftime(
        "%d %B %Y | %I:%M %p"
    )

    metadata_data = [
        [
            Paragraph("<b>IMAGE FILE</b>", small_style),
            Paragraph("<b>REPORT GENERATED</b>", small_style),
        ],
        [
            Paragraph(filename, normal_style),
            Paragraph(report_date, normal_style),
        ],
        [
            Paragraph("<b>IMAGE DIMENSIONS</b>", small_style),
            Paragraph("<b>CONFIDENCE THRESHOLD</b>", small_style),
        ],
        [
            Paragraph(
                f"{image.width} Ã— {image.height} pixels",
                normal_style,
            ),
            Paragraph(f"{conf:.0%}", normal_style),
        ],
    ]

    metadata_table = Table(
        metadata_data,
        colWidths=[87 * mm, 87 * mm],
    )

    metadata_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), light),
            ("BOX", (0, 0), (-1, -1), 0.6, border),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    story.append(metadata_table)
    story.append(Spacer(1, 9))

    class_counts = {}

    for detection in detections:
        class_name = detection["class_name"]

        class_counts[class_name] = (
            class_counts.get(class_name, 0) + 1
        )

    class_count = len(class_counts)

    summary_data = [[
        [
            Paragraph(
                f'<font color="#84CC16"><b>{len(detections)}</b></font>',
                card_style,
            ),
            Paragraph("TOTAL DETECTIONS", card_label_style),
        ],
        [
            Paragraph(
                f'<font color="#84CC16"><b>{class_count}</b></font>',
                card_style,
            ),
            Paragraph("DETECTED CLASSES", card_label_style),
        ],
        [
            Paragraph(
                f'<font color="#84CC16"><b>{conf:.0%}</b></font>',
                card_style,
            ),
            Paragraph("CONFIDENCE FILTER", card_label_style),
        ],
    ]]

    summary_table = Table(
        summary_data,
        colWidths=[58 * mm, 58 * mm, 58 * mm],
        rowHeights=[21 * mm],
    )

    summary_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), navy),
            ("BOX", (0, 0), (-1, -1), 0.5, navy),
            ("INNERGRID", (0, 0), (-1, -1), 1, dark),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
    )

    story.append(summary_table)
    story.append(Spacer(1, 10))

    story.append(
        Paragraph("Annotated Road Image", section_style)
    )

    story.append(
        Paragraph(
            "Green boxes show the locations returned by the detection model.",
            small_style,
        )
    )

    story.append(Spacer(1, 5))

    pdf_image = PDFImage(image_buffer)

    max_image_width = 174 * mm
    max_image_height = 78 * mm

    image_scale = min(
        max_image_width / image.width,
        max_image_height / image.height,
    )

    pdf_image.drawWidth = image.width * image_scale
    pdf_image.drawHeight = image.height * image_scale

    story.append(pdf_image)
    story.append(Spacer(1, 6))

    if class_counts:
        distribution = " | ".join(
            f"{name}: {count}"
            for name, count in sorted(class_counts.items())
        )
    else:
        distribution = "No detections returned"

    story.append(
        Paragraph(
            f"<b>Class distribution:</b> {escape(distribution)}",
            small_style,
        )
    )

    # PAGE 2: DETECTION DETAILS

    story.append(PageBreak())

    story.append(
        Paragraph("Detection Details", title_style)
    )

    story.append(
        Paragraph(
            "Individual model predictions and bounding-box coordinates",
            subtitle_style,
        )
    )

    story.append(Spacer(1, 12))

    table_data = [[
        "CLASS",
        "CONFIDENCE",
        "X1",
        "Y1",
        "X2",
        "Y2",
    ]]

    for detection in detections:
        box = detection["box"]

        table_data.append([
            detection["class_name"],
            f'{detection["confidence"]:.1%}',
            f'{box["x1"]:.1f}',
            f'{box["y1"]:.1f}',
            f'{box["x2"]:.1f}',
            f'{box["y2"]:.1f}',
        ])

    if not detections:
        table_data.append([
            "No detections",
            "-",
            "-",
            "-",
            "-",
            "-",
        ])

    details_table = Table(
        table_data,
        colWidths=[
            30 * mm,
            30 * mm,
            28.5 * mm,
            28.5 * mm,
            28.5 * mm,
            28.5 * mm,
        ],
        repeatRows=1,
    )

    details_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), navy),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 1), (-1, -1), dark),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, light]),
            ("GRID", (0, 0), (-1, -1), 0.4,
             colors.HexColor("#D5DCE3")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])
    )

    story.append(details_table)
    story.append(Spacer(1, 16))

    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=normal_style,
        fontSize=8,
        leading=12,
    )

    disclaimer = Table(
        [[
            Paragraph(
                "<b>IMPORTANT â€” MODEL LIMITATION</b><br/><br/>"
                "This report contains AI-generated predictions. "
                "Predictions may be incorrect or incomplete and must "
                "be visually verified. Bounding boxes and class labels "
                "are model outputs, not confirmed measurements or a "
                "verified road-safety assessment.",
                disclaimer_style,
            )
        ]],
        colWidths=[174 * mm],
    )

    disclaimer.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), light),
            ("BOX", (0, 0), (-1, -1), 1, green),
            ("LEFTPADDING", (0, 0), (-1, -1), 11),
            ("RIGHTPADDING", (0, 0), (-1, -1), 11),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ])
    )

    story.append(disclaimer)

    document.build(
        story,
        onFirstPage=draw_page_chrome,
        onLaterPages=draw_page_chrome,
    )

    pdf_buffer.seek(0)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                'attachment; filename="roadrescue-inspection-report.pdf"'
            )
        },
    )
