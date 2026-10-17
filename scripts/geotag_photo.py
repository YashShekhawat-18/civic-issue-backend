"""Put a GPS position into a JPEG, or read the one it has. For demos and testing the geotag rule.

  python scripts/geotag_photo.py show   photo.jpg
  python scripts/geotag_photo.py set    photo.jpg 19.1867 73.1920 [out.jpg]

`set` writes a new file (default: photo-geotagged.jpg). The original is not changed.
Only JPEG files can carry the position the app reads.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.geotag_service import read_gps, write_gps  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[1] == "show":
        position = read_gps(Path(argv[2]).read_bytes())
        print("No GPS location in this photo" if position is None else f"Latitude {position[0]:.6f}, longitude {position[1]:.6f}")
        return 0
    if len(argv) >= 5 and argv[1] == "set":
        source = Path(argv[2])
        target = Path(argv[5]) if len(argv) > 5 else source.with_name(source.stem + "-geotagged.jpg")
        target.write_bytes(write_gps(source.read_bytes(), float(argv[3]), float(argv[4])))
        print(f"Wrote {target}")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
