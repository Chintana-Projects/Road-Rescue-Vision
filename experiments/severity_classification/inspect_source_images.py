
from pathlib import Path
import csv
import cv2
import math
import numpy as np

BASE = Path(__file__).resolve().parent
PROJECT_ROOT = BASE.parents[1]

DATASET = PROJECT_ROOT / "data" / "raw" / "RDD-India"

PILOT_CSV = BASE / "annotations" / "severity_pilot.csv"

OUTPUT = BASE / "results" / "pilot_source_images.jpg"

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

image_lookup = {}

for split in ["train", "valid", "test"]:
    image_dir = DATASET / split / "images"

    for path in image_dir.glob("*"):
        if path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
            image_lookup[path.stem] = path

with open(PILOT_CSV, "r", newline="", encoding="utf-8") as file:
    pilot = list(csv.DictReader(file))

tiles = []

for row in pilot:

    crop_name = row["crop_name"]
    source_stem = Path(crop_name).stem.rsplit("_", 1)[0]

    source_path = image_lookup.get(source_stem)

    if source_path is None:
        print("Source not found:", crop_name)
        continue

    image = cv2.imread(str(source_path))

    if image is None:
        print("Could not read:", source_path)
        continue

    image = cv2.resize(image, (320, 240))

    tile = np.full((280, 340, 3), 255, dtype=np.uint8)
    tile[0:240, 10:330] = image

    label = f'{row["damage_class"]} | {source_path.name[:27]}'

    cv2.putText(
        tile,
        label,
        (10, 265),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (0, 0, 0),
        1
    )

    tiles.append(tile)

columns = 4
rows = math.ceil(len(tiles) / columns)

sheet = np.full(
    (rows * 280, columns * 340, 3),
    255,
    dtype=np.uint8
)

for index, tile in enumerate(tiles):
    r = index // columns
    c = index % columns

    sheet[
        r * 280:(r + 1) * 280,
        c * 340:(c + 1) * 340
    ] = tile

cv2.imwrite(str(OUTPUT), sheet)

print("SOURCE IMAGE INSPECTION COMPLETED")
print("Images:", len(tiles))
print("Saved:", OUTPUT)
