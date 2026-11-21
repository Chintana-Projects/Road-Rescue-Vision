
import os
import pandas as pd
from PIL import Image, ImageDraw

BASE = "data/raw/RDD-India"
OUTPUT = "experiments/dataset_quality"

csv_path = os.path.join(OUTPUT, "train_related_review.csv")
df = pd.read_csv(csv_path)

pairs_per_sheet = 5
thumb_width = 400
thumb_height = 260
label_height = 55

for start in range(0, len(df), pairs_per_sheet):
    batch = df.iloc[start:start + pairs_per_sheet]

    sheet_height = len(batch) * (thumb_height + label_height)
    sheet = Image.new("RGB", (thumb_width * 2, sheet_height), "white")
    draw = ImageDraw.Draw(sheet)

    for index, row in enumerate(batch.itertuples()):
        y = index * (thumb_height + label_height)

        path1 = os.path.join(BASE, row.split_1, "images", row.image_1)
        path2 = os.path.join(BASE, row.split_2, "images", row.image_2)

        img1 = Image.open(path1).convert("RGB")
        img2 = Image.open(path2).convert("RGB")

        img1.thumbnail((thumb_width, thumb_height))
        img2.thumbnail((thumb_width, thumb_height))

        sheet.paste(img1, (0, y + label_height))
        sheet.paste(img2, (thumb_width, y + label_height))

        pair_number = start + index + 1

        draw.text(
            (5, y + 5),
            f"PAIR {pair_number} | {row.split_1} | pHash {row.phash_distance}",
            fill="black"
        )
        draw.text(
            (thumb_width + 5, y + 5),
            f"PAIR {pair_number} | {row.split_2}",
            fill="black"
        )

    output_path = os.path.join(
        OUTPUT,
        f"train_related_sheet_{start // pairs_per_sheet + 1}.jpg"
    )

    sheet.save(output_path, quality=95)
    print("Saved:", output_path)

print("Completed. Total pairs:", len(df))
