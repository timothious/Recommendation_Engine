#!/usr/bin/env python3
"""Generate a short Recommendation Engine workflow PDF (2 pages)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image as RLImage,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


DOC_DIR = Path(__file__).resolve().parent
OUT_PATH = DOC_DIR / "Recommendation_Engine_Workflow_Report.pdf"
DIAGRAM_PATH = DOC_DIR / "workflow_diagram.png"

NAVY = colors.HexColor("#1B2A4A")
TEAL = colors.HexColor("#2A6F7A")
LIGHT = colors.HexColor("#F4F7F8")
LINE = colors.HexColor("#D0D7DE")
MUTED = colors.HexColor("#5B6B7A")


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "T", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=16, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "S", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, textColor=MUTED, alignment=TA_CENTER, spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=11, textColor=NAVY, spaceBefore=8, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "B", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.5, leading=11, textColor=colors.HexColor("#243040"), spaceAfter=4,
        ),
        "code": ParagraphStyle(
            "C", parent=base["Code"], fontName="Courier",
            fontSize=6.8, leading=8.6, textColor=NAVY, backColor=LIGHT,
            leftIndent=3, rightIndent=3, spaceBefore=2, spaceAfter=4,
        ),
        "cell": ParagraphStyle(
            "Cell", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.5, leading=9.5, textColor=colors.HexColor("#243040"),
        ),
        "cell_bold": ParagraphStyle(
            "CellB", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.5, leading=9.5, textColor=NAVY,
        ),
    }


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(14 * mm, A4[1] - 10 * mm, A4[0] - 14 * mm, A4[1] - 10 * mm)
    canvas.line(14 * mm, 10 * mm, A4[0] - 14 * mm, 10 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(14 * mm, A4[1] - 8 * mm, "Halal SNS | Recommendation Engine")
    canvas.drawRightString(A4[0] - 14 * mm, A4[1] - 8 * mm, "Workflow Report")
    canvas.drawCentredString(A4[0] / 2, 6.5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def file_table(rows, s, path_w=42, sum_w=138):
    data = [[
        Paragraph("<b>File</b>", s["cell_bold"]),
        Paragraph("<b>Summary</b>", s["cell_bold"]),
    ]]
    for path, summary in rows:
        data.append([Paragraph(path, s["cell_bold"]), Paragraph(summary, s["cell"])])
    table = Table(data, colWidths=[path_w * mm, sum_w * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return table


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _rounded_box(draw, box, fill, outline, radius=14, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _center_text(draw, cx, cy, lines, fonts, fills):
    """Draw one or more centered text lines around (cx, cy)."""
    heights = []
    widths = []
    for text, font in zip(lines, fonts):
        bbox = draw.textbbox((0, 0), text, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    gap = 4
    total_h = sum(heights) + gap * (len(lines) - 1)
    y = cy - total_h / 2
    for text, font, fill, h, w in zip(lines, fonts, fills, heights, widths):
        draw.text((cx - w / 2, y), text, font=font, fill=fill)
        y += h + gap


def _arrow_down(draw, x, y1, y2, color=(42, 111, 122)):
    draw.line((x, y1, x, y2 - 10), fill=color, width=3)
    draw.polygon([(x - 7, y2 - 12), (x + 7, y2 - 12), (x, y2)], fill=color)


def build_workflow_diagram_png(path: Path) -> Path:
    """
    Simple top-to-bottom diagram:
      two starts -> ranking -> scoring (+config) -> sort -> diversity -> reasons -> output
    """
    W, H = 1100, 1450
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    title_font = _font(28, bold=True)
    step_font = _font(20, bold=True)
    body_font = _font(16)
    small_font = _font(14)
    tiny_font = _font(13)

    navy = (27, 42, 74)
    teal = (42, 111, 122)
    start_fill = (220, 232, 245)
    main_fill = (232, 241, 242)
    rank_fill = (243, 233, 215)
    out_fill = (220, 245, 230)
    muted = (91, 107, 122)

    # Title
    draw.rounded_rectangle((40, 30, W - 40, 95), radius=12, fill=navy)
    t = "How ranking works (files + functions)"
    tb = draw.textbbox((0, 0), t, font=title_font)
    draw.text(((W - (tb[2] - tb[0])) / 2, 48), t, font=title_font, fill=(255, 255, 255))

    # Two start boxes
    left = (70, 130, 480, 230)
    right = (620, 130, 1030, 230)
    _rounded_box(draw, left, start_fill, navy)
    _rounded_box(draw, right, start_fill, navy)
    _center_text(
        draw, (left[0] + left[2]) / 2, (left[1] + left[3]) / 2,
        ["START A — API", "main.py", "get_recommendations()"],
        [step_font, body_font, small_font],
        [navy, navy, muted],
    )
    _center_text(
        draw, (right[0] + right[2]) / 2, (right[1] + right[3]) / 2,
        ["START B — Test UI", "test_ui/app.py", "main() → run_pipeline()"],
        [step_font, body_font, small_font],
        [navy, navy, muted],
    )

    # Merge lines into one arrow
    mid_x = W // 2
    draw.line((275, 230, 275, 260), fill=teal, width=3)
    draw.line((825, 230, 825, 260), fill=teal, width=3)
    draw.line((275, 260, 825, 260), fill=teal, width=3)
    _arrow_down(draw, mid_x, 260, 300)

    # Step boxes — single column
    box_w = 640
    box_h = 100
    x0 = (W - box_w) // 2
    gap = 46

    steps = [
        {
            "title": "1) ranking.py  →  rank_posts()",
            "sub": "Controls the full order: score → sort → diversity → reasons",
            "fill": rank_fill,
        },
        {
            "title": "2) scoring.py  →  calculate_post_score()",
            "sub": "Builds 5 scores: topic, relationship, freshness, engagement, exploration",
            "fill": main_fill,
            "side": True,
        },
        {
            "title": "3) Sort posts",
            "sub": "Highest final score first",
            "fill": main_fill,
        },
        {
            "title": "4) diversity.py  →  apply_diversity()",
            "sub": "If same creator/topic repeats too much, delay that post (never delete)",
            "fill": main_fill,
        },
        {
            "title": "5) ranking.py  →  generate_reasons()",
            "sub": "Add short labels like “followed creator”, “topic match”, “recent post”",
            "fill": main_fill,
        },
        {
            "title": "6) Response",
            "sub": "Return { model, ranked_posts[{post_id, score, reasons}], total_candidates }",
            "fill": out_fill,
        },
    ]

    y = 300
    for index, step in enumerate(steps):
        box = (x0, y, x0 + box_w, y + box_h)
        _rounded_box(draw, box, step["fill"], navy)
        _center_text(
            draw, mid_x, y + box_h / 2,
            [step["title"], step["sub"]],
            [step_font, small_font],
            [navy, muted],
        )

        # config side box next to scoring
        if step.get("side"):
            side = (x0 + box_w + 20, y + 10, W - 50, y + box_h - 10)
            _rounded_box(draw, side, (255, 255, 255), teal, radius=12, width=2)
            _center_text(
                draw, (side[0] + side[2]) / 2, (side[1] + side[3]) / 2,
                ["config.py", "weights & limits", "read by scoring"],
                [body_font, tiny_font, tiny_font],
                [teal, muted, muted],
            )
            # arrow from scoring to config
            ax1 = x0 + box_w
            ax2 = side[0]
            ay = y + box_h / 2
            draw.line((ax1, ay, ax2 - 8, ay), fill=teal, width=3)
            draw.polygon(
                [(ax2 - 10, ay - 6), (ax2 - 10, ay + 6), (ax2, ay)],
                fill=teal,
            )

        if index < len(steps) - 1:
            _arrow_down(draw, mid_x, y + box_h, y + box_h + gap)

        y += box_h + gap

    # Footer note
    note = "Same core path for API and UI. UI also uses explain_post() to show formulas in Activity."
    nb = draw.textbbox((0, 0), note, font=small_font)
    draw.text(((W - (nb[2] - nb[0])) / 2, H - 55), note, font=small_font, fill=muted)

    img.save(path, format="PNG")
    return path


def build_pdf() -> Path:
    diagram_png = build_workflow_diagram_png(DIAGRAM_PATH)

    s = styles()
    doc = SimpleDocTemplate(
        str(OUT_PATH),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Recommendation Engine Workflow Report",
        author="Recommendation Engine Lab",
    )

    story = []
    story.append(Paragraph("Recommendation Engine — Workflow Report", s["title"]))
    story.append(Paragraph(
        "Folder map, one-line file summaries, and a simple workflow diagram",
        s["subtitle"],
    ))

    story.append(Paragraph("1. Folder & file system", s["h1"]))
    story.append(Preformatted(
        """Recommendation_Engine/
|-- main.py / api.py / config.py / scoring.py / ranking.py / diversity.py
|-- requirements.txt
|-- data/          recommendation_candidates_test.json   (+ more scenarios later)
|-- test_ui/       app.py, engine_runner.py, __init__.py, run.sh
|-- doc/           Implementation_Plan.pdf, this report, generate_workflow_report.py
+-- tests/         (reserved)""",
        s["code"],
    ))

    story.append(Paragraph("2. One-line summary of every file", s["h1"]))
    story.append(file_table([
        ["main.py", "FastAPI entry: validates request and returns ranked posts."],
        ["api.py", "Older schema stub; live schemas are in main.py."],
        ["config.py", "Tunable weights, half-lives, engagement k/prior, diversity caps."],
        ["scoring.py", "Five signals + weighted final score (and breakdown)."],
        ["ranking.py", "Score all → sort → diversity → attach short reasons."],
        ["diversity.py", "Delay repeats so creator/topic do not run too long in a row."],
        ["requirements.txt", "Python deps for API, UI, and tests."],
        ["data/*.json", "Candidate scenarios for local simulation (dropdown reads this folder)."],
        ["test_ui/app.py", "Streamlit UI start: controls, ranked feed, activity formulas."],
        ["test_ui/engine_runner.py", "Loads JSON, applies live config, runs full pipeline for UI."],
        ["test_ui/run.sh", "Convenience launcher for Streamlit."],
        ["test_ui/__init__.py", "Package marker for imports."],
        ["doc/*Plan*.pdf", "Product/engineering implementation plan."],
        ["doc/*Workflow*.pdf", "This short workflow report."],
        ["doc/generate_workflow_report.py", "Regenerates this PDF."],
        ["doc/workflow_diagram.png", "Diagram image embedded in this report."],
        ["tests/", "Placeholder for automated tests."],
    ], s))

    story.append(PageBreak())
    story.append(Paragraph("3. Workflow diagram (read top → bottom)", s["h1"]))
    story.append(Paragraph(
        "Follow the numbered boxes. Both starts join at step 1, then the same path runs to the response.",
        s["body"],
    ))
    story.append(Spacer(1, 2 * mm))
    # Fit diagram to page width
    story.append(RLImage(str(diagram_png), width=180 * mm, height=237 * mm))
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("4. Shared scoring formula & run commands", s["h1"]))
    story.append(Preformatted(
        "score = max(0, 0.30*topic + 0.25*relationship + 0.20*freshness "
        "+ 0.15*engagement + 0.10*exploration - penalty)\n"
        "Run API:  .venv/bin/uvicorn main:app --reload --port 8000\n"
        "Run UI:   .venv/bin/streamlit run test_ui/app.py   |   ./test_ui/run.sh\n"
        "Regen PDF: .venv/bin/python doc/generate_workflow_report.py",
        s["code"],
    ))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    return OUT_PATH


if __name__ == "__main__":
    path = build_pdf()
    print(f"Wrote {path}")
    print(f"Diagram {DIAGRAM_PATH}")
