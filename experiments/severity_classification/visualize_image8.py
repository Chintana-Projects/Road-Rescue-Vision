
import cv2
from pathlib import Path

image_path = Path(
    "data/raw/RDD-India/train/images/"
    "India_002680_jpg.rf.6e521d35f0983bfb148d13cbe83306d8.jpg"
)

image = cv2.imread(str(image_path))

if image is None:
    raise FileNotFoundError(image_path)

height, width = image.shape[:2]

label_path = (
    image_path.parent.parent / "labels" / (image_path.stem + ".txt")
)

for i, line in enumerate(label_path.read_text().splitlines()):
    class_id, x, y, bw, bh = map(float, line.split())

    x1 = int((x - bw / 2) * width)
    y1 = int((y - bh / 2) * height)
    x2 = int((x + bw / 2) * width)
    y2 = int((y + bh / 2) * height)

    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)

    cv2.putText(
        image,
        f"Box {i + 1} Class {int(class_id)}",
        (x1, max(15, y1 - 5)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (0, 0, 255),
        1
    )

output_path = Path(
    "experiments/severity_classification/results/"
    "image8_original_boxes.jpg"
)

output_path.parent.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(output_path), image)

print("Saved:", output_path)
