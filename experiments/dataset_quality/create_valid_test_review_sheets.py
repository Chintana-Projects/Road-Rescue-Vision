from pathlib import Path
from PIL import Image, ImageDraw
import csv
import math

root = Path("data/raw/RDD-India")
output_dir = Path("experiments/dataset_quality")

csv_path = output_dir / "valid_test_manual_review.csv"

with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
    candidates = list(csv.DictReader(file))

candidates.sort(key=lambda row: int(row["phash_distance"]))

print("Validation-Test candidates:", len(candidates))

thumbnail_size = (300, 270)
row_height = 330
sheet_width = 640
pairs_per_sheet = 5

total_sheets = math.ceil(len(candidates) / pairs_per_sheet)

for sheet_number in range(total_sheets):
    batch = candidates[
        sheet_number * pairs_per_sheet:
        (sheet_number + 1) * pairs_per_sheet
    ]

    sheet = Image.new(
        "RGB",
        (sheet_width, row_height * len(batch)),
        "white"
    )

    draw = ImageDraw.Draw(sheet)

    for index, row in enumerate(batch):
        pair_number = sheet_number * pairs_per_sheet + index + 1
        y = index * row_height

        draw.text(
            (10, y + 5),
            f"Pair {pair_number} | pHash distance: {row['phash_distance']}",
            fill="black"
        )

        for column, (split, name) in enumerate([
            (row["split_1"], row["image_1"]),
            (row["split_2"], row["image_2"])
        ]):
            image_path = root / split / "images" / name

            with Image.open(image_path) as img:
                img = img.convert("RGB")
                img.thumbnail(thumbnail_size)

                x = 10 + column * 320
                sheet.paste(img, (x, y + 30))

            short_name = name.split("_jpg.rf.")[0]

            draw.text(
                (10 + column * 320, y + 305),
                f"{split}: {short_name}",
                fill="black"
            )

    sheet_path = output_dir / f"valid_test_review_sheet_{sheet_number + 1}.jpg"
    sheet.save(sheet_path, quality=95)

    print("Created:", sheet_path)

print("\nTotal sheets created:", total_sheets)
print("All Validation-Test comparison sheets generated.")
