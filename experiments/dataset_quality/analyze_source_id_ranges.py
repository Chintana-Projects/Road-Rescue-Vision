from pathlib import Path
from collections import defaultdict
import re

root = Path("data/raw/RDD-India")

ranges = defaultdict(lambda: {
    "train": 0,
    "valid": 0,
    "test": 0
})

for split in ["train", "valid", "test"]:
    image_dir = root / split / "images"

    for image_path in image_dir.iterdir():
        match = re.match(r"India_(\d+)_", image_path.name)

        if not match:
            continue

        image_id = int(match.group(1))
        range_start = (image_id // 500) * 500

        ranges[range_start][split] += 1

print("SOURCE ID RANGE DISTRIBUTION")
print("=" * 65)
print(f"{'ID RANGE':<15}{'TRAIN':<12}{'VALID':<12}{'TEST':<12}")

for start in sorted(ranges):
    end = start + 499
    counts = ranges[start]

    print(
        f"{start}-{end:<10}"
        f"{counts['train']:<12}"
        f"{counts['valid']:<12}"
        f"{counts['test']:<12}"
    )