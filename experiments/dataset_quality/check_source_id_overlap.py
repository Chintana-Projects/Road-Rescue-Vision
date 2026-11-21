from pathlib import Path
from collections import defaultdict
import re

root = Path("data/raw/RDD-India")
source_ids = defaultdict(list)

for split in ["train", "valid", "test"]:
    image_dir = root / split / "images"

    for image_path in image_dir.iterdir():
        if image_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
            continue

        match = re.match(r"(India_\d+)_", image_path.name)

        if match:
            source_id = match.group(1)
            source_ids[source_id].append((split, image_path.name))

overlaps = {
    source_id: files
    for source_id, files in source_ids.items()
    if len({split for split, _ in files}) > 1
}

print("SOURCE IMAGE ID OVERLAP ANALYSIS")
print("=" * 55)

print("Unique source IDs:", len(source_ids))
print("IDs appearing in multiple splits:", len(overlaps))

if overlaps:
    print("\nFirst 20 overlapping IDs:")

    for source_id, files in list(overlaps.items())[:20]:
        print("\n", source_id)

        for split, filename in files:
            print(split, "->", filename)