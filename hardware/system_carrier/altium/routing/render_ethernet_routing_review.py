import argparse
import csv
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


NET_COLORS = {
    "ETH_TXP": "#00d9ff",
    "ETH_TXN": "#2f80ed",
    "ETH_RXP": "#ffb347",
    "ETH_RXN": "#ff5d73",
}


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def draw_dashed_line(draw, start, end, fill, width, dash=10, gap=7):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return
    distance = 0
    while distance < length:
        segment_end = min(distance + dash, length)
        a = distance / length
        b = segment_end / length
        draw.line(
            (
                start[0] + dx * a,
                start[1] + dy * a,
                start[0] + dx * b,
                start[1] + dy * b,
            ),
            fill=fill,
            width=width,
        )
        distance += dash + gap


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path(__file__).parent)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "ethernet_routing_review_a.png",
    )
    args = parser.parse_args()

    pads = read_csv(args.input_dir / "pad_geometry.csv")
    tracks = read_csv(args.input_dir / "track_inventory.csv")
    fills = read_csv(args.input_dir / "fill_inventory.csv")
    vias = read_csv(args.input_dir / "via_inventory.csv")

    image = Image.new("RGB", (1600, 900), "#0e141b")
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default()
    draw.text((44, 28), "EVT SYS CARRIER Ethernet MDI routing review A", fill="#f4f7fb", font=font)
    draw.text(
        (44, 50),
        "0.26 mm width, 0.20 mm pair gap, native Altium DRC baseline retained",
        fill="#b6c2d0",
        font=font,
    )

    panels = [
        ((40, 85, 780, 850), (0.0, 4200.0, 0.0, 3200.0), "Full board"),
        ((820, 85, 1560, 850), (2650.0, 4200.0, 2000.0, 2850.0), "U3, terminations, D3 and J6"),
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
            x1, y1 = float(fill["x1_mil"]), float(fill["y1_mil"])
            x2, y2 = float(fill["x2_mil"]), float(fill["y2_mil"])
            if max(x1, x2) < xmin or min(x1, x2) > xmax or max(y1, y2) < ymin or min(y1, y2) > ymax:
                continue
            p1 = point(x1, y1, rect, bounds)
            p2 = point(x2, y2, rect, bounds)
            draw.rectangle(
                (min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])),
                fill="#56708518",
                outline="#56708535",
            )

        for track in tracks:
            x1, y1 = float(track["x1_mil"]), float(track["y1_mil"])
            x2, y2 = float(track["x2_mil"]), float(track["y2_mil"])
            if max(x1, x2) < xmin or min(x1, x2) > xmax or max(y1, y2) < ymin or min(y1, y2) > ymax:
                continue
            p1 = point(x1, y1, rect, bounds)
            p2 = point(x2, y2, rect, bounds)
            net = track["net_name"]
            if net in NET_COLORS:
                scale = (right - left - 60) / (xmax - xmin)
                width = max(3, round(float(track["width_mil"]) * scale))
                if int(track["layer"]) == 32:
                    draw_dashed_line(draw, p1, p2, NET_COLORS[net], width)
                else:
                    draw.line((p1[0], p1[1], p2[0], p2[1]), fill=NET_COLORS[net], width=width)
            elif title == "Full board":
                draw.line((p1[0], p1[1], p2[0], p2[1]), fill="#75879a35", width=1)

        for pad in pads:
            x, y = float(pad["x_mil"]), float(pad["y_mil"])
            if not xmin <= x <= xmax or not ymin <= y <= ymax:
                continue
            px, py = point(x, y, rect, bounds)
            net = pad["net_name"]
            connected = net in NET_COLORS
            radius = 5 if connected else 1.5
            color = NET_COLORS.get(net, "#718096")
            draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color)
            if title.startswith("U3") and pad["designator"] in {"U3", "D3", "J6", "R601", "R602", "R603", "R604"} and connected:
                draw.text((px + 6, py - 11), f'{pad["designator"]}-{pad["pad_name"]}', fill="#f4f7fb", font=font)

        for via in vias:
            if via["net_name"] not in NET_COLORS:
                continue
            x, y = float(via["x_mil"]), float(via["y_mil"])
            if not xmin <= x <= xmax or not ymin <= y <= ymax:
                continue
            px, py = point(x, y, rect, bounds)
            draw.ellipse((px - 5, py - 5, px + 5, py + 5), outline="#ffffff", width=2)

    legend_x = 900
    for index, (net, color) in enumerate(NET_COLORS.items()):
        y = 31 + index * 16
        draw.line((legend_x, y + 6, legend_x + 24, y + 6), fill=color, width=4)
        draw.text((legend_x + 32, y), net, fill="#f4f7fb", font=font)
    draw.text((1240, 31), "Solid: Top Layer", fill="#f4f7fb", font=font)
    draw_dashed_line(draw, (1240, 55), (1270, 55), "#f4f7fb", 3, dash=6, gap=4)
    draw.text((1280, 49), "Dashed: Bottom Layer", fill="#f4f7fb", font=font)
    draw.ellipse((1240, 73, 1250, 83), outline="#ffffff", width=2)
    draw.text((1260, 70), "Via", fill="#f4f7fb", font=font)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)


if __name__ == "__main__":
    main()
