from pathlib import Path
from collections import Counter
import re

root = Path("data/raw/RDD-India")
split_ids = {}

for split in ["train", "valid", "test"]:
    image_dir = root / split / "images"
    ids = []

    for image_path in image_dir.iterdir():
        match = re.match(r"India_(\d+)_", image_path.name)

        if match:
            ids.append(int(match.group(1)))

    split_ids[split] = sorted(ids)

    print(f"\n{split.upper()}")
    print("=" * 40)
    print("Image count:", len(ids))
    print("Minimum ID:", min(ids))
    print("Maximum ID:", max(ids))
    print("First 10 IDs:", sorted(ids)[:10])
    print("Last 10 IDs:", sorted(ids)[-10:])

# Check which split contains each numeric ID.
all_ids = sorted(
    (image_id, split)
    for split, ids in split_ids.items()
    for image_id in ids
)

print("\nSOURCE ID ORDER ANALYSIS")
print("=" * 40)

for split in ["train", "valid", "test"]:
    print(split, "images:", len(split_ids[split]))

# Count adjacent IDs belonging to different splits.
adjacent_cross_split = 0

for i in range(len(all_ids) - 1):
    current_id, current_split = all_ids[i]
    next_id, next_split = all_ids[i + 1]

    if next_id - current_id == 1 and current_split != next_split:
        adjacent_cross_split += 1

print("Adjacent consecutive IDs crossing splits:", adjacent_cross_split)