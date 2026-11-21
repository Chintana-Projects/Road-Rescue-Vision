from pathlib import Path
from collections import Counter

root = Path("data/raw/RDD-India")

for split in ["train", "valid", "test"]:
    label_dir = root / split / "labels"

    box_counts = []

    for file in label_dir.glob("*.txt"):
        lines = [
            line for line in file.read_text().splitlines()
            if line.strip()
        ]

        box_counts.append((file.name, len(lines)))

    counts = [count for _, count in box_counts]

    print(f"\n{split.upper()} SPLIT")
    print("=" * 45)
    print("Total images:", len(counts))
    print("Images with zero boxes:", sum(c == 0 for c in counts))
    print("Images with 1-5 boxes:", sum(1 <= c <= 5 for c in counts))
    print("Images with 6-10 boxes:", sum(6 <= c <= 10 for c in counts))
    print("Images with more than 10 boxes:", sum(c > 10 for c in counts))
    print("Maximum boxes in one image:", max(counts))

    print("\nTop 10 images with most boxes:")
    for filename, count in sorted(
        box_counts, key=lambda item: item[1], reverse=True
    )[:10]:
        print(filename, "->", count)