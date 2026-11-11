"""Draw the PyPanTool icon and write assets/pypantool.ico and pypantool.png.

Run:  python assets/make_icon.py
The .ico holds 16-256 px images; sizes below 64 px show the globe only,
because the word "pantool" is not readable that small.
"""

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPainterPath, QPen

PAPER, INK, TEAL, RULE = "#FBFAF7", "#1D2126", "#0E6B6B", "#B9B4A7"
SIZES = (16, 24, 32, 48, 64, 128, 256)

# Simplified Pangaea on a 100 x 100 globe: Laurasia in the north, Gondwana in
# the south, the Tethys Sea opening to the east.  (x, y) outline points.
_LAND = [
    (38, 6), (58, 9), (74, 18), (84, 30), (80, 38), (66, 40), (58, 46),
    (62, 54), (76, 58), (86, 66), (82, 78), (70, 88), (56, 95), (44, 92),
    (38, 80), (30, 68), (24, 56), (20, 44), (16, 32), (22, 18),
]


def _land_path(scale: float, dx: float, dy: float) -> QPainterPath:
    """Closed smooth outline through the _LAND points."""
    pts = [QPointF(dx + x * scale, dy + y * scale) for x, y in _LAND]
    path = QPainterPath()
    n = len(pts)
    mid = lambda a, b: QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
    path.moveTo(mid(pts[-1], pts[0]))
    for i in range(n):
        path.quadTo(pts[i], mid(pts[i], pts[(i + 1) % n]))
    path.closeSubpath()
    return path


def draw(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    with_text = size >= 64

    if with_text:
        # Paper tile so the icon reads on any desktop background.
        inset = size * 0.03
        tile = QRectF(inset, inset, size - 2 * inset, size - 2 * inset)
        p.setPen(QPen(QColor(RULE), max(1.0, size / 128)))
        p.setBrush(QColor(PAPER))
        p.drawRoundedRect(tile, size * 0.14, size * 0.14)
        diameter = size * 0.60
        left, top = (size - diameter) / 2, size * 0.09
    else:
        diameter = size - 1.0
        left = top = 0.5

    globe = QPainterPath()
    globe.addEllipse(QRectF(left, top, diameter, diameter))
    p.setPen(Qt.PenStyle.NoPen)
    p.fillPath(globe, QColor(TEAL))
    p.setClipPath(globe)
    p.fillPath(_land_path(diameter / 100, left, top), QColor(PAPER))
    p.setClipping(False)

    if with_text:
        font = QFont(["Segoe UI", "Inter", "Arial"])
        font.setBold(True)
        font.setPixelSize(round(size * 0.185))
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 97)
        p.setFont(font)
        p.setPen(QColor(INK))
        p.drawText(QRectF(0, size * 0.70, size, size * 0.24),
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
