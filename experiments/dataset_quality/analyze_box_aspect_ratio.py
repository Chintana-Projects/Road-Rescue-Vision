from pathlib import Path
from collections import defaultdict
import statistics

root = Path("data/raw/RDD-India")
ratios = defaultdict(list)

for split in ["train", "valid", "test"]:
    label_dir = root / split / "labels"

    for file in label_dir.glob("*.txt"):
        for line in file.read_text().splitlines():
            parts = line.split()

            if not parts:
                continue

            class_id = int(parts[0])
            width = float(parts[3])
            height = float(parts[4])

            ratio = width / height
            ratios[class_id].append(ratio)

print("BOUNDING BOX ASPECT RATIO ANALYSIS")
print("=" * 55)

for class_id in range(4):
    values = ratios[class_id]

    print(f"\nClass {class_id}")
    print("Number of boxes:", len(values))
    print("Minimum ratio:", round(min(values), 3))
    print("Median ratio:", round(statistics.median(values), 3))
    print("Maximum ratio:", round(max(values), 3))
    print("Very tall boxes (< 0.2):", sum(r < 0.2 for r in values))
    print("Very wide boxes (> 5):", sum(r > 5 for r in values))