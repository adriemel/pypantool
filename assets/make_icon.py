"""Draw the PyPanTool icon and write assets/pypantool.ico and pypantool.png.

Run:  python assets/make_icon.py
The icon is a teal tile with a simplified PANGAEA logo (red-to-yellow ellipse,
continents in flat green) and the word "pantool".  The .ico holds 16-256 px
images; sizes below 64 px show the logo only, because the word is not
readable that small.
"""

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)

PAPER, TEAL, TEAL_DARK = "#FBFAF7", "#0E6B6B", "#0A5252"
LAND = "#2E9483"
# Ocean of the logo: yellow centre to red rim (colours sampled from the logo).
OCEAN = ((0.0, "#F5C400"), (0.45, "#EC9F00"), (0.78, "#DD4A08"), (1.0, "#BF0D0D"))
ASPECT = 760 / 460           # width / height of the logo ellipse
SIZES = (16, 24, 32, 48, 64, 128, 256)

# Simplified outline of the continents, traced from the logo on
# www.pangaea.de (white = land).  Covers exactly the ellipse's bounding box.
_MASK_FILE = Path(__file__).parent / "pangaea_logo_land.png"


def _land_image(width: int, height: int) -> QImage:
    """Land in flat colour, transparent elsewhere, scaled to the ellipse box."""
    mask = QImage(str(_MASK_FILE)).convertToFormat(QImage.Format.Format_Grayscale8)
    mask = mask.scaled(width, height, Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    land = QImage(width, height, QImage.Format.Format_ARGB32)
    land.fill(QColor(LAND))
    land.setAlphaChannel(mask)
    return land


def draw(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    with_text = size >= 64

    # Teal tile.
    inset = size * 0.03
    tile = QRectF(inset, inset, size - 2 * inset, size - 2 * inset)
    p.setPen(QPen(QColor(TEAL_DARK), max(1.0, size / 128)))
    p.setBrush(QColor(TEAL))
    p.drawRoundedRect(tile, size * 0.16, size * 0.16)

    # Logo ellipse: gradient ocean, flat land.
    width = size * (0.80 if with_text else 0.86)
    height = width / ASPECT
    left = (size - width) / 2
    top = size * 0.15 if with_text else (size - height) / 2
    box = QRectF(left, top, width, height)
    ocean = QRadialGradient(box.center(), width / 2)
    for stop, colour in OCEAN:
        ocean.setColorAt(stop, QColor(colour))
    ellipse = QPainterPath()
    ellipse.addEllipse(box)
    p.setPen(Qt.PenStyle.NoPen)
    # A radial gradient is circular; squash it to follow the ellipse.
    p.save()
    p.translate(box.center())
    p.scale(1.0, height / width)
    p.translate(-box.center())
    circle = QPainterPath()
    circle.addEllipse(box.center(), width / 2, width / 2)
    p.fillPath(circle, ocean)
    p.restore()
    p.setClipPath(ellipse)
    p.drawImage(box.topLeft(), _land_image(round(width), round(height)))
    p.setClipping(False)

    if with_text:
        font = QFont(["Segoe UI", "Inter", "Arial"])
        font.setBold(True)
        font.setPixelSize(round(size * 0.185))
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 97)
        p.setFont(font)
        p.setPen(QColor(PAPER))
        p.drawText(QRectF(0, size * 0.68, size, size * 0.24),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, "pantool")
    p.end()
    return image


def _png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def main() -> None:
    app = QGuiApplication(sys.argv)  # noqa: F841 (needed for fonts)
    out = Path(__file__).parent
    pngs = [(size, _png_bytes(draw(size))) for size in SIZES]

    # ICO container with PNG-compressed entries.
    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = len(header) + 16 * len(pngs)
    entries, blobs = b"", b""
    for size, png in pngs:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32,
                               len(png), offset)
        blobs += png
        offset += len(png)
    (out / "pypantool.ico").write_bytes(header + entries + blobs)
    (out / "pypantool.png").write_bytes(pngs[-1][1])
    print("written:", out / "pypantool.ico", out / "pypantool.png")


if __name__ == "__main__":
    main()
