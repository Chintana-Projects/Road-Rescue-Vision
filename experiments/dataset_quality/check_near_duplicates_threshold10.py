
from pathlib import Path
from PIL import Image
import imagehash
from itertools import combinations
import csv

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

near_duplicates = []

print("Comparing image hashes...")

for first, second in combinations(image_hashes, 2):
    distance = first["hash"] - second["hash"]

    if distance <= 10:
        near_duplicates.append((
            first["split"],
            first["name"],
            second["split"],
            second["name"],
            distance
        ))

near_duplicates.sort(key=lambda pair: pair[4])

cross_split = [
    pair for pair in near_duplicates
    if pair[0] != pair[2]
]

same_split = [
    pair for pair in near_duplicates
    if pair[0] == pair[2]
]

print("\nNEAR-DUPLICATE ANALYSIS")
print("=" * 60)
print("Threshold: Hamming distance <= 10")
print("Total candidate pairs:", len(near_duplicates))
print("Same-split pairs:", len(same_split))
print("Cross-split pairs:", len(cross_split))

output_path = Path(
    "experiments/dataset_quality/near_duplicate_candidates_10.csv"
)

with output_path.open("w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)

    writer.writerow([
        "split_1",
        "image_1",
        "split_2",
        "image_2",
        "phash_distance"
    ])

    writer.writerows(near_duplicates)

print("\nResults saved to:", output_path)

print("\nFIRST 30 CANDIDATE PAIRS")

for pair in near_duplicates[:30]:
    print("\nImage 1:", pair[0], pair[1])
    print("Image 2:", pair[2], pair[3])
    print("Hash distance:", pair[4])
