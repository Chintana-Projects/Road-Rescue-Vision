
from pathlib import Path
from collections import defaultdict
import cv2

base = Path(__file__).resolve().parent / "crops"

stats = defaultdict(list)

for split in ["train", "valid", "test"]:
    for class_name in ["D00", "D20", "D40", "D44"]:

        folder = base / split / class_name

        for path in folder.glob("*.jpg"):
            image = cv2.imread(str(path))

            if image is None:
                continue

            height, width = image.shape[:2]
            stats[(split, class_name)].append((width, height))

print("\nCROP SIZE ANALYSIS")

for key, dimensions in stats.items():

    total = len(dimensions)

    small_32 = sum(
        1 for w, h in dimensions if w < 32 or h < 32
    )

    small_64 = sum(
        1 for w, h in dimensions if w < 64 or h < 64
    )

    print(f"\n{key[0]} - {key[1]}")
    print("Total:", total)
    print("Below 32 pixels in either dimension:", small_32)
    print("Below 64 pixels in either dimension:", small_64)
    print("Smallest:", min(dimensions, key=lambda x: x[0] * x[1]))
    print("Largest:", max(dimensions, key=lambda x: x[0] * x[1]))
