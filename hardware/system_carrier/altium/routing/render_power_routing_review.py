import argparse
import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


NET_COLORS = {
    "VIN_RAW": "#e63946",
    "VIN_PROTECTED": "#f4a261",
    "RADAR_12V": "#ffd166",
    "3V3": "#2a9d8f",
    "BUCK_SW": "#9b5de5",
    "GND": "#457b9d",
}
LAYERS = [(1, "Top Layer"), (2, "Mid Layer 1"), (3, "Mid Layer 2"), (32, "Bottom Layer")]


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path(__file__).parent)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "power_routing_review_a.png")
    args = parser.parse_args()

    pads = read_csv(args.input_dir / "pad_geometry.csv")
    fills = read_csv(args.input_dir / "fill_inventory.csv")
    vias = read_csv(args.input_dir / "via_inventory.csv")

    xs = [float(row["x_mil"]) for row in pads]
    ys = [float(row["y_mil"]) for row in pads]
    margin = 120.0
    xmin, xmax = min(xs) - margin, max(xs) + margin
    ymin, ymax = min(ys) - margin, max(ys) + margin

    image = Image.new("RGB", (1800, 1200), "#10151c")
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default()
    panel_width, panel_height = 860, 520
    origins = [(40, 80), (900, 80), (40, 640), (900, 640)]

    def point(x, y, origin):
        ox, oy = origin
        px = ox + 30 + (x - xmin) / (xmax - xmin) * (panel_width - 60)
        py = oy + panel_height - 30 - (y - ymin) / (ymax - ymin) * (panel_height - 60)
        return px, py

    draw.text((40, 28), "EVT SYS CARRIER power routing review A", fill="#f1faee", font=font)
    legend_x = 520
    for net, color in NET_COLORS.items():
        draw.rectangle((legend_x, 24, legend_x + 18, 42), fill=color)
        draw.text((legend_x + 24, 27), net, fill="#f1faee", font=font)
        legend_x += 155

    for (layer, title), origin in zip(LAYERS, origins):
        ox, oy = origin
        draw.rectangle((ox, oy, ox + panel_width, oy + panel_height), fill="#18212b", outline="#8191a3", width=2)
        draw.text((ox + 12, oy + 10), title, fill="#f1faee", font=font)

        for pad in pads:
            if int(pad["layer"]) not in (layer, 74):
                continue
            x, y = point(float(pad["x_mil"]), float(pad["y_mil"]), origin)
            color = NET_COLORS.get(pad["net_name"], "#54606d")
            radius = 2.5 if pad["net_name"] in NET_COLORS else 1.2
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

        for fill in fills:
            if int(fill["layer"]) != layer:
                continue
            x1, y1 = point(float(fill["x1_mil"]), float(fill["y1_mil"]), origin)
            x2, y2 = point(float(fill["x2_mil"]), float(fill["y2_mil"]), origin)
            color = NET_COLORS.get(fill["net_name"], "#ffffff")
            draw.rectangle((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)), fill=color + "88", outline=color, width=2)

        for via in vias:
            low, high = int(via["low_layer"]), int(via["high_layer"])
            if not low <= layer <= high:
                continue
            x, y = point(float(via["x_mil"]), float(via["y_mil"]), origin)
            color = NET_COLORS.get(via["net_name"], "#ffffff")
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), outline=color, width=2)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)


if __name__ == "__main__":
    main()
