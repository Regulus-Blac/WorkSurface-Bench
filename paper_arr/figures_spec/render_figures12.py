"""Render publication-ready vector versions of Figures 1 and 2.

The diagrams are intentionally code-generated so the manuscript assets and
their numeric annotations can be audited and regenerated without a slide
editor.  Run from anywhere with::

    python3 paper_arr/figures_spec/render_figures12.py
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white


HERE = Path(__file__).resolve().parent
PAPER_DIR = HERE.parent
PAGE = (864, 270)
FIGURE2_PAGE = (864, 225)

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
pdfmetrics.registerFont(TTFont("TNR", str(FONT_DIR / "Times New Roman.ttf")))
pdfmetrics.registerFont(TTFont("TNR-Bold", str(FONT_DIR / "Times New Roman Bold.ttf")))
pdfmetrics.registerFont(TTFont("TNR-Italic", str(FONT_DIR / "Times New Roman Italic.ttf")))

INK = HexColor("#1F2937")
MUTED = HexColor("#667085")
LIGHT_TEXT = HexColor("#98A2B3")
BORDER = HexColor("#D0D5DD")
PANEL = HexColor("#F8FAFC")
BLUE = HexColor("#56B4E9")
BLUE_DARK = HexColor("#2878A8")
BLUE_BG = HexColor("#EDF7FC")
ORANGE = HexColor("#E69F00")
ORANGE_BG = HexColor("#FFF8E7")
GREEN = HexColor("#009E73")
GREEN_BG = HexColor("#ECFDF5")
PURPLE = HexColor("#7A5195")
PURPLE_BG = HexColor("#F5F0F8")
SLATE = HexColor("#475467")
SLATE_BG = HexColor("#F2F4F7")


def _text(c, x, y, value, size=12, font="TNR", color=INK, align="left"):
    c.setFont(font, size)
    c.setFillColor(color)
    if align == "center":
        c.drawCentredString(x, y, value)
    elif align == "right":
        c.drawRightString(x, y, value)
    else:
        c.drawString(x, y, value)


def _round_card(c, x, y, w, h, fill=white, stroke=BORDER, radius=10,
                line_width=1.2, shadow=False):
    if shadow:
        c.setFillColor(HexColor("#EAECF0"))
        c.setStrokeColor(HexColor("#EAECF0"))
        c.roundRect(x + 2, y - 2, w, h, radius, fill=1, stroke=0)
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(line_width)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def _arrow(c, x1, y1, x2, y2, color=SLATE, width=1.8, head=6):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2 - head, y2)
    c.line(x2 - head, y2 + head * 0.55, x2, y2)
    c.line(x2 - head, y2 - head * 0.55, x2, y2)
    p = c.beginPath()
    p.moveTo(x2 - head, y2 + head * 0.55)
    p.lineTo(x2, y2)
    p.lineTo(x2 - head, y2 - head * 0.55)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def _down_arrow(c, x, y1, y2, color=LIGHT_TEXT, width=1.4, head=5):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.line(x, y1, x, y2 + head)
    p = c.beginPath()
    p.moveTo(x - head * 0.55, y2 + head)
    p.lineTo(x, y2)
    p.lineTo(x + head * 0.55, y2 + head)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def _up_arrow(c, x, y1, y2, color=LIGHT_TEXT, width=1.4, head=5):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.line(x, y1, x, y2 - head)
    p = c.beginPath()
    p.moveTo(x - head * 0.55, y2 - head)
    p.lineTo(x, y2)
    p.lineTo(x + head * 0.55, y2 - head)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def _file_icon(c, x, y, label, accent=LIGHT_TEXT, w=33, h=42):
    c.setFillColor(white)
    c.setStrokeColor(BORDER)
    c.setLineWidth(1.0)
    c.roundRect(x, y, w, h, 4, fill=1, stroke=1)
    c.setFillColor(accent)
    c.rect(x, y + h - 5, w, 5, fill=1, stroke=0)
    c.setStrokeColor(HexColor("#CBD5E1"))
    c.setLineWidth(1.1)
    c.line(x + 7, y + h - 14, x + w - 7, y + h - 14)
    c.line(x + 7, y + h - 20, x + w - 10, y + h - 20)
    _text(c, x + w / 2, y + 6, label, 10.5, "TNR-Bold", MUTED, "center")


def _surface_icon(c, kind, x, y, color):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(1.5)
    if kind == "rag":
        c.roundRect(x, y, 22, 28, 3, fill=0, stroke=1)
        c.line(x + 5, y + 19, x + 17, y + 19)
        c.line(x + 5, y + 14, x + 17, y + 14)
        c.line(x + 5, y + 9, x + 14, y + 9)
    elif kind == "table":
        c.roundRect(x, y, 24, 27, 3, fill=0, stroke=1)
        c.line(x + 4, y + 18, x + 20, y + 18)
        c.line(x + 4, y + 11, x + 20, y + 11)
        c.line(x + 10, y + 4, x + 10, y + 23)
        c.line(x + 16, y + 4, x + 16, y + 23)
    else:
        pts = [(x + 3, y + 20), (x + 18, y + 26), (x + 22, y + 8)]
        c.line(*pts[0], *pts[1])
        c.line(*pts[1], *pts[2])
        c.line(*pts[2], *pts[0])
        for px, py in pts:
            c.circle(px, py, 3.3, fill=1, stroke=0)


def _surface_card(c, x, y, w, title, subtitle, tool, kind, color, bg):
    _round_card(c, x, y, w, 76, bg, color, radius=9, line_width=1.4)
    c.setFillColor(color)
    c.roundRect(x, y + 71, w, 5, 5, fill=1, stroke=0)
    _surface_icon(c, kind, x + 14, y + 35, color)
    _text(c, x + 47, y + 52, title, 18, "TNR-Bold", color)
    _text(c, x + 47, y + 35, subtitle, 12.7, "TNR", INK)
    _text(c, x + 47, y + 18, tool, 11.4, "Courier-Bold", MUTED)


def _compact_surface(c, x, y, title, subtitle, kind, color, bg,
                     text_color=None):
    """Small, high-legibility surface card used by the teaser."""
    _round_card(c, x, y, 82, 88, bg, color, radius=9, line_width=1.35)
    c.setFillColor(color)
    c.roundRect(x, y + 83, 82, 5, 5, fill=1, stroke=0)
    _surface_icon(c, kind, x + 29, y + 49, color)
    _text(c, x + 41, y + 31, title, 16.5, "TNR-Bold",
          text_color or color, "center")
    _text(c, x + 41, y + 14, subtitle, 12.2, "TNR", MUTED, "center")


def render_figure1(path: Path):
    c = canvas.Canvas(str(path), pagesize=PAGE, pageCompression=1)
    c.setTitle("Figure 1: WorkSurface-Bench teaser")
    c.setFillColor(white)
    c.rect(0, 0, *PAGE, fill=1, stroke=0)

    # Enterprise question with three compact source-type chips.
    _round_card(c, 20, 118, 200, 111, white, BORDER, radius=10,
                line_width=1.2)
    c.setFillColor(SLATE)
    c.roundRect(20, 118, 6, 111, 4, fill=1, stroke=0)
    _text(c, 36, 207, "Enterprise question", 16.5, "TNR-Bold", INK)
    chips = [("DOC", BLUE_DARK, BLUE_BG), ("TABLE", ORANGE, ORANGE_BG),
             ("LINKS", GREEN, GREEN_BG)]
    xx = 36
    for label, color, bg in chips:
        width = 43 if label != "TABLE" else 52
        _round_card(c, xx, 180, width, 18, bg, color, radius=4,
                    line_width=0.8)
        _text(c, xx + width / 2, 185, label, 10.5, "TNR-Bold", color,
              "center")
        xx += width + 7
    _text(c, 36, 161, "How many items have negative", 13.2, "TNR")
    _text(c, 36, 144, "variance, and what is their total", 13.2, "TNR")
    _text(c, 36, 127, "cost by shipping mode?", 13.2, "TNR")

    # Routing agent is the visual focal point.
    _arrow(c, 229, 177, 274, 177, SLATE, width=1.8, head=7)
    _text(c, 251, 186, "question", 11.3, "TNR-Italic", MUTED, "center")
    _round_card(c, 274, 142, 122, 70, SLATE, SLATE, radius=10,
                line_width=1.2)
    c.setStrokeColor(white)
    c.setFillColor(white)
    c.setLineWidth(1.5)
    c.circle(296, 180, 8, fill=0, stroke=1)
    c.circle(296, 180, 2.3, fill=1, stroke=0)
    _text(c, 312, 179, "Agent", 20, "TNR-Bold", white)
    _text(c, 312, 160, "route + retrieve", 12.1, "TNR", white)

    # The agent chooses one or more of three canonical surfaces.
    _arrow(c, 405, 177, 434, 177, SLATE, width=1.8, head=7)
    _text(c, 575, 231, "select one or more", 13.2, "TNR-Italic", MUTED,
          "center")
    _compact_surface(c, 442, 134, "RAG", "documents", "rag", BLUE,
                     BLUE_BG, BLUE_DARK)
    _compact_surface(c, 534, 134, "Table", "SQL views", "table", ORANGE,
                     ORANGE_BG)
    _compact_surface(c, 626, 134, "Graph", "lineage", "graph", GREEN,
                     GREEN_BG)

    # Final response is downstream of retrieved evidence.
    _arrow(c, 717, 177, 746, 177, SLATE, width=1.8, head=7)
    _round_card(c, 746, 142, 98, 70, PURPLE_BG, PURPLE, radius=10,
                line_width=1.35)
    c.setStrokeColor(PURPLE)
    c.setLineWidth(1.8)
    c.circle(795, 189, 9, fill=0, stroke=1)
    c.line(790, 189, 794, 185)
    c.line(794, 185, 801, 194)
    _text(c, 795, 159, "Final answer", 15.5, "TNR-Bold", PURPLE,
          "center")

    # Two equal-width diagnostic score heads map to distinct decisions.
    c.setStrokeColor(BORDER)
    c.setLineWidth(1.0)
    c.setDash(3, 3)
    c.line(420, 134, 420, 78)
    c.line(795, 142, 795, 78)
    c.setDash()
    _text(c, 20, 55, "Scored independently", 17, "TNR-Bold", INK)
    _text(c, 20, 36, "diagnose where the agent fails", 12.2,
          "TNR-Italic", MUTED)

    _round_card(c, 240, 20, 294, 58, BLUE_BG, BLUE_DARK, radius=9,
                line_width=1.25)
    c.setFillColor(BLUE)
    c.roundRect(240, 73, 294, 5, 5, fill=1, stroke=0)
    _text(c, 258, 54, "Route F1", 17, "TNR-Bold", BLUE_DARK)
    _text(c, 258, 35, "selected surface set  vs.  required set", 13.1,
          "TNR", MUTED)

    _round_card(c, 550, 20, 294, 58, PURPLE_BG, PURPLE, radius=9,
                line_width=1.25)
    c.setFillColor(PURPLE)
    c.roundRect(550, 73, 294, 5, 5, fill=1, stroke=0)
    _text(c, 568, 54, "Answer accuracy", 17, "TNR-Bold", PURPLE)
    _text(c, 568, 35, "final response  vs.  reference answer", 13.1,
          "TNR", MUTED)

    c.showPage()
    c.save()


def _stage_card(c, x, y, w, h, number, title, subtitle, accent,
                highlight=False):
    stroke = accent if highlight else BORDER
    _round_card(c, x, y, w, h, white, stroke, radius=10,
                line_width=1.55 if highlight else 1.0, shadow=False)
    c.setFillColor(white)
    c.setStrokeColor(accent)
    c.setLineWidth(1.4)
    c.circle(x + 22, y + h - 28, 13, fill=1, stroke=1)
    _text(c, x + 22, y + h - 33, str(number), 14, "TNR-Bold", accent,
          "center")
    _text(c, x + 43, y + h - 31, title, 17.5, "TNR-Bold", INK)
    _text(c, x + 15, y + h - 53, subtitle, 11.7, "TNR-Italic", MUTED)


def _badge(c, x, y, w, h, text, color=GREEN, bg=GREEN_BG, size=13.5):
    _round_card(c, x, y, w, h, bg, color, radius=7, line_width=1.2)
    _text(c, x + w / 2, y + (h - size) / 2 + 2, text, size,
          "TNR-Bold", color, "center")


def _surface_row(c, x, y, w, name, value, color, bg):
    _round_card(c, x, y, w, 25, bg, color, radius=5, line_width=1.0)
    c.setFillColor(color)
    c.rect(x, y, 5, 25, fill=1, stroke=0)
    _text(c, x + 12, y + 7, name, 12.8, "TNR-Bold", color)
    _text(c, x + w - 9, y + 7, value, 12.2, "TNR", INK, "right")


def render_figure2(path: Path):
    c = canvas.Canvas(str(path), pagesize=FIGURE2_PAGE, pageCompression=1)
    c.setTitle("Figure 2: WorkSurface-Bench construction pipeline")
    c.setFillColor(white)
    c.rect(0, 0, *FIGURE2_PAGE, fill=1, stroke=0)
    c.translate(0, -45)

    xs = [10, 181, 352, 523, 694]
    w, y, h = 155, 55, 204
    accents = [SLATE, BLUE, GREEN, PURPLE, SLATE]
    titles = ["Freeze", "Project", "Derive", "Expand", "Audit"]
    subtitles = ["pin source state", "make surfaces queryable",
                 "deterministic core", "compose and verify",
                 "validate and release"]
    for i, (x, accent, title, subtitle) in enumerate(
            zip(xs, accents, titles, subtitles), start=1):
        _stage_card(c, x, y, w, h, i, title, subtitle, accent,
                    highlight=i in (3, 4))
        if i < 5:
            _arrow(c, x + w + 3, 156, xs[i] - 3, 156, SLATE,
                   width=1.7, head=6)

    # 1. Frozen provenance.
    _text(c, xs[0] + 15, 183, "Workspace-Bench-Lite", 14,
          "TNR-Bold", INK)
    _text(c, xs[0] + 15, 166, "English split", 12.4, "TNR", MUTED)
    _badge(c, xs[0] + 15, 127, 125, 29, "commit + SHA-256", SLATE,
           SLATE_BG, 12.5)
    _text(c, xs[0] + 15, 104, "100 source tasks", 12.8, "TNR-Bold")
    _text(c, xs[0] + 15, 87, "5 personas  |  493 docs", 12.2,
          "TNR", MUTED)
    _text(c, xs[0] + 15, 67, "reproducible inputs", 11.8,
          "TNR-Italic", MUTED)

    # 2. Three routable surfaces.
    _surface_row(c, xs[1] + 13, 166, 129, "RAG", "493 docs", BLUE, BLUE_BG)
    _surface_row(c, xs[1] + 13, 134, 129, "Table", "207 views", ORANGE,
                 ORANGE_BG)
    _surface_row(c, xs[1] + 13, 102, 129, "Graph", "1,438 edges", GREEN,
                 GREEN_BG)
    _text(c, xs[1] + w / 2, 80, "SOPs remain metadata", 11.7,
          "TNR-Italic", MUTED, "center")
    _text(c, xs[1] + w / 2, 65, "not a routable surface", 11.7,
          "TNR-Italic", MUTED, "center")

    # 3. Candidate generation.
    _text(c, xs[2] + 15, 184, "Proof-carrying gold", 13.5,
          "TNR-Bold", GREEN)
    _text(c, xs[2] + 17, 158, "- executed SQL", 12.5)
    _text(c, xs[2] + 17, 139, "- verified spans", 12.5)
    _text(c, xs[2] + 17, 120, "- graph paths", 12.5)
    _badge(c, xs[2] + 15, 78, 125, 31, "2,000 candidates", GREEN, GREEN_BG, 13)
    _text(c, xs[2] + w / 2, 63, "deterministic + assisted", 11.7,
          "TNR-Italic", MUTED, "center")

    # 4. Verified expansion and cross-surface composition.
    _text(c, xs[3] + 15, 184, "Three-model screen", 13.3,
          "TNR-Bold", PURPLE)
    _text(c, xs[3] + 15, 163, "GPT strict", 12.5, "TNR-Bold")
    _text(c, xs[3] + w - 15, 163, "1,465", 12.5, "TNR-Bold", INK, "right")
    _text(c, xs[3] + 15, 143, "All 3 pass", 12.2)
    _text(c, xs[3] + w - 15, 143, "429", 12.2, "TNR-Bold", INK, "right")
    _text(c, xs[3] + 15, 123, "Human audit", 12.2)
    _text(c, xs[3] + w - 15, 123, "200", 12.2, "TNR-Bold", INK, "right")
    _badge(c, xs[3] + 15, 83, 125, 28, "2-of-3 strict", PURPLE,
           PURPLE_BG, 13.5)
    _text(c, xs[3] + w / 2, 63, "six quality dimensions", 11.2,
          "TNR-Italic", MUTED, "center")

    # 5. Exact released set and distribution.
    _round_card(c, xs[4] + 14, 160, 127, 43, GREEN_BG, GREEN,
                radius=7, line_width=1.2)
    _text(c, xs[4] + w / 2, 182, "1,151 atomic tasks", 15,
          "TNR-Bold", GREEN, "center")
    _text(c, xs[4] + w / 2, 166, "auditable  |  schema-valid", 10.4,
          "TNR-Italic", MUTED, "center")
    rows = [("Cross", "488", PURPLE, PURPLE_BG),
            ("RAG", "213", BLUE, BLUE_BG),
            ("Graph", "171", GREEN, GREEN_BG),
            ("Table", "279", ORANGE, ORANGE_BG)]
    yy = 134
    for name, value, color, bg in rows:
        _surface_row(c, xs[4] + 15, yy, 125, name, value, color, bg)
        yy -= 26

    c.showPage()
    c.save()


def _render_png(pdf: Path, png: Path):
    prefix = png.with_suffix("")
    env = os.environ.copy()
    homebrew_fontconfig = Path("/opt/homebrew/etc/fonts/fonts.conf")
    if "FONTCONFIG_FILE" not in env and homebrew_fontconfig.exists():
        env["FONTCONFIG_FILE"] = str(homebrew_fontconfig)
    subprocess.run([
        "pdftoppm", "-png", "-singlefile", "-r", "300",
        str(pdf), str(prefix)
    ], check=True, env=env)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--figure",
        choices=("1", "2", "all"),
        default="all",
        help="render only the requested figure (default: all)",
    )
    args = parser.parse_args()
    outputs = [
        ("figure1_teaser", render_figure1),
        ("figure2_pipeline", render_figure2),
    ]
    if args.figure != "all":
        outputs = [outputs[int(args.figure) - 1]]
    for stem, renderer in outputs:
        spec_pdf = HERE / f"{stem}.pdf"
        spec_png = HERE / f"{stem}.png"
        renderer(spec_pdf)
        _render_png(spec_pdf, spec_png)
        shutil.copy2(spec_pdf, PAPER_DIR / spec_pdf.name)
        shutil.copy2(spec_png, PAPER_DIR / spec_png.name)
        print(f"wrote {spec_pdf.name} and {spec_png.name}")


if __name__ == "__main__":
    main()
