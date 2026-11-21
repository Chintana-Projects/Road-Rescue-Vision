
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]

IMAGE_DIR = ROOT / "data" / "raw" / "RDD-India" / "train" / "images"
LABEL_DIR = ROOT / "experiments" / "severity_classification" / "results" / "quadrant_split_pilot" / "labels"
OUTPUT_DIR = ROOT / "experiments" / "severity_classification" / "results" / "quadrant_split_pilot" / "visualized"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

stem = "India_002775_jpg.rf.b7022146256cd793e8027920a647d95c"

with Image.open(IMAGE_DIR / f"{stem}.jpg") as original:
    original = original.convert("RGB")
    w, h = original.size

    quadrants = {
        "top_left": (0, 0, w // 2, h // 2),
        "top_right": (w // 2, 0, w, h // 2),
        "bottom_left": (0, h // 2, w // 2, h),
        "bottom_right": (w // 2, h // 2, w, h),
    }

    for name, coords in quadrants.items():
        image = original.crop(coords)
        draw = ImageDraw.Draw(image)

        label_file = LABEL_DIR / f"{name}.txt"

        if label_file.exists():
            for line in label_file.read_text().splitlines():
                if not line.strip():
                    continue

                cls, xc, yc, bw, bh = line.split()
                xc, yc, bw, bh = map(float, (xc, yc, bw, bh))

                x1 = (xc - bw / 2) * image.width
                y1 = (yc - bh / 2) * image.height
                x2 = (xc + bw / 2) * image.width
                y2 = (yc + bh / 2) * image.height

                draw.rectangle((x1, y1, x2, y2), outline="red", width=2)
                draw.text((x1, y1), f"Class {cls}", fill="red")

        output = OUTPUT_DIR / f"{name}_preview.jpg"
        image.save(output)
        print("Saved:", output)

print("Visualization completed.")
