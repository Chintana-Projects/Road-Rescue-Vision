
from pathlib import Path
from PIL import Image, ImageDraw
import csv

root = Path("data/raw/RDD-India")
output_dir = Path("experiments/dataset_quality")

csv_path = output_dir / "near_duplicate_candidates_10.csv"

# The pair already reviewed manually
already_reviewed = {
    ("valid", "India_008541_jpg.rf.411752ffbb57ebb8c9ec33a9898daa7d.jpg"),
    ("test", "India_000940_jpg.rf.f79a0d44fd1626ece8cc81897f9945d6.jpg")
}

with csv_path.open("r", encoding="utf-8", newline="") as file:
    candidates = list(csv.DictReader(file))

# Keep only cross-split candidates
cross_split = [
    row for row in candidates
    if row["split_1"] != row["split_2"]
]

# Exclude the pair already reviewed, regardless of pair order
remaining = []

for row in cross_split:
    pair = {
        (row["split_1"], row["image_1"]),
        (row["split_2"], row["image_2"])
    }

    if pair != already_reviewed:
        remaining.append(row)

remaining.sort(key=lambda row: int(row["phash_distance"]))

selected = remaining[:20]

print("Cross-split candidates:", len(cross_split))
print("Already reviewed pair excluded: 1")
print("Selected for visual review:", len(selected))

# Save the selected candidate list
selected_csv = output_dir / "cross_split_top20_review.csv"

with selected_csv.open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=[
        "split_1", "image_1", "split_2",
        "image_2", "phash_distance"
    ])
    writer.writeheader()
    writer.writerows(selected)

# Create comparison sheets: 5 pairs per sheet
thumbnail_size = 300
row_height = 350
sheet_width = 640

for sheet_number in range(4):
    batch = selected[sheet_number * 5:(sheet_number + 1) * 5]

    if not batch:
        continue

    sheet = Image.new(
        "RGB",
        (sheet_width, row_height * len(batch)),
        "white"
    )

    draw = ImageDraw.Draw(sheet)

    for index, row in enumerate(batch):
        y = index * row_height

        name1 = row["image_1"]
        name2 = row["image_2"]
        split1 = row["split_1"]
        split2 = row["split_2"]
        distance = row["phash_distance"]

        draw.text(
            (10, y + 5),
            f"Pair {sheet_number * 5 + index + 1} | "
            f"pHash distance: {distance}",
            fill="black"
        )

        for column, (split, name) in enumerate([
            (split1, name1),
            (split2, name2)
        ]):
            image_path = root / split / "images" / name

            with Image.open(image_path) as img:
                img = img.convert("RGB")
                img.thumbnail((thumbnail_size, thumbnail_size))

                x = 10 + column * 320
                image_y = y + 40

                sheet.paste(img, (x, image_y))

            short_name = name.split("_jpg.rf.")[0]

            draw.text(
                (10 + column * 320, y + 325),
                f"{split}: {short_name}",
                fill="black"
            )

    sheet_path = output_dir / f"cross_split_review_sheet_{sheet_number + 1}.jpg"
    sheet.save(sheet_path, quality=95)

    print("Created:", sheet_path)

print("\nSelected pair list:", selected_csv)
print("Visual review sheets created successfully.")
