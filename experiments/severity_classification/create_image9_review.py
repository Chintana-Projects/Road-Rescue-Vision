import csv
from pathlib import Path

image_name = (
    "India_004701_jpg.rf."
    "9e80acb81548f93578dffc4f6a8f56ae.jpg"
)

# Original class IDs from the YOLO label file
class_ids = [2, 2, 2, 1, 2, 1]

output_path = Path(
    "experiments/severity_classification/annotations/image9_review.csv"
)

output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)

    writer.writerow([
        "image",
        "box_number",
        "class_id",
        "review_status",
        "observed_content",
        "notes"
    ])

    for box_number, class_id in enumerate(class_ids, start=1):
        writer.writerow([
            image_name,
            box_number,
            class_id,
            "UNVERIFIABLE",
            "Overlay and smooth-looking road",
            "Dark semi-transparent overlay blocks reliable inspection; "
            "no visible defect can be confirmed"
        ])

print("Saved:", output_path)
print("Reviewed annotations:", len(class_ids))