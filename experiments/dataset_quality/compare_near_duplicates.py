from pathlib import Path
from PIL import Image, ImageDraw

root = Path("data/raw/RDD-India")

image1 = root / "valid/images/India_008541_jpg.rf.411752ffbb57ebb8c9ec33a9898daa7d.jpg"
image2 = root / "test/images/India_000940_jpg.rf.f79a0d44fd1626ece8cc81897f9945d6.jpg"

img1 = Image.open(image1).convert("RGB")
img2 = Image.open(image2).convert("RGB")

img1.thumbnail((416, 416))
img2.thumbnail((416, 416))

canvas = Image.new("RGB", (850, 470), "white")

draw = ImageDraw.Draw(canvas)

canvas.paste(img1, (5, 40))
canvas.paste(img2, (430, 40))

draw.text((5, 10), "VALIDATION IMAGE", fill="black")
draw.text((430, 10), "TEST IMAGE", fill="black")

output_dir = Path("experiments/dataset_quality")
output_dir.mkdir(parents=True, exist_ok=True)

output_path = output_dir / "near_duplicate_comparison.jpg"

canvas.save(output_path)

print("Comparison image saved to:")
print(output_path.resolve())