from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


TARGET_NETS = {
    204: "RX1",
    205: "RX2",
    206: "RX3",
    207: "RX4",
    220: "TX1",
    221: "TX2",
    222: "TX3",
    223: "TX4",
}
COLORS = {
    204: (17, 92, 160),
    205: (37, 118, 189),
    206: (74, 144, 226),
    207: (112, 173, 245),
    220: (173, 35, 35),
    221: (204, 56, 56),
    222: (229, 91, 91),
    223: (245, 132, 132),
}
VIEW = (32.0, 45.0, 67.5, 66.5)
IMAGE_SIZE = (1800, 1160)
LEFT_MARGIN = 80
RIGHT_MARGIN = 80
TOP_MARGIN = 170
BOTTOM_MARGIN = 70


def value(line: str, name: str) -> str | None:
    match = re.search(rf"\|{re.escape(name)}=([^|\r\n]+)", line)
    return match.group(1) if match else None


def mil(line: str, name: str) -> float:
    raw = value(line, name)
    if raw is None or not raw.endswith("mil"):
        raise ValueError(f"missing {name}=...mil")
    return float(raw[:-3]) * 0.0254


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the D79 wide-elevation antenna candidate")
    parser.add_argument("--pcb", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    image = Image.new("RGB", IMAGE_SIZE, (244, 246, 248))
    draw = ImageDraw.Draw(image)
    x_min, y_min, x_max, y_max = VIEW
    width = IMAGE_SIZE[0] - LEFT_MARGIN - RIGHT_MARGIN
    height = IMAGE_SIZE[1] - TOP_MARGIN - BOTTOM_MARGIN
    scale = min(width / (x_max - x_min), height / (y_max - y_min))

    def point(x_mm: float, y_mm: float) -> tuple[int, int]:
        return (
            round(LEFT_MARGIN + (x_mm - x_min) * scale),
            round(IMAGE_SIZE[1] - BOTTOM_MARGIN - (y_mm - y_min) * scale),
        )

    board_box = (*point(10.5, 89.5), *point(89.5, 10.5))
    draw.ellipse(board_box, fill=(255, 255, 255), outline=(83, 94, 104), width=3)

    lines = args.pcb.read_bytes().decode("cp1252").splitlines()
    fills: list[tuple[int, str]] = []
    tracks: list[tuple[int, str]] = []
    for line in lines:
        net_raw = value(line, "NET")
        if net_raw is None or int(net_raw) not in TARGET_NETS or value(line, "LAYER") != "TOP":
            continue
        net = int(net_raw)
        record = value(line, "RECORD")
        if record == "Fill":
            fills.append((net, line))
        elif record == "Track" and int(value(line, "INDEXFORSAVE") or 0) >= 8000:
            tracks.append((net, line))

    for net, line in tracks:
        width_px = max(2, round(mil(line, "WIDTH") * scale))
        draw.line(
            (point(mil(line, "X1"), mil(line, "Y1")), point(mil(line, "X2"), mil(line, "Y2"))),
            fill=COLORS[net],
            width=width_px,
            joint="curve",
        )

    for net, line in fills:
        x1, x2 = mil(line, "X1"), mil(line, "X2")
        y1, y2 = mil(line, "Y1"), mil(line, "Y2")
        left, bottom = point(x1, y1)
        right, top = point(x2, y2)
        draw.rectangle((left, top, right, bottom), fill=COLORS[net], outline=(30, 30, 30), width=1)

    label_font = font(24, bold=True)
    for section in manifest["sections"]:
        x_mm = float(section["x_center_mm"])
        top_mm = float(section["patch_centers_y_mm"][-1]) + float(section["patch_length_mm"]) / 2.0
        px, py = point(x_mm, top_mm + 0.35)
        name = str(section["net_name"]).replace("TI_", "")
        box = draw.textbbox((0, 0), name, font=label_font)
        draw.text((px - (box[2] - box[0]) / 2, py - 24), name, fill=(15, 20, 25), font=label_font)

    title_font = font(34, bold=True)
    body_font = font(23)
    draw.rounded_rectangle((50, 30, 1750, 128), radius=14, fill=(255, 255, 255), outline=(185, 191, 197), width=2)
    draw.text((78, 45), "Антенный узел D79, ревизия 0.8.0", fill=(18, 29, 38), font=title_font)
    draw.text(
        (78, 91),
        "8 элементов на канал, 64 элемента, расчётный сектор по углу места не менее ±20°",
        fill=(55, 65, 74),
        font=body_font,
    )
    draw.text(
        (78, 1100),
        "Синий: RX. Красный: TX. Расчётная геометрия, полный электромагнитный расчёт не выполнен.",
        fill=(65, 72, 80),
        font=body_font,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
