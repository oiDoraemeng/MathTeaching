from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))

from linear_algebra.catalog.drawing_index import load_drawing_catalog, validate_drawing_catalog


def main() -> int:
    path = Path(__file__).parents[1] / "openspec" / "changes" / "extend-linear-algebra-chapters-4-8" / "drawing-catalog.md"
    entries = load_drawing_catalog(path)
    errors = validate_drawing_catalog(entries)
    counts = [sum(item.chapter_number == chapter for item in entries) for chapter in range(4, 9)]
    print(f"{len(entries)} topics; {'/'.join(map(str, counts))}; {len(errors)} duplicates")
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
