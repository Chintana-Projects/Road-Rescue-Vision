
import cv2
from pathlib import Path

image_path = Path(
    "data/raw/RDD-India/train/images/"
    "India_000814_jpg.rf.78a3e907cf2ea0ec319c030707708504.jpg"
)

image = cv2.imread(str(image_path))

if image is None:
    raise FileNotFoundError(image_path)

height, width = image.shape[:2]

label_path = (
    image_path.parent.parent / "labels" / (image_path.stem + ".txt")
)

colors = [
    (0, 255, 0),
    (0, 255, 255),
    (0, 0, 255),
    (255, 0, 0)
]

for i, line in enumerate(label_path.read_text().splitlines()):
    class_id, x, y, bw, bh = map(float, line.split())

    x1 = int((x - bw / 2) * width)
    y1 = int((y - bh / 2) * height)
    x2 = int((x + bw / 2) * width)
    y2 = int((y + bh / 2) * height)

    color = colors[int(class_id)]

    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

    cv2.putText(
        image,
        f"Box {i + 1} Class {int(class_id)}",
        (x1, max(15, y1 - 5)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        color,
        1
    )

output_path = Path(
    "experiments/severity_classification/results/"
    "image7_original_boxes.jpg"
)

output_path.parent.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(output_path), image)

print("Saved:", output_path)
