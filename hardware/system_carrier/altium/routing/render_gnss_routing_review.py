import argparse
import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path(__file__).parent)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "gnss_routing_review_a.png",
    )
    args = parser.parse_args()

    pads = read_csv(args.input_dir / "pad_geometry.csv")
    tracks = [
        row
        for row in read_csv(args.input_dir / "track_inventory.csv")
        if row["net_name"] == "GNSS_RF"
    ]
    fills = read_csv(args.input_dir / "fill_inventory.csv")

    image = Image.new("RGB", (1600, 900), "#0e141b")
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default()
    draw.text((44, 28), "EVT SYS CARRIER GNSS RF routing review A", fill="#f4f7fb", font=font)
    draw.text((44, 50), "Top layer, 0.36 mm controlled-width start geometry, 0 vias", fill="#b6c2d0", font=font)

    panels = [
        ((40, 85, 780, 850), (0.0, 4200.0, 0.0, 3200.0), "Full board"),
        ((820, 85, 1560, 850), (80.0, 1320.0, 2020.0, 2780.0), "GNSS corridor J8-D8-L80-U8"),
    ]

    def point(x, y, rect, bounds):
        left, top, right, bottom = rect
        xmin, xmax, ymin, ymax = bounds
        px = left + 30 + (x - xmin) / (xmax - xmin) * (right - left - 60)
        py = bottom - 30 - (y - ymin) / (ymax - ymin) * (bottom - top - 60)
        return px, py

    for rect, bounds, title in panels:
        left, top, right, bottom = rect
        xmin, xmax, ymin, ymax = bounds
        draw.rectangle(rect, fill="#17212b", outline="#7f92a8", width=2)
        draw.text((left + 14, top + 12), title, fill="#f4f7fb", font=font)

        for fill in fills:
            if int(fill["layer"]) != 1:
                continue
            x1, y1 = float(fill["x1_mil"]), float(fill["y1_mil"])
            x2, y2 = float(fill["x2_mil"]), float(fill["y2_mil"])
            if max(x1, x2) < xmin or min(x1, x2) > xmax or max(y1, y2) < ymin or min(y1, y2) > ymax:
                continue
            p1 = point(x1, y1, rect, bounds)
            p2 = point(x2, y2, rect, bounds)
            draw.rectangle(
                (min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])),
                fill="#56708522",
                outline="#56708555",
            )

        for pad in pads:
            if int(pad["layer"]) != 1:
                continue
            x, y = float(pad["x_mil"]), float(pad["y_mil"])
            if not xmin <= x <= xmax or not ymin <= y <= ymax:
                continue
            px, py = point(x, y, rect, bounds)
            connected = pad["net_name"] == "GNSS_RF"
            radius = 5 if connected else 1.4
            color = "#ffd166" if connected else "#718096"
            draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color)
            if title.startswith("GNSS") and pad["designator"] in {"J8", "D8", "L80", "U8"}:
                draw.text((px + 7, py - 12), f'{pad["designator"]}-{pad["pad_name"]}', fill="#f4f7fb", font=font)

        for track in tracks:
            x1, y1 = float(track["x1_mil"]), float(track["y1_mil"])
            x2, y2 = float(track["x2_mil"]), float(track["y2_mil"])
            p1 = point(x1, y1, rect, bounds)
            p2 = point(x2, y2, rect, bounds)
            scale = (right - left - 60) / (xmax - xmin)
            width = max(3, round(float(track["width_mil"]) * scale))
            draw.line((p1[0], p1[1], p2[0], p2[1]), fill="#00d9ff", width=width)

    draw.rectangle((1180, 31, 1202, 43), fill="#00d9ff")
    draw.text((1212, 30), "GNSS_RF", fill="#f4f7fb", font=font)
    draw.ellipse((1330, 30, 1342, 42), fill="#ffd166")
    draw.text((1352, 30), "GNSS_RF pad", fill="#f4f7fb", font=font)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)


if __name__ == "__main__":
    main()
