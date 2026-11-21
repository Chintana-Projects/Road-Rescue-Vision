
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]

IMAGE_DIR = PROJECT_ROOT / "data" / "raw" / "RDD-India" / "train" / "images"

OUTPUT_DIR = (
    PROJECT_ROOT / "experiments" / "severity_classification"
    / "results" / "quadrant_split_pilot"
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

selected = [
    "India_002775_jpg.rf.b7022146256cd793e8027920a647d95c",
    "India_000543_jpg.rf.71414aed1ff40268eef5ee19ee3c177a",
    "India_000768_jpg.rf.f538fa8764646b898018c4f2bac6e160",
]

for stem in selected:
    matches = list(IMAGE_DIR.glob(stem + ".*"))

    if not matches:
        print("NOT FOUND:", stem)
        continue

    with Image.open(matches[0]) as image:
        image = image.convert("RGB")
        width, height = image.size

        if width % 2 != 0 or height % 2 != 0:
            print("Uneven dimensions; skipping:", stem)
            continue

        mid_x = width // 2
        mid_y = height // 2

        quadrants = {
            "top_left": (0, 0, mid_x, mid_y),
            "top_right": (mid_x, 0, width, mid_y),
            "bottom_left": (0, mid_y, mid_x, height),
            "bottom_right": (mid_x, mid_y, width, height),
        }

        for name, coordinates in quadrants.items():
            crop = image.crop(coordinates)
            output_path = OUTPUT_DIR / f"{stem}_{name}.jpg"
            crop.save(output_path, quality=95)
            print("Saved:", output_path)

print("\nPilot splitting completed.")
