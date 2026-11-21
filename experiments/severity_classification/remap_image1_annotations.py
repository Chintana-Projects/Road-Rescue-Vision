
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LABEL_FILE = (
    PROJECT_ROOT / "data" / "raw" / "RDD-India"
    / "train" / "labels"
    / "India_002775_jpg.rf.b7022146256cd793e8027920a647d95c.txt"
)

OUTPUT_DIR = (
    PROJECT_ROOT / "experiments" / "severity_classification"
    / "results" / "quadrant_split_pilot" / "labels"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Each quadrant's boundaries in original normalized coordinates.
QUADRANTS = {
    "top_left":     (0.0, 0.0, 0.5, 0.5),
    "top_right":    (0.5, 0.0, 1.0, 0.5),
    "bottom_left":  (0.0, 0.5, 0.5, 1.0),
    "bottom_right": (0.5, 0.5, 1.0, 1.0),
}

# Read original YOLO annotations.
boxes = []

with open(LABEL_FILE, "r", encoding="utf-8") as file:
    for line in file:
        values = line.strip().split()

        if len(values) != 5:
            continue

        cls = int(values[0])
        x, y, w, h = map(float, values[1:])

        boxes.append((cls, x, y, w, h))


# Process each quadrant independently.
for quadrant, (qx1, qy1, qx2, qy2) in QUADRANTS.items():

    remapped_boxes = []

    for cls, x, y, w, h in boxes:

        # Original bounding-box edges.
        x1 = x - w / 2
        y1 = y - h / 2
        x2 = x + w / 2
        y2 = y + h / 2

        # Intersection with the current quadrant.
        ix1 = max(x1, qx1)
        iy1 = max(y1, qy1)
        ix2 = min(x2, qx2)
        iy2 = min(y2, qy2)

        # No intersection.
        if ix2 <= ix1 or iy2 <= iy1:
            continue

        # Intersection area / original box area.
        original_area = w * h
        intersection_area = (ix2 - ix1) * (iy2 - iy1)

        retained_ratio = intersection_area / original_area

        # Drop boxes with less than 60% of their original
        # area retained in this quadrant.
        if retained_ratio < 0.60:
            continue

        # Convert coordinates to the quadrant's coordinate system.
        new_x1 = (ix1 - qx1) / (qx2 - qx1)
        new_y1 = (iy1 - qy1) / (qy2 - qy1)
        new_x2 = (ix2 - qx1) / (qx2 - qx1)
        new_y2 = (iy2 - qy1) / (qy2 - qy1)

        new_x = (new_x1 + new_x2) / 2
        new_y = (new_y1 + new_y2) / 2
        new_w = new_x2 - new_x1
        new_h = new_y2 - new_y1

        remapped_boxes.append(
            (cls, new_x, new_y, new_w, new_h)
        )

    # Save the new annotation file.
    output_file = OUTPUT_DIR / f"{quadrant}.txt"

    with open(output_file, "w", encoding="utf-8") as file:
        for cls, x, y, w, h in remapped_boxes:
            file.write(
                f"{cls} {x:.8f} {y:.8f} "
                f"{w:.8f} {h:.8f}\n"
            )

    print(f"{quadrant}: {len(remapped_boxes)} boxes")
    print(f"Saved: {output_file}")

print("\nAnnotation remapping completed.")
