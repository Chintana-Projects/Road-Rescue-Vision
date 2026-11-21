
from pathlib import Path
from collections import defaultdict
import cv2
import csv
import math

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET = PROJECT_ROOT / "data" / "raw" / "RDD-India"

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "expanded_crops"
ANNOTATIONS = BASE / "annotations"

CLASSES = {
    0: "D00",
    1: "D20",
    2: "D40",
    3: "D44"
}

EXPANSION_FACTOR = 2.0
MIN_CROP_SIZE = 64

rows = []
counts = defaultdict(int)
skipped = 0


def crop_bounds(center, desired_size, limit):
    """Create a crop window while keeping it inside the image."""

    size = min(desired_size, limit)

    start = int(round(center - size / 2))
    end = start + size

    if start < 0:
        start = 0
        end = size

    if end > limit:
        end = limit
        start = limit - size

    return start, end


for split in ["train", "valid", "test"]:

    image_dir = DATASET / split / "images"
    label_dir = DATASET / split / "labels"

    if not image_dir.exists() or not label_dir.exists():
        print(f"Missing folders: {split}")
        continue

    image_lookup = {
        path.stem: path
        for path in image_dir.iterdir()
        if path.suffix.lower() in [".jpg", ".jpeg", ".png"]
    }

    for label_file in label_dir.glob("*.txt"):

        image_path = image_lookup.get(label_file.stem)

        if image_path is None:
            skipped += 1
            continue

        image = cv2.imread(str(image_path))

        if image is None:
            skipped += 1
            continue

        height, width = image.shape[:2]

        with open(label_file, "r") as file:
            lines = file.readlines()

        for index, line in enumerate(lines):

            values = line.strip().split()

            if len(values) != 5:
                skipped += 1
                continue

            try:
                class_id, xc, yc, bw, bh = map(float, values)
            except ValueError:
                skipped += 1
                continue

            if (
                class_id not in CLASSES
                or not (0 <= xc <= 1 and 0 <= yc <= 1)
                or not (0 < bw <= 1 and 0 < bh <= 1)
            ):
                skipped += 1
                continue

            # Convert normalized coordinates to pixels
            cx = xc * width
            cy = yc * height
            box_w = bw * width
            box_h = bh * height

            # Expand around the original box
            desired_w = max(
                MIN_CROP_SIZE,
                math.ceil(box_w * EXPANSION_FACTOR)
            )

            desired_h = max(
                MIN_CROP_SIZE,
                math.ceil(box_h * EXPANSION_FACTOR)
            )

            x1, x2 = crop_bounds(cx, desired_w, width)
            y1, y2 = crop_bounds(cy, desired_h, height)

            if x2 <= x1 or y2 <= y1:
                skipped += 1
                continue

            crop = image[y1:y2, x1:x2]

            if crop.size == 0:
                skipped += 1
                continue

            class_name = CLASSES[int(class_id)]

            output_dir = OUTPUT / split / class_name
            output_dir.mkdir(parents=True, exist_ok=True)

            crop_name = f"{label_file.stem}_{index}.jpg"
            crop_path = output_dir / crop_name

            if cv2.imwrite(str(crop_path), crop):

                crop_h, crop_w = crop.shape[:2]

                counts[(split, class_name)] += 1

                rows.append([
                    split,
                    crop_name,
                    class_name,
                    str(crop_path),
                    crop_w,
                    crop_h,
                    x1, y1, x2, y2
                ])

            else:
                skipped += 1


# Save metadata
ANNOTATIONS.mkdir(parents=True, exist_ok=True)

csv_path = ANNOTATIONS / "expanded_crop_metadata.csv"

with open(csv_path, "w", newline="") as file:

    writer = csv.writer(file)

    writer.writerow([
        "split",
        "crop_name",
        "damage_class",
        "crop_path",
        "crop_width",
        "crop_height",
        "x1", "y1", "x2", "y2"
    ])

    writer.writerows(rows)


print("\nEXPANDED CROP GENERATION COMPLETED")
print("Total crops:", len(rows))
print("Skipped:", skipped)
print("Metadata:", csv_path)

print("\nCROPS BY SPLIT AND CLASS:")

for split in ["train", "valid", "test"]:
    for class_name in CLASSES.values():
        print(
            f"{split} - {class_name}: "
            f"{counts[(split, class_name)]}"
        )
