
from pathlib import Path

root = Path("data/raw/RDD-India")

total_boxes = 0
invalid_rows = []
class_counts = {0: 0, 1: 0, 2: 0, 3: 0}

for split in ["train", "valid", "test"]:

    label_dir = root / split / "labels"

    for file in label_dir.glob("*.txt"):

        for line_number, line in enumerate(
            file.read_text().splitlines(), start=1
        ):

            parts = line.split()

            if not parts:
                continue

            total_boxes += 1

            try:
                if len(parts) != 5:
                    raise ValueError("Expected 5 values")

                class_id = int(parts[0])
                x, y, w, h = map(float, parts[1:])

                if class_id not in class_counts:
                    raise ValueError("Invalid class ID")

                if not all(0 <= value <= 1 for value in [x, y, w, h]):
                    raise ValueError("Coordinate outside 0-1")

                if w <= 0 or h <= 0:
                    raise ValueError("Zero or negative box size")

                if x - w / 2 < 0 or x + w / 2 > 1:
                    raise ValueError("Box exceeds horizontal boundary")

                if y - h / 2 < 0 or y + h / 2 > 1:
                    raise ValueError("Box exceeds vertical boundary")

                class_counts[class_id] += 1

            except (ValueError, TypeError) as error:
                invalid_rows.append(
                    (split, file.name, line_number, str(error))
                )

print("Total bounding boxes:", total_boxes)
print("Valid bounding boxes:", total_boxes - len(invalid_rows))
print("Invalid bounding boxes:", len(invalid_rows))

print("\nValid class counts:")
for class_id, count in class_counts.items():
    print(f"Class {class_id}: {count}")

print("\nFirst 20 invalid annotations:")
for item in invalid_rows[:20]:
    print(item)
