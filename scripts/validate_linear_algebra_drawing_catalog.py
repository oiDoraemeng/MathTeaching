from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))

from linear_algebra.catalog.drawing_index import load_drawing_catalog, validate_drawing_catalog


def main() -> int:
    root = Path(__file__).parents[1]
    candidates = sorted(root.glob("openspec/changes/archive/*-extend-linear-algebra-chapters-4-8/drawing-catalog.md"))
    if not candidates:
        raise FileNotFoundError("No archived linear algebra drawing catalog found")
    path = candidates[-1]
    entries = load_drawing_catalog(path)
    errors = validate_drawing_catalog(entries)
    counts = [sum(item.chapter_number == chapter for item in entries) for chapter in range(4, 9)]
    print(f"{len(entries)} topics; {'/'.join(map(str, counts))}; {len(errors)} duplicates")
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
