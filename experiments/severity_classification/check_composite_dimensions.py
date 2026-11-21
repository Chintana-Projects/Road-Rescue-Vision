
import csv
from pathlib import Path
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PILOT_CSV = (
    PROJECT_ROOT / "experiments" / "severity_classification"
    / "annotations" / "severity_pilot.csv"
)

IMAGE_DIR = PROJECT_ROOT / "data" / "raw" / "RDD-India" / "train" / "images"

OUTPUT_DIR = (
    PROJECT_ROOT / "experiments" / "severity_classification"
    / "results" / "boundary_check"
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

selected = [
    "India_002775",
    "India_000543",
    "India_000768",
]

with open(PILOT_CSV, newline="", encoding="utf-8") as file:
    rows = list(csv.DictReader(file))

for prefix in selected:
    row = next(
        (r for r in rows if r["crop_name"].startswith(prefix)),
        None
    )

    if row is None:
        print("Pilot entry not found:", prefix)
        continue

    source_stem = row["crop_name"].rsplit("_", 1)[0]
    matches = list(IMAGE_DIR.glob(source_stem + ".*"))

    if not matches:
        print("Source image not found:", source_stem)
        continue

    with Image.open(matches[0]) as original:
        preview = original.convert("RGB")

    draw = ImageDraw.Draw(preview)
    width, height = preview.size

    draw.line((width // 2, 0, width // 2, height), fill="red", width=2)
    draw.line((0, height // 2, width, height // 2), fill="red", width=2)

    output_path = OUTPUT_DIR / f"{prefix}_boundary.jpg"
    preview.save(output_path)

    print("Saved:", output_path)

