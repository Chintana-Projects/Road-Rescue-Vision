from pathlib import Path
from collections import defaultdict
import hashlib

root = Path("data/raw/RDD-India")

hash_groups = defaultdict(list)

for split in ["train", "valid", "test"]:
    image_dir = root / split / "images"

    for image_path in image_dir.iterdir():
        if image_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
            continue

        file_hash = hashlib.sha256(image_path.read_bytes()).hexdigest()
        hash_groups[file_hash].append((split, image_path.name))

duplicate_groups = [
    files for files in hash_groups.values()
    if len(files) > 1
]

print("EXACT DUPLICATE IMAGE ANALYSIS")
print("=" * 55)

print("Total unique image hashes:", len(hash_groups))
print("Duplicate groups:", len(duplicate_groups))

duplicates_within_split = 0
duplicates_across_splits = 0

for group in duplicate_groups:
    splits = {split for split, _ in group}

    if len(splits) > 1:
        duplicates_across_splits += 1
    else:
        duplicates_within_split += 1

print("Duplicates within same split:", duplicates_within_split)
print("Duplicates across different splits:", duplicates_across_splits)

if duplicate_groups:
    print("\nFirst 10 duplicate groups:")

    for group in duplicate_groups[:10]:
        print("\nGroup:")
        for split, filename in group:
            print(split, "->", filename)