
from pathlib import Path
import cv2
import csv

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET = PROJECT_ROOT / "data" / "raw" / "RDD-India"

OUTPUT = Path(__file__).resolve().parent / "crops"
ANNOTATIONS = Path(__file__).resolve().parent / "annotations"

CLASSES = {
    0: "D00",
    1: "D20",
    2: "D40",
    3: "D44"
}

rows = []
crop_count = 0
skipped_count = 0

for split in ["train", "valid", "test"]:

    image_dir = DATASET / split / "images"
    label_dir = DATASET / split / "labels"

    if not image_dir.exists() or not label_dir.exists():
        print(f"Missing folders for split: {split}")
        continue

    for label_file in label_dir.glob("*.txt"):

        image_path = image_dir / f"{label_file.stem}.jpg"

        if not image_path.exists():
            skipped_count += 1
            continue

        image = cv2.imread(str(image_path))

        if image is None:
            skipped_count += 1
            continue

        height, width = image.shape[:2]

        with open(label_file, "r") as file:
            lines = file.readlines()

        for index, line in enumerate(lines):

            values = line.strip().split()

            if len(values) != 5:
                skipped_count += 1
                continue

            class_id, x_center, y_center, box_width, box_height = map(
                float, values
            )

            class_id = int(class_id)

            if class_id not in CLASSES:
                skipped_count += 1
                continue

            # Convert normalized YOLO coordinates to pixels
            x_center *= width
            y_center *= height
            box_width *= width
            box_height *= height

            x1 = max(0, int(x_center - box_width / 2))
            y1 = max(0, int(y_center - box_height / 2))
            x2 = min(width, int(x_center + box_width / 2))
            y2 = min(height, int(y_center + box_height / 2))

            if x2 <= x1 or y2 <= y1:
                skipped_count += 1
                continue

            crop = image[y1:y2, x1:x2]

            class_name = CLASSES[class_id]

            output_dir = OUTPUT / split / class_name
            output_dir.mkdir(parents=True, exist_ok=True)

            crop_name = f"{label_file.stem}_{index}.jpg"
            crop_path = output_dir / crop_name

            if cv2.imwrite(str(crop_path), crop):

                crop_count += 1

                rows.append([
                    split,
                    crop_name,
                    class_name,
                    str(crop_path),
                    x1, y1, x2, y2
                ])

            else:
                skipped_count += 1

# Save crop metadata
ANNOTATIONS.mkdir(parents=True, exist_ok=True)

csv_path = ANNOTATIONS / "crop_metadata.csv"

with open(csv_path, "w", newline="") as file:

    writer = csv.writer(file)

    writer.writerow([
        "split",
        "crop_name",
        "damage_class",
        "crop_path",
        "x1", "y1", "x2", "y2"
    ])

    writer.writerows(rows)

print("\nCROP PREPARATION COMPLETED")
print("Total crops:", crop_count)
print("Skipped:", skipped_count)
print("Metadata:", csv_path)

print("\nCrops by split and class:")

for split in ["train", "valid", "test"]:
    for class_name in CLASSES.values():
        folder = OUTPUT / split / class_name
        count = len(list(folder.glob("*.jpg"))) if folder.exists() else 0
        print(f"{split} - {class_name}: {count}")
