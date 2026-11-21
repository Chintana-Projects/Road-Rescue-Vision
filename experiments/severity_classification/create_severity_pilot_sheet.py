
from pathlib import Path
import csv
import cv2
import numpy as np
import math

BASE = Path(__file__).resolve().parent

CSV_PATH = BASE / "annotations" / "severity_pilot.csv"
OUTPUT_DIR = BASE / "results"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TILE_WIDTH = 240
TILE_HEIGHT = 200
IMAGE_HEIGHT = 155
COLUMNS = 4

tiles = []

with open(CSV_PATH, "r", newline="", encoding="utf-8") as file:
    rows = list(csv.DictReader(file))

for row in rows:

    image_path = Path(row["crop_path"])

    image = cv2.imread(str(image_path))

    if image is None:
        print("Could not read:", image_path)
        continue

    height, width = image.shape[:2]

    scale = min(
        210 / width,
        IMAGE_HEIGHT / height
    )

    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))

    resized = cv2.resize(
        image,
        (new_width, new_height)
    )

    tile = np.full(
        (TILE_HEIGHT, TILE_WIDTH, 3),
        255,
        dtype=np.uint8
    )

    x = (TILE_WIDTH - new_width) // 2
    y = (IMAGE_HEIGHT - new_height) // 2

    tile[y:y + new_height, x:x + new_width] = resized

    text = f'{row["damage_class"]} | {width}x{height}'

    cv2.putText(
        tile,
        text,
        (8, 175),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 0, 0),
        1
    )

    tiles.append(tile)

rows_count = math.ceil(len(tiles) / COLUMNS)

sheet = np.full(
    (rows_count * TILE_HEIGHT, COLUMNS * TILE_WIDTH, 3),
    255,
    dtype=np.uint8
)

for index, tile in enumerate(tiles):

    r = index // COLUMNS
    c = index % COLUMNS

    sheet[
        r * TILE_HEIGHT:(r + 1) * TILE_HEIGHT,
        c * TILE_WIDTH:(c + 1) * TILE_WIDTH
    ] = tile

output_path = OUTPUT_DIR / "severity_pilot_contact_sheet.jpg"

cv2.imwrite(str(output_path), sheet)

print("\nPILOT CONTACT SHEET CREATED")
print("Images displayed:", len(tiles))
print("Saved to:", output_path)
