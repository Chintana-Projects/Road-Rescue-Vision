
from pathlib import Path
import csv
import cv2
import numpy as np
import math

# --------------------------------------------------
# PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET = PROJECT_ROOT / "data" / "raw" / "RDD-India"

BASE = Path(__file__).resolve().parent

PILOT_CSV = BASE / "annotations" / "severity_pilot.csv"

OUTPUT_DIR = BASE / "results" / "pilot_alignment"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLASSES = {
    0: "D00",
    1: "D20",
    2: "D40",
    3: "D44"
}

# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

PANEL_WIDTH = 420
PANEL_HEIGHT = 320

CANVAS_WIDTH = 900
CANVAS_HEIGHT = 380

# --------------------------------------------------
# RESIZE IMAGE WITHOUT DISTORTING IT
# --------------------------------------------------

def resize_to_fit(image, target_width, target_height):

    height, width = image.shape[:2]

    scale = min(
        target_width / width,
        target_height / height
    )

    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))

    resized = cv2.resize(
        image,
        (new_width, new_height)
    )

    canvas = np.full(
        (target_height, target_width, 3),
        255,
        dtype=np.uint8
    )

    x = (target_width - new_width) // 2
    y = (target_height - new_height) // 2

    canvas[
        y:y + new_height,
        x:x + new_width
    ] = resized

    return canvas


# --------------------------------------------------
# BUILD SOURCE IMAGE LOOKUP
# --------------------------------------------------

image_dir = DATASET / "train" / "images"
label_dir = DATASET / "train" / "labels"

image_lookup = {
    path.stem: path
    for path in image_dir.iterdir()
    if path.suffix.lower() in [".jpg", ".jpeg", ".png"]
}

# Maps generated crop filename to its original annotation
source_lookup = {}

for label_file in label_dir.glob("*.txt"):

    image_path = image_lookup.get(label_file.stem)

    if image_path is None:
        continue

    with open(label_file, "r", encoding="utf-8") as file:
        lines = file.readlines()

    for index, line in enumerate(lines):

        values = line.strip().split()

        if len(values) != 5:
            continue

        try:
            class_id, xc, yc, bw, bh = map(float, values)
        except ValueError:
            continue

        class_id = int(class_id)

        if class_id not in CLASSES:
            continue

        crop_name = f"{label_file.stem}_{index}.jpg"

        source_lookup[crop_name] = {
            "image_path": image_path,
            "class_id": class_id,
            "xc": xc,
            "yc": yc,
            "bw": bw,
            "bh": bh
        }

# --------------------------------------------------
# LOAD EXACT PILOT SAMPLES
# --------------------------------------------------

with open(PILOT_CSV, "r", newline="", encoding="utf-8") as file:
    pilot_rows = list(csv.DictReader(file))

print("\nPILOT ALIGNMENT INSPECTION")

print("Pilot samples:", len(pilot_rows))

comparison_images = []
successful = 0

# --------------------------------------------------
# PROCESS EACH PILOT SAMPLE
# --------------------------------------------------

for sample_number, row in enumerate(pilot_rows, start=1):

    crop_name = row["crop_name"]
    class_name = row["damage_class"]
    crop_path = Path(row["crop_path"])

    source = source_lookup.get(crop_name)

    if source is None:
        print("Source annotation not found:", crop_name)
        continue

    if CLASSES[source["class_id"]] != class_name:
        print("Class mismatch:", crop_name)
        continue

    original = cv2.imread(str(source["image_path"]))
    expanded = cv2.imread(str(crop_path))

    if original is None or expanded is None:
        print("Could not read image:", crop_name)
        continue

    height, width = original.shape[:2]

    # Original YOLO normalized coordinates
    xc = source["xc"]
    yc = source["yc"]
    bw = source["bw"]
    bh = source["bh"]

    # Convert normalized coordinates to pixels
    x1 = int((xc - bw / 2) * width)
    y1 = int((yc - bh / 2) * height)

    x2 = int((xc + bw / 2) * width)
    y2 = int((yc + bh / 2) * height)

    # Keep coordinates within image boundaries
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(0, min(x2, width))
    y2 = max(0, min(y2, height))

    box_width = x2 - x1
    box_height = y2 - y1

    # Draw ground-truth bounding box
    annotated = original.copy()

    cv2.rectangle(
        annotated,
        (x1, y1),
        (x2, y2),
        (0, 0, 255),
        2
    )

    # Prepare both panels
    original_panel = resize_to_fit(
        annotated,
        PANEL_WIDTH,
        PANEL_HEIGHT
    )

    expanded_panel = resize_to_fit(
        expanded,
        PANEL_WIDTH,
        PANEL_HEIGHT
    )

    # Create comparison canvas
    comparison = np.full(
        (CANVAS_HEIGHT, CANVAS_WIDTH, 3),
        255,
        dtype=np.uint8
    )

    comparison[45:365, 15:435] = original_panel
    comparison[45:365, 465:885] = expanded_panel

    # Headings
    cv2.putText(
        comparison,
        "Original + YOLO Ground Truth",
        (15, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 0, 0),
        2
    )

    cv2.putText(
        comparison,
        "Expanded Crop",
        (465, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 0, 0),
        2
    )

    # Dimensions and class
    crop_height, crop_width = expanded.shape[:2]

    information = (
        f"{sample_number}. {class_name} | "
        f"Original box: {box_width}x{box_height} | "
        f"Expanded crop: {crop_width}x{crop_height}"
    )

    cv2.putText(
        comparison,
        information,
        (15, 377),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (0, 0, 0),
        1
    )

    # Save individual comparison
    output_path = OUTPUT_DIR / f"sample_{sample_number:02d}_{class_name}.jpg"

    cv2.imwrite(str(output_path), comparison)

    comparison_images.append(comparison)

    successful += 1

    print("Saved:", output_path.name)

# --------------------------------------------------
# CREATE CONTACT SHEET
# --------------------------------------------------

if comparison_images:

    columns = 2
    rows = math.ceil(len(comparison_images) / columns)

    sheet = np.full(
        (rows * CANVAS_HEIGHT, columns * CANVAS_WIDTH, 3),
        255,
        dtype=np.uint8
    )

    for index, comparison in enumerate(comparison_images):

        row_index = index // columns
        col_index = index % columns

        sheet[
            row_index * CANVAS_HEIGHT:
            (row_index + 1) * CANVAS_HEIGHT,

            col_index * CANVAS_WIDTH:
            (col_index + 1) * CANVAS_WIDTH
        ] = comparison

    sheet_path = OUTPUT_DIR / "severity_pilot_alignment_sheet.jpg"

    cv2.imwrite(str(sheet_path), sheet)

    print("\nALIGNMENT INSPECTION COMPLETED")
    print("Successful comparisons:", successful)
    print("Contact sheet:", sheet_path)

else:
    print("\nNo comparison images were generated.")
