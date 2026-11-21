
from pathlib import Path
from collections import Counter

root = Path("data/raw/RDD-India")

class_names = {
    0: "D00",
    1: "D20",
    2: "D40",
    3: "D44"
}

for split in ["train", "valid", "test"]:

    counts = Counter()
    total = 0
    invalid = 0

    label_dir = root / split / "labels"

    for file in label_dir.glob("*.txt"):

        for line in file.read_text().splitlines():

            parts = line.split()

            if not parts:
                continue

            try:
                class_id = int(parts[0])

                counts[class_id] += 1
                total += 1

            except (ValueError, IndexError):
                invalid += 1

    print(f"\n{split.upper()}")
    print("-" * 35)

    print("Total bounding boxes:", total)

    for class_id, name in class_names.items():
        print(f"{name}: {counts[class_id]}")

    print("Invalid class entries:", invalid)
