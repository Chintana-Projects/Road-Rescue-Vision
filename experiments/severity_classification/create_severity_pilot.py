
from pathlib import Path
import csv
import random

BASE = Path(__file__).resolve().parent

SOURCE = BASE / "annotations" / "severity_labels.csv"
OUTPUT = BASE / "annotations" / "severity_pilot.csv"

CLASSES = ["D00", "D20", "D40", "D44"]
SAMPLES_PER_CLASS = 5

random.seed(42)

with open(SOURCE, "r", newline="", encoding="utf-8") as file:
    rows = list(csv.DictReader(file))

pilot = []

for class_name in CLASSES:

    available = [
        row for row in rows
        if row["split"] == "train"
        and row["damage_class"] == class_name
    ]

    selected = random.sample(
        available,
        min(SAMPLES_PER_CLASS, len(available))
    )

    pilot.extend(selected)

fieldnames = [
    "split",
    "crop_name",
    "damage_class",
    "crop_path",
    "visual_severity",
    "review_status",
    "annotator_notes"
]

with open(OUTPUT, "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(pilot)

print("\nSEVERITY PILOT CREATED")
print("Total samples:", len(pilot))
print("Output:", OUTPUT)

for class_name in CLASSES:
    count = sum(
        1 for row in pilot
        if row["damage_class"] == class_name
    )
    print(class_name, ":", count)
