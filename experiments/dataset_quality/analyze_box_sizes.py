
from pathlib import Path
from collections import defaultdict
import statistics

root = Path("data/raw/RDD-India")

box_areas = defaultdict(list)

for split in ["train", "valid", "test"]:

    label_dir = root / split / "labels"

    for file in label_dir.glob("*.txt"):

        for line in file.read_text().splitlines():

            parts = line.split()

            if not parts:
                continue

            class_id = int(parts[0])
            width = float(parts[3])
            height = float(parts[4])

            area_percent = width * height * 100

            box_areas[class_id].append(area_percent)

print("BOUNDING BOX AREA ANALYSIS")
print("=" * 55)

for class_id in range(4):

    areas = box_areas[class_id]

    print(f"\nClass {class_id}")
    print("Number of boxes:", len(areas))
    print("Minimum area (%):", round(min(areas), 4))
    print("Median area (%):", round(statistics.median(areas), 4))
    print("Maximum area (%):", round(max(areas), 4))

    print("Tiny boxes (< 0.1%):",
          sum(a < 0.1 for a in areas))

    print("Large boxes (> 50%):",
          sum(a > 50 for a in areas))
