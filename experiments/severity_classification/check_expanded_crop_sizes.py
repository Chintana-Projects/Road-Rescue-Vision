
from pathlib import Path
from collections import defaultdict
import cv2
import statistics

BASE = Path(__file__).resolve().parent / "expanded_crops"

stats = defaultdict(list)

for split in ["train", "valid", "test"]:
    for class_name in ["D00", "D20", "D40", "D44"]:

        folder = BASE / split / class_name

        for path in folder.glob("*.jpg"):
            image = cv2.imread(str(path))

            if image is None:
                continue

            height, width = image.shape[:2]
            stats[(split, class_name)].append((width, height))

print("\nEXPANDED CROP SIZE ANALYSIS")

for key, dimensions in stats.items():

    if not dimensions:
        continue

    total = len(dimensions)

    below_32 = sum(
        1 for w, h in dimensions if w < 32 or h < 32
    )

    below_64 = sum(
        1 for w, h in dimensions if w < 64 or h < 64
    )

    median_width = statistics.median(w for w, h in dimensions)
    median_height = statistics.median(h for w, h in dimensions)

    print(f"\n{key[0]} - {key[1]}")
    print("Total:", total)
    print("Below 32 pixels:", below_32)
    print("Below 64 pixels:", below_64)
    print("Median width:", median_width)
    print("Median height:", median_height)
    print("Smallest:", min(dimensions, key=lambda x: x[0] * x[1]))
    print("Largest:", max(dimensions, key=lambda x: x[0] * x[1]))
