from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ASSET_DIR = Path("docs/assets")
PUBLIC_REAL_PAGE_DIR = Path("runs/stage6_public_real/page_images")
NON_GOV_PAGE_DIR = Path("runs/stage7_non_gov_public/page_images")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _mono_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/consolab.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return _font(size)


def _rounded(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    fill: str,
    outline: str | None = None,
    width: int = 1,
    radius: int = 18,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    size: int,
    fill: str = "#111827",
    bold: bool = False,
) -> None:
    draw.text(xy, text, font=_font(size, bold=bold), fill=fill)


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    size: int,
    fill: str,
    *,
    max_chars: int,
    line_gap: int = 8,
    bold: bool = False,
) -> int:
    font = _font(size, bold=bold)
    y = xy[1]
    for line in textwrap.wrap(text, width=max_chars):
        draw.text((xy[0], y), line, font=font, fill=fill)
        y += size + line_gap
    return y


def _fit_image(img: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    max_w = box[2] - box[0]
    max_h = box[3] - box[1]
    scale = min(max_w / img.width, max_h / img.height)
    size = (int(img.width * scale), int(img.height * scale))
    return img.resize(size, Image.Resampling.LANCZOS)


def _crop_page(src: Path, crop: tuple[int, int, int, int], size: tuple[int, int]) -> Image.Image:
    img = Image.open(src).convert("RGB")
    return img.crop(crop).resize(size, Image.Resampling.LANCZOS)


def _paste_shadow_card(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    image: Image.Image,
    *,
    pad: int = 18,
    radius: int = 20,
) -> tuple[int, int, int, int]:
    x, y = xy
    w, h = image.size
    card = (x, y, x + w + pad * 2, y + h + pad * 2)
    _rounded(draw, (card[0] + 8, card[1] + 12, card[2] + 8, card[3] + 12), "#dbe3ef", None, 1, radius)
    _rounded(draw, card, "#ffffff", "#cbd5e1", 2, radius)
    canvas.paste(image, (x + pad, y + pad))
    return card


def _draw_assertion_card(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    *,
    title: str,
    case_id: str,
    params: list[tuple[str, str]],
    badge: str,
    badge_color: str,
    why: str,
) -> None:
    x, y = xy
    _rounded(draw, (x, y, x + 440, y + 500), "#ffffff", "#cbd5e1", 2, 22)
    _draw_text(draw, (x + 30, y + 32), title, 30, bold=True)
    _draw_text(draw, (x + 32, y + 72), case_id, 16, "#64748b")
    mono = _mono_font(19)
    code_lines = ["{"]
    for idx, (key, value) in enumerate(params):
        suffix = "," if idx < len(params) - 1 else ""
        raw = f'  "{key}": "{value}"{suffix}'
        code_lines.extend(textwrap.wrap(raw, width=33, subsequent_indent="    "))
    code_lines.append("}")
    param_y = y + 120
    for line in code_lines[:10]:
        draw.text((x + 30, param_y), line, font=mono, fill="#111827")
        param_y += 30
    _rounded(draw, (x + 30, y + 338, x + 166, y + 392), badge_color[0], badge_color[1], 2, 13)
    _draw_text(draw, (x + 59, y + 353), badge, 21, badge_color[2], bold=True)
    _draw_text(draw, (x + 30, y + 428), "Why kept", 15, "#64748b", bold=True)
    _wrap_text(draw, (x + 112, y + 428), why, 15, "#475569", max_chars=39, line_gap=5)


def _draw_locator(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    src: Path,
    xy: tuple[int, int],
    crop: tuple[int, int, int, int],
    *,
    outline: str,
) -> None:
    img = Image.open(src).convert("RGB")
    thumb = _fit_image(img, (0, 0, 156, 206))
    x, y = xy
    _rounded(draw, (x, y, x + 184, y + 236), "#ffffff", "#cbd5e1", 2, 14)
    canvas.paste(thumb, (x + 14, y + 14))
    sx = thumb.width / img.width
    sy = thumb.height / img.height
    rect = (
        x + 14 + int(crop[0] * sx),
        y + 14 + int(crop[1] * sy),
        x + 14 + int(crop[2] * sx),
        y + 14 + int(crop[3] * sy),
    )
    draw.rectangle(rect, outline=outline, width=3)
    _draw_text(draw, (x + 18, y + 218), "full-page locator", 13, "#64748b")


def table_example() -> None:
    src = PUBLIC_REAL_PAGE_DIR / "public_real_nist_sp800_53r5_p027.png"
    crop = (105, 104, 792, 898)
    table = _crop_page(src, crop, (820, 660))

    canvas = Image.new("RGB", (1440, 860), "#f8fafc")
    draw = ImageDraw.Draw(canvas)
    _draw_text(draw, (48, 38), "Strict review on a real complex revision table", 34, bold=True)
    _draw_text(
        draw,
        (50, 82),
        "NIST SP 800-53 p27: keep grid-position checks that expose row/column drift and numeric loss.",
        18,
        "#475569",
    )
    _paste_shadow_card(canvas, draw, (48, 132), table)

    # Row 11 / col 2 and its page-number cell, measured on the rendered crop.
    row_y0 = 236
    row_y1 = 258
    revision_x0 = 228
    revision_x1 = 735
    page_x0 = 735
    page_x1 = 812
    highlight = "#dc2626"
    table_origin = (48 + 18, 132 + 18)
    draw.rectangle(
        (
            table_origin[0] + revision_x0,
            table_origin[1] + row_y0,
            table_origin[0] + revision_x1,
            table_origin[1] + row_y1,
        ),
        outline=highlight,
        width=5,
    )
    draw.rectangle(
        (
            table_origin[0] + page_x0,
            table_origin[1] + row_y0,
            table_origin[0] + page_x1,
            table_origin[1] + row_y1,
        ),
        outline=highlight,
        width=5,
    )
    draw.line((892, 390, 984, 318), fill=highlight, width=4)

    _draw_locator(canvas, draw, src, (48, 690), crop, outline="#dc2626")
    _draw_assertion_card(
        draw,
        (984, 150),
        title="table_grid_cell",
        case_id="public_real_nist_sp800_53r5_p027",
        params=[
            ("row", "11"),
            ("col", "2"),
            ("expected", "Table C-5: Delete duplicate row CM-8(5)."),
        ],
        badge="approve",
        badge_color=("#fee2e2", "#dc2626", "#991b1b"),
        why="specific row, column, long cell text, and page-number cell all have to survive.",
    )

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    canvas.save(ASSET_DIR / "review_table_assertion.png", quality=94)


def formula_grounding_example() -> None:
    src = NON_GOV_PAGE_DIR / "non_gov_public_openstax_chemistry_p257.png"
    crop = (96, 80, 812, 460)
    panel = _crop_page(src, crop, (820, 435))

    canvas = Image.new("RGB", (1440, 760), "#f8fafc")
    draw = ImageDraw.Draw(canvas)
    _draw_text(draw, (48, 38), "Formula checks on an open textbook page", 34, bold=True)
    _draw_text(
        draw,
        (50, 82),
        "OpenStax Chemistry book p247 / PDF p257: signs, subscripts, units, and nearby prompts must survive together.",
        18,
        "#475569",
    )
    _paste_shadow_card(canvas, draw, (48, 128), panel)

    # Main heat-equation block in the resized crop coordinates.
    blue = "#2563eb"
    panel_origin = (48 + 18, 128 + 18)
    draw.rectangle((panel_origin[0] + 198, panel_origin[1] + 24, panel_origin[0] + 612, panel_origin[1] + 138), outline=blue, width=5)
    draw.rectangle((panel_origin[0] + 38, panel_origin[1] + 164, panel_origin[0] + 252, panel_origin[1] + 204), outline=blue, width=5)
    draw.line((888, 220, 984, 222), fill=blue, width=4)
    draw.line((888, 332, 984, 350), fill=blue, width=4)

    _draw_locator(canvas, draw, src, (48, 598), crop, outline=blue)
    _draw_assertion_card(
        draw,
        (984, 140),
        title="formula_contains",
        case_id="non_gov_public_openstax_chemistry_p257",
        params=[
            ("latex", "q_rxn = -q_soln = -(c x m x DeltaT)_soln"),
            ("nearby", "+1.0 x 10^3 J = +1.0 kJ"),
        ],
        badge="approve",
        badge_color=("#dbeafe", "#2563eb", "#1d4ed8"),
        why="formula symbols, signs, units, and nearby learning prompt are visible and diagnostically specific.",
    )

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    canvas.save(ASSET_DIR / "review_formula_grounding.png", quality=94)


def main() -> int:
    table_example()
    formula_grounding_example()
    print(f"Wrote screenshots to {ASSET_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
