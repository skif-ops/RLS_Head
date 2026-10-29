import argparse
import csv
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


TARGET_COLORS = {
    "GNSS_PPS": "#31c48d",
    "IMU_DRDY": "#a78bfa",
    "RADAR_REF": "#f97316",
}
QUIET_COLORS = {
    "BUCK_SW": "#ef4444",
    "ETH_TXP": "#00d9ff",
    "ETH_TXN": "#2f80ed",
    "ETH_RXP": "#ffb347",
    "ETH_RXN": "#ff5d73",
}


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    default_input = Path(__file__).parent / "connection_audit"
    parser.add_argument("--input-dir", type=Path, default=default_input)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "timing_routing_review_a.png",
    )
    args = parser.parse_args()

    pads = read_csv(args.input_dir / "pad_geometry.csv")
    tracks = read_csv(args.input_dir / "track_inventory.csv")
    fills = read_csv(args.input_dir / "fill_inventory.csv")
    vias = read_csv(args.input_dir / "via_inventory.csv")
    image = Image.new("RGB", (1600, 1040), "#0e141b")
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default()
    draw.text(
        (46, 26),
        "EVT SYS CARRIER timing routing review A",
        fill="#f4f7fb",
        font=font,
    )
    draw.text(
        (46, 49),
        "GNSS_PPS, IMU_DRDY and RADAR_REF, multilayer view, 0.20 mm width",
        fill="#b6c2d0",
        font=font,
    )

    board = (55, 92, 1545, 1010)
    margin = 36
    xmin, xmax = 0.0, 3937.008
    ymin, ymax = 0.0, 3149.606

    def point(x, y):
        left, top, right, bottom = board
        px = left + margin + (x - xmin) / (xmax - xmin) * (right - left - 2 * margin)
        py = bottom - margin - (y - ymin) / (ymax - ymin) * (bottom - top - 2 * margin)
        return px, py

    draw.rectangle(board, fill="#17212b", outline="#9fb3c8", width=2)
    for fill in fills:
        if int(fill["layer"]) != 1:
            continue
        first = point(float(fill["x1_mil"]), float(fill["y1_mil"]))
        second = point(float(fill["x2_mil"]), float(fill["y2_mil"]))
        color = QUIET_COLORS.get(fill["net_name"], "#56708520")
        draw.rectangle(
            (
                min(first[0], second[0]),
                min(first[1], second[1]),
                max(first[0], second[0]),
                max(first[1], second[1]),
            ),
            fill=color + "30" if len(color) == 7 else color,
            outline=color,
            width=1,
        )

    scale = (board[2] - board[0] - 2 * margin) / (xmax - xmin)
    for track in tracks:
        layer = int(track["layer"])
        if layer != 1 and track["net_name"] not in TARGET_COLORS:
            continue
        first = point(float(track["x1_mil"]), float(track["y1_mil"]))
        second = point(float(track["x2_mil"]), float(track["y2_mil"]))
        net = track["net_name"]
        if net in TARGET_COLORS:
            alpha = {1: "FF", 2: "D0", 3: "A0", 32: "80"}.get(layer, "70")
            color = TARGET_COLORS[net] + alpha
            width = max(4, round(float(track["width_mil"]) * scale))
        elif net in QUIET_COLORS:
            color = QUIET_COLORS[net] + "B0"
            width = max(2, round(float(track["width_mil"]) * scale))
        else:
            color = "#71809628"
            width = 1
        draw.line((*first, *second), fill=color, width=width)

    for via in vias:
        net = via["net_name"]
        if net not in TARGET_COLORS:
            continue
        px, py = point(float(via["x_mil"]), float(via["y_mil"]))
        radius = max(4, round(float(via["size_mil"]) * scale / 2.0))
        draw.ellipse(
            (px - radius, py - radius, px + radius, py + radius),
            fill="#0e141b",
            outline=TARGET_COLORS[net],
            width=2,
        )

    for pad in pads:
        x = float(pad["x_mil"])
        y = float(pad["y_mil"])
        px, py = point(x, y)
        net = pad["net_name"]
        if net in TARGET_COLORS:
            radius = 6
            color = TARGET_COLORS[net]
        elif net in QUIET_COLORS:
            radius = 3
            color = QUIET_COLORS[net]
        else:
            radius = 1.2
            color = "#75879a90"
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color)
        if net in TARGET_COLORS:
            designator = pad["designator"] or "J4"
            label_y = py - 12
            if designator == "U1" and net == "IMU_DRDY":
                label_y = py - 26
            elif designator == "U1" and net == "RADAR_REF":
                label_y = py + 8
            draw.text(
                (px + 8, label_y),
                f'{designator}-{pad["pad_name"]}',
                fill="#f4f7fb",
                font=font,
            )

    legend_x = 1040
    for index, (net, color) in enumerate(TARGET_COLORS.items()):
        y = 27 + index * 19
        draw.line((legend_x, y + 6, legend_x + 30, y + 6), fill=color, width=5)
        length = sum(
            math.hypot(
                float(row["x2_mil"]) - float(row["x1_mil"]),
                float(row["y2_mil"]) - float(row["y1_mil"]),
            ) * 0.0254
            for row in tracks
            if row["net_name"] == net
        )
        segments = sum(1 for row in tracks if row["net_name"] == net)
        via_count = sum(1 for row in vias if row["net_name"] == net)
        layers = sorted({int(row["layer"]) for row in tracks if row["net_name"] == net})
        draw.text(
            (legend_x + 40, y),
            f"{net}: {length:.3f} mm, {segments} segments, {via_count} vias, L{layers}",
            fill="#f4f7fb",
            font=font,
        )
    draw.text(
        (55, 1017),
        "Red: BUCK_SW. Blue, cyan, amber and rose: Ethernet MDI corridor.",
        fill="#b6c2d0",
        font=font,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)


if __name__ == "__main__":
    main()
