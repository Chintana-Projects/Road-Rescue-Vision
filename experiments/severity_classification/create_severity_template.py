
from pathlib import Path
import csv
from collections import Counter

BASE = Path(__file__).resolve().parent

metadata_path = (
    BASE / "annotations" / "expanded_crop_metadata.csv"
)

output_path = (
    BASE / "annotations" / "severity_labels.csv"
)

if not metadata_path.exists():
    raise FileNotFoundError(
        f"Metadata file not found: {metadata_path}"
    )

total = 0
split_counts = Counter()
class_counts = Counter()

with open(metadata_path, "r", newline="", encoding="utf-8") as source:
    reader = csv.DictReader(source)

    with open(output_path, "w", newline="", encoding="utf-8") as destination:

        fieldnames = [
            "split",
            "crop_name",
            "damage_class",
            "crop_path",
            "visual_severity",
            "review_status",
            "annotator_notes"
        ]

        writer = csv.DictWriter(
            destination,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for row in reader:

            writer.writerow({
                "split": row["split"],
                "crop_name": row["crop_name"],
                "damage_class": row["damage_class"],
                "crop_path": row["crop_path"],
                "visual_severity": "",
                "review_status": "PENDING",
                "annotator_notes": ""
            })

            total += 1
            split_counts[row["split"]] += 1
            class_counts[row["damage_class"]] += 1

print("\nSEVERITY ANNOTATION TEMPLATE CREATED")
print("Total records:", total)
print("Output:", output_path)

print("\nRecords by split:")
for split, count in sorted(split_counts.items()):
    print(split, ":", count)

print("\nRecords by damage class:")
for class_name, count in sorted(class_counts.items()):
    print(class_name, ":", count)
