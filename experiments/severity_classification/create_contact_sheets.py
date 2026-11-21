
from pathlib import Path
import cv2
import random
import math

BASE = Path(__file__).resolve().parent
DATA = BASE / "expanded_crops"
OUTPUT = BASE / "results"

OUTPUT.mkdir(parents=True, exist_ok=True)

random.seed(42)

classes = ["D00", "D20", "D40", "D44"]
splits = ["train", "valid"]

for split in splits:

    images = []

    for class_name in classes:

        folder = DATA / split / class_name
        files = list(folder.glob("*.jpg"))

        selected = random.sample(files, min(5, len(files)))

        for path in selected:

            image = cv2.imread(str(path))

            if image is None:
                continue

            h, w = image.shape[:2]

            # Resize for display only, preserving aspect ratio
            scale = min(180 / w, 130 / h)

            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))

            image = cv2.resize(image, (new_w, new_h))

            canvas = 255 * (image.shape[0] > 0)
            tile = 255 * __import__("numpy").ones(
                (175, 200, 3), dtype="uint8"
            )

            x = (200 - new_w) // 2
            y = 25 + (130 - new_h) // 2

            tile[y:y + new_h, x:x + new_w] = image

            cv2.putText(
                tile,
                f"{class_name} | {w}x{h}",
                (5, 165),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (0, 0, 0),
                1
            )

            images.append(tile)

    columns = 4
    rows = math.ceil(len(images) / columns)

    sheet = 255 * __import__("numpy").ones(
        (rows * 175, columns * 200, 3),
        dtype="uint8"
    )

    for i, image in enumerate(images):
        row = i // columns
        col = i % columns

        sheet[
            row * 175:(row + 1) * 175,
            col * 200:(col + 1) * 200
        ] = image

    output_path = OUTPUT / f"{split}_expanded_contact_sheet.jpg"

    cv2.imwrite(str(output_path), sheet)

    print("Saved:", output_path)

print("\nCONTACT SHEETS CREATED")
