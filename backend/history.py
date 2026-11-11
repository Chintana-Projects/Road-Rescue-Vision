
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
import os
import hashlib
import hmac

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_DIRECTORY = PROJECT_ROOT / "data" / "history"
DB_DIRECTORY.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIRECTORY / "inspection_history.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:

        # Existing inspection history table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL,
                image_width INTEGER,
                image_height INTEGER,
                confidence_threshold REAL,
                detection_count INTEGER,
                detections TEXT,
                prediction_status TEXT,
                latitude REAL,
                longitude REAL
            )
        """)

        # Citizen accounts table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS citizens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Add GPS columns to existing inspection databases
        existing_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(inspections)"
            ).fetchall()
        }

        if "latitude" not in existing_columns:
            conn.execute(
                "ALTER TABLE inspections ADD COLUMN latitude REAL"
            )

        if "longitude" not in existing_columns:
            conn.execute(
                "ALTER TABLE inspections ADD COLUMN longitude REAL"
            )

        # Citizen road reports table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT UNIQUE NOT NULL,
                citizen_id INTEGER,
                inspection_id INTEGER,
                filename TEXT NOT NULL,
                image_path TEXT,
                created_at TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                description TEXT,
                detection_count INTEGER DEFAULT 0,
                detections TEXT,
                prediction_status TEXT,
                status TEXT DEFAULT 'Submitted'
            )
        """)

        # Add citizen ownership to existing reports databases
        report_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(reports)"
            ).fetchall()
        }

        if "citizen_id" not in report_columns:
            conn.execute(
                "ALTER TABLE reports ADD COLUMN citizen_id INTEGER"
            )

        # Report status history table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS report_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                changed_at TEXT NOT NULL
            )
        """)
                # Citizens supporting existing road reports
        conn.execute("""
            CREATE TABLE IF NOT EXISTS report_supports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT NOT NULL,
                citizen_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(report_id, citizen_id)
            )
        """)
                # Citizen in-app notifications
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                citizen_id INTEGER NOT NULL,
                report_id TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_citizen
            ON notifications(citizen_id, is_read)
        """)

        # Index for faster support count lookup
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_report_supports_report_id
            ON report_supports(report_id)
        """)

        # Add initial history entries for existing reports
        conn.execute("""
            INSERT INTO report_status_history (
                report_id,
                old_status,
                new_status,
                changed_at
            )
            SELECT
                r.report_id,
                NULL,
                'Submitted',
                r.created_at
            FROM reports r
            WHERE NOT EXISTS (
                SELECT 1
                FROM report_status_history h
                WHERE h.report_id = r.report_id
            )
        """)


def save_report(
    filename,
    image_path,
    latitude,
    longitude,
    description,
    detection_count,
    detections,
    prediction_status,
    inspection_id=None,
    citizen_id=None,
):
    with get_connection() as conn:

        created_at = datetime.now(timezone.utc).isoformat()

        # Insert the report first
        cursor = conn.execute(
            """
            INSERT INTO reports (
                report_id,
                citizen_id,
                inspection_id,
                filename,
                image_path,
                created_at,
                latitude,
                longitude,
                description,
                detection_count,
                detections,
                prediction_status,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"TEMP-{datetime.now(timezone.utc).timestamp()}",
                citizen_id,
                inspection_id,
                filename,
                image_path,
                created_at,
                latitude,
                longitude,
                description,
                detection_count,
                json.dumps(detections),
                prediction_status,
                "Submitted",
            ),
        )

        report_db_id = cursor.lastrowid

        report_id = (
            f"RR-{datetime.now(timezone.utc).year}-{report_db_id:05d}"
        )

        conn.execute(
            """
            UPDATE reports
            SET report_id = ?
            WHERE id = ?
            """,
            (report_id, report_db_id),
        )

        # Record initial Submitted status
        conn.execute(
            """
            INSERT INTO report_status_history (
                report_id,
                old_status,
                new_status,
                changed_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                report_id,
                None,
                "Submitted",
                created_at,
            ),
        )

        return report_id


def get_reports(limit=100):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT *
            FROM reports
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        reports = []

        for row in rows:
            item = dict(row)
            item["detections"] = json.loads(
                item["detections"] or "[]"
            )
            reports.append(item)

        return reports


def get_report_by_id(report_id):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            """
            SELECT *
            FROM reports
            WHERE report_id = ?
            """,
            (report_id,),
        ).fetchone()

        if row is None:
            return None

        report = dict(row)

        report["detections"] = json.loads(
            report["detections"] or "[]"
        )

        return report

def get_report_status_history(report_id):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                old_status,
                new_status,
                changed_at
            FROM report_status_history
            WHERE report_id = ?
            ORDER BY id ASC
            """,
            (report_id,),
        ).fetchall()

        return [dict(row) for row in rows]

def update_report_status(report_id, new_status, return_transition=False):

    allowed_statuses = {
        "Submitted",
        "Verified",
        "Assigned",
        "In Progress",
        "Resolved",
        "Rejected",
    }

    if new_status not in allowed_statuses:
        raise ValueError("Invalid report status")

    with get_connection() as conn:

        # Get current report status
        row = conn.execute(
            """
            SELECT status, citizen_id
FROM reports
WHERE report_id = ?
            """,
            (report_id,),
        ).fetchone()

        if row is None:
            return (False, False) if return_transition else False

        old_status = row[0]
        citizen_id = row[1]

        # Avoid duplicate history entries
        if old_status == new_status:
            return (True, False) if return_transition else True

        # Check whether this report was verified previously
        already_verified = conn.execute(
            """
            SELECT 1
            FROM report_status_history
            WHERE report_id = ?
              AND new_status = 'Verified'
            LIMIT 1
            """,
            (report_id,),
        ).fetchone() is not None

        # Notify only on the first-ever verification
        should_notify = (
            new_status == "Verified"
            and not already_verified
        )

        changed_at = datetime.now(timezone.utc).isoformat()

        # Update current report status
        conn.execute(
            """
            UPDATE reports
            SET status = ?
            WHERE report_id = ?
            """,
            (new_status, report_id),
        )

        # Save status change history
        conn.execute(
            """
            INSERT INTO report_status_history (
                report_id,
                old_status,
                new_status,
                changed_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                report_id,
                old_status,
                new_status,
                changed_at,
            ),
        )
                # Create an in-app notification for the report owner
        if citizen_id is not None:

            notification_messages = {
                "Verified": (
                    "Report Verified",
                    f"Your road damage report {report_id} has been verified."
                ),
                "Assigned": (
                    "Report Assigned",
                    f"Your report {report_id} has been assigned for inspection."
                ),
                "In Progress": (
                    "Work In Progress",
                    f"Work has started on your report {report_id}."
                ),
                "Resolved": (
                    "Report Resolved",
                    f"Your road damage report {report_id} has been resolved."
                ),
                "Rejected": (
                    "Report Rejected",
                    f"Your road damage report {report_id} has been rejected."
                ),
                "Submitted": (
                    "Report Submitted",
                    f"Your road damage report {report_id} has been submitted."
                ),
            }

            title, message = notification_messages[new_status]

            conn.execute(
                """
                INSERT INTO notifications (
                    citizen_id,
                    report_id,
                    title,
                    message,
                    is_read,
                    created_at
                )
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (
                    citizen_id,
                    report_id,
                    title,
                    message,
                    changed_at,
                ),
            )

        if return_transition:
            return True, should_notify

        return True
def save_inspection(
    filename,
    image_width,
    image_height,
    confidence_threshold,
    detections,
    prediction_status
):
    with get_connection() as conn:

        cursor = conn.execute("""
            INSERT INTO inspections (
                filename,
                created_at,
                image_width,
                image_height,
                confidence_threshold,
                detection_count,
                detections,
                prediction_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            filename,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            image_width,
            image_height,
            confidence_threshold,
            len(detections),
            json.dumps(detections),
            prediction_status
        ))

        return cursor.lastrowid


def get_inspections(limit=50):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT *
            FROM inspections
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        history = []

        for row in rows:
            item = dict(row)
            item["detections"] = json.loads(
                item["detections"] or "[]"
            )
            history.append(item)

        return history


def get_inspection_by_id(inspection_id):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute("""
            SELECT *
            FROM inspections
            WHERE id = ?
        """, (inspection_id,)).fetchone()

        if row is None:
            return None

        item = dict(row)

        item["detections"] = json.loads(
            item["detections"] or "[]"
        )

        return item


def delete_inspection(inspection_id):
    with get_connection() as conn:
        cursor = conn.execute("""
            DELETE FROM inspections
            WHERE id = ?
        """, (inspection_id,))

        return cursor.rowcount > 0


def hash_citizen_password(password):
    salt = os.urandom(16)

    password_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1
    )

    return f"{salt.hex()}:{password_hash.hex()}"


def verify_citizen_password(password, stored_hash):
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)

        password_hash = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=16384,
            r=8,
            p=1
        )

        return hmac.compare_digest(
            password_hash.hex(),
            hash_hex
        )

    except (ValueError, TypeError):
        return False


def create_citizen(full_name, email, username, password):
    with get_connection() as conn:

        cursor = conn.execute(
            """
            INSERT INTO citizens (
                full_name,
                email,
                username,
                password_hash,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                full_name,
                email.lower(),
                username,
                hash_citizen_password(password),
                datetime.now(timezone.utc).isoformat()
            )
        )

        return cursor.lastrowid


def get_citizen_by_login(login):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        citizen = conn.execute(
            """
            SELECT *
            FROM citizens
            WHERE username = ? OR email = ?
            """,
            (login, login.lower())
        ).fetchone()

        return dict(citizen) if citizen else None


def get_citizen_by_username(username):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        citizen = conn.execute(
            """
            SELECT id, full_name, email, username, created_at
            FROM citizens
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        return dict(citizen) if citizen else None


def get_reports_by_citizen(citizen_id, limit=100):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT *
            FROM reports
            WHERE citizen_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (citizen_id, limit)
        ).fetchall()

        reports = []

        for row in rows:
            item = dict(row)

            item["detections"] = json.loads(
                item["detections"] or "[]"
            )

            reports.append(item)

        return reports


def get_citizen_profile(username):
    return get_citizen_by_username(username)

def add_report_support(report_id, citizen_id):
    with get_connection() as conn:

        # Check whether the report exists
        report = conn.execute(
            """
            SELECT citizen_id
            FROM reports
            WHERE report_id = ?
            """,
            (report_id,)
        ).fetchone()

        if report is None:
            raise ValueError("Report not found")

        # Citizens cannot support their own reports
        if report[0] == citizen_id:
            raise ValueError("You cannot support your own report")

        # Check whether this citizen has already supported it
        existing = conn.execute(
            """
            SELECT id
            FROM report_supports
            WHERE report_id = ? AND citizen_id = ?
            """,
            (report_id, citizen_id)
        ).fetchone()

        if existing:
            return False

        conn.execute(
            """
            INSERT INTO report_supports (
                report_id,
                citizen_id,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                report_id,
                citizen_id,
                datetime.now(timezone.utc).isoformat()
            )
        )

        return True


def get_report_support_count(report_id):
    with get_connection() as conn:

        result = conn.execute(
            """
            SELECT COUNT(*)
            FROM report_supports
            WHERE report_id = ?
            """,
            (report_id,)
        ).fetchone()

        return result[0]
def get_citizen_notifications(citizen_id, limit=50):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                id,
                report_id,
                title,
                message,
                is_read,
                created_at
            FROM notifications
            WHERE citizen_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (citizen_id, limit)
        ).fetchall()

        return [dict(row) for row in rows]
def mark_notification_as_read(notification_id, citizen_id):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE id = ? AND citizen_id = ?
            """,
            (notification_id, citizen_id),
        )

        return cursor.rowcount > 0