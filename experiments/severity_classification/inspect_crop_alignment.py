
from pathlib import Path
import cv2
import numpy as np
import random
import math

# --------------------------------------------------
# PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET = PROJECT_ROOT / "data" / "raw" / "RDD-India"

BASE = Path(__file__).resolve().parent

EXPANDED_CROPS = BASE / "expanded_crops"

OUTPUT = BASE / "results" / "crop_alignment"

OUTPUT.mkdir(parents=True, exist_ok=True)

CLASSES = {
    0: "D00",
    1: "D20",
    2: "D40",
    3: "D44"
}

SPLIT = "valid"
SAMPLES_PER_CLASS = 2

random.seed(42)


# --------------------------------------------------
# IMAGE RESIZING FUNCTION
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
# LOAD VALIDATION DATASET
# --------------------------------------------------

image_dir = DATASET / SPLIT / "images"
label_dir = DATASET / SPLIT / "labels"

image_lookup = {
    path.stem: path
    for path in image_dir.iterdir()
    if path.suffix.lower() in [".jpg", ".jpeg", ".png"]
}

candidates = {
    class_id: []
    for class_id in CLASSES
}


# --------------------------------------------------
# FIND DAMAGE ANNOTATIONS
# --------------------------------------------------

for label_file in label_dir.glob("*.txt"):

    image_path = image_lookup.get(label_file.stem)

    if image_path is None:
        continue

    with open(label_file, "r") as file:
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

        candidates[class_id].append(
            (label_file, image_path, index, xc, yc, bw, bh)
        )


# --------------------------------------------------
# SELECT SAMPLES
# --------------------------------------------------

comparison_images = []

for class_id, class_name in CLASSES.items():

    available = candidates[class_id]

    selected = random.sample(
        available,
        min(SAMPLES_PER_CLASS, len(available))
    )

    print(f"\n{class_name}: {len(selected)} samples selected")

    for sample_number, item in enumerate(selected, start=1):

        label_file, image_path, index, xc, yc, bw, bh = item

        original = cv2.imread(str(image_path))

        if original is None:
            continue

        height, width = original.shape[:2]

        # Convert normalized YOLO coordinates to pixels
        x_center = xc * width
        y_center = yc * height

        box_width = bw * width
        box_height = bh * height

        x1 = max(0, int(x_center - box_width / 2))
        y1 = max(0, int(y_center - box_height / 2))

        x2 = min(width, int(x_center + box_width / 2))
        y2 = min(height, int(y_center + box_height / 2))

        # Draw original ground-truth bounding box
        annotated = original.copy()

        cv2.rectangle(
            annotated,
            (x1, y1),
            (x2, y2),
            (0, 0, 255),
            2
        )

        # Find corresponding expanded crop
        crop_name = f"{label_file.stem}_{index}.jpg"

        crop_path = (
            EXPANDED_CROPS
            / SPLIT
            / class_name
            / crop_name
        )

        if not crop_path.exists():
            print("Missing expanded crop:", crop_name)
            continue

        expanded = cv2.imread(str(crop_path))

        if expanded is None:
            continue

        crop_height, crop_width = expanded.shape[:2]

        # Prepare comparison panels
        original_panel = resize_to_fit(
            annotated, 420, 300
        )

        expanded_panel = resize_to_fit(
            expanded, 420, 300
        )

        # Create comparison canvas
        comparison = np.full(
            (360, 900, 3),
            255,
            dtype=np.uint8
        )

        comparison[40:340, 20:440] = original_panel
        comparison[40:340, 460:880] = expanded_panel

        cv2.putText(
            comparison,
            "Original + YOLO Ground Truth",
            (20, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 0),
            2
        )

        cv2.putText(
            comparison,
            "Expanded Crop",
            (460, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 0),
            2
        )

        cv2.putText(
            comparison,
            f"{class_name} | Original box: "
            f"{int(box_width)}x{int(box_height)} | "
            f"Crop: {crop_width}x{crop_height}",
            (20, 355),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 0),
            1
        )

        output_name = (
            f"{class_name}_sample_{sample_number}.jpg"
        )

        output_path = OUTPUT / output_name

        cv2.imwrite(str(output_path), comparison)

        comparison_images.append(comparison)

        print("Saved:", output_path)


# --------------------------------------------------
# CREATE FINAL CONTACT SHEET
# --------------------------------------------------

if comparison_images:

    columns = 2
    rows = math.ceil(len(comparison_images) / columns)

    sheet = np.full(
        (rows * 360, columns * 900, 3),
        255,
        dtype=np.uint8
    )

    for i, image in enumerate(comparison_images):

        row = i // columns
        col = i % columns

        sheet[
            row * 360:(row + 1) * 360,
            col * 900:(col + 1) * 900
        ] = image

    sheet_path = OUTPUT / "validation_alignment_sheet.jpg"

    cv2.imwrite(str(sheet_path), sheet)

    print("\nALIGNMENT INSPECTION COMPLETED")
    print("Total comparisons:", len(comparison_images))
    print("Contact sheet:", sheet_path)

else:

    print("\nNo comparison images were generated.")
