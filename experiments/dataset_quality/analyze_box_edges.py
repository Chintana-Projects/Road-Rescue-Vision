from pathlib import Path
from collections import defaultdict

root = Path("data/raw/RDD-India")
edge_counts = defaultdict(int)
total_counts = defaultdict(int)

for split in ["train", "valid", "test"]:
    label_dir = root / split / "labels"

    for file in label_dir.glob("*.txt"):
        for line in file.read_text().splitlines():
            parts = line.split()

            if not parts:
                continue

            class_id = int(parts[0])
            x = float(parts[1])
            y = float(parts[2])
            w = float(parts[3])
            h = float(parts[4])

            left = x - w / 2
            right = x + w / 2
            top = y - h / 2
            bottom = y + h / 2

            total_counts[class_id] += 1

            if (
                left <= 0.001
                or right >= 0.999
                or top <= 0.001
                or bottom >= 0.999
            ):
                edge_counts[class_id] += 1

print("BOUNDING BOX EDGE ANALYSIS")
print("=" * 55)

for class_id in range(4):
    total = total_counts[class_id]
    edge = edge_counts[class_id]

    percentage = (edge / total) * 100 if total else 0

    print(f"\nClass {class_id}")
    print("Total boxes:", total)
    print("Boxes touching image edges:", edge)
    print("Percentage:", round(percentage, 2), "%")