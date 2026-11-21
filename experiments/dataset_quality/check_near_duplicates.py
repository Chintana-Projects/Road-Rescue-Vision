from pathlib import Path
from collections import defaultdict
from PIL import Image
import imagehash
from itertools import combinations

root = Path("data/raw/RDD-India")
splits = ["train", "valid", "test"]

image_hashes = []

print("Calculating perceptual hashes...")

for split in splits:
    image_dir = root / split / "images"

    for image_path in image_dir.iterdir():
        if image_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
            continue

        try:
            with Image.open(image_path) as img:
                phash = imagehash.phash(img)

            image_hashes.append({
                "split": split,
                "name": image_path.name,
                "hash": phash
            })

        except Exception as error:
            print("Could not process:", image_path.name, error)

print("Images processed:", len(image_hashes))

# Compare every pair of perceptual hashes.
# Hamming distance <= 5 is used as an initial review threshold.

near_duplicates = []

print("Comparing image hashes...")

for first, second in combinations(image_hashes, 2):
    distance = first["hash"] - second["hash"]

    if distance <= 5:
        near_duplicates.append((
            first["split"],
            first["name"],
            second["split"],
            second["name"],
            distance
        ))

print("\nNEAR-DUPLICATE IMAGE ANALYSIS")
print("=" * 60)
print("Similarity threshold: Hamming distance <= 5")
print("Near-duplicate pairs found:", len(near_duplicates))

cross_split = [
    pair for pair in near_duplicates
    if pair[0] != pair[2]
]

same_split = [
    pair for pair in near_duplicates
    if pair[0] == pair[2]
]

print("Pairs within the same split:", len(same_split))
print("Pairs across different splits:", len(cross_split))

if near_duplicates:
    print("\nFirst 30 candidate pairs:")

    for pair in near_duplicates[:30]:
        print("\nImage 1:", pair[0], pair[1])
        print("Image 2:", pair[2], pair[3])
        print("Hash distance:", pair[4])