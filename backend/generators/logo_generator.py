"""
Logo üretimi — iki katman:
  1. SVG (HTML brand kit için): vektörel, modern, yüksek kalite
  2. PIL (preview collage / ZIP için): raster, hızlı

SVG fonksiyonlar: generate_logo_*_svg() → base64 data URI string
PIL fonksiyonlar: generate_logo_primary/icon/reversed/social_post() → PIL.Image
"""

import base64
import html as html_esc
from PIL import Image, ImageDraw, ImageFont
import os
import math

FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")

# Fallback font paths (sistem fontları)
SYSTEM_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Sistemde bulunan ilk fontu döner."""
    for path in SYSTEM_FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def extract_initials(brand_name: str) -> str:
    """'Windy Venture Capital' → 'WVC', tek kelime → ilk 2 harf"""
    words = brand_name.strip().split()
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:3]).upper()


def hex_to_rgb(hex_color: str) -> tuple:
    """#RRGGBB → (R, G, B)"""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def is_dark(hex_color: str) -> bool:
    """Rengin karanlık mı açık mı olduğunu hesapla (luminance)."""
    try:
        r, g, b = hex_to_rgb(hex_color)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance < 0.5
    except Exception:
        return True


def ghost_color(hex_color: str, alpha_factor: float = 0.12) -> tuple:
    """Zemin rengine yakın ama hafif görünür ghost rengi üret."""
    try:
        r, g, b = hex_to_rgb(hex_color)
        dark = is_dark(hex_color)
        shift = 30 if dark else -30
        return (
            max(0, min(255, r + shift)),
            max(0, min(255, g + shift)),
            max(0, min(255, b + shift)),
        )
    except Exception:
        return (30, 30, 30)


def generate_logo_primary(
    brand_name: str,
    primary: str = "#0A0A0A",
    secondary: str = "#F1EBE1",
    size: tuple = (1200, 800),
) -> Image.Image:
    """
    Primary logo — büyük display harfler, ölçek çarpışması.
    Hem koyu hem açık zemin renklerini destekler.
    """
    w, h = size
    bg_rgb = hex_to_rgb(primary)
    text_rgb = hex_to_rgb(secondary)

    img = Image.new("RGB", (w, h), bg_rgb)
    draw = ImageDraw.Draw(img)

    initials = extract_initials(brand_name)
    name_upper = brand_name.upper()

    # BG ghost letter — canvas'ı taşan devasa harf
    ghost_size = h * 2
    try:
        ghost_font = get_font(ghost_size)
        draw.text(
            (-ghost_size * 0.15, -ghost_size * 0.2),
            initials[0],
            font=ghost_font,
            fill=ghost_color(primary),
        )
    except Exception:
        pass

    # Ana metin — sağda, ortada
    name_font = get_font(int(h * 0.18))
    name_bbox = draw.textbbox((0, 0), name_upper, font=name_font)
    name_w = name_bbox[2] - name_bbox[0]
    name_x = w - name_w - 60
    name_y = h // 2 - 40

    draw.text((name_x, name_y), name_upper, font=name_font, fill=text_rgb)

    # Alt çizgi
    line_y = name_y + int(h * 0.22)
    draw.line([(name_x, line_y), (w - 60, line_y)], fill=text_rgb, width=2)

    mono_font = get_font(int(h * 0.055), bold=False)
    # Subtitle rengi: text rengi ama daha soluk
    sub_r = (text_rgb[0] + bg_rgb[0]) // 2
    sub_g = (text_rgb[1] + bg_rgb[1]) // 2
    sub_b = (text_rgb[2] + bg_rgb[2]) // 2
    draw.text(
        (name_x, line_y + 16),
        "BRAND IDENTITY",
        font=mono_font,
        fill=(sub_r, sub_g, sub_b),
    )

    return img


def generate_logo_icon(
    brand_name: str,
    primary: str = "#0A0A0A",
    secondary: str = "#F1EBE1",
    size: tuple = (800, 800),
) -> Image.Image:
    """
    Icon versiyonu — kare format, monogram.
    Hem koyu hem açık zemin desteklenir.
    """
    w, h = size
    bg_rgb = hex_to_rgb(primary)
    text_rgb = hex_to_rgb(secondary)

    img = Image.new("RGB", (w, h), bg_rgb)
    draw = ImageDraw.Draw(img)

    initials = extract_initials(brand_name)[:2]

    font_size = int(h * 0.55)
    font = get_font(font_size)

    bbox = draw.textbbox((0, 0), initials, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (w - text_w) // 2 - bbox[0]
    y = (h - text_h) // 2 - bbox[1]

    draw.text((x, y), initials, font=font, fill=text_rgb)

    # Köşe çerçeve — zemine göre ayarlı
    margin = 24
    frame_color = ghost_color(primary, alpha_factor=0.25)
    draw.rectangle(
        [margin, margin, w - margin, h - margin],
        outline=frame_color,
        width=1,
    )

    return img


def generate_logo_reversed(
    brand_name: str,
    primary: str = "#0A0A0A",
    secondary: str = "#F1EBE1",
    size: tuple = (1200, 800),
) -> Image.Image:
    """
    Reversed — açık zemin, koyu metin.
    """
    img = generate_logo_primary(brand_name, secondary, primary, size)
    return img


def apply_watermark(img: Image.Image, text: str = "BRANDGEN PREVIEW") -> Image.Image:
    """
    Diagonal watermark ekler.
    """
    watermark = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark)
    w, h = img.size

    font = get_font(max(24, w // 30), bold=False)

    # Grid şeklinde çapraz watermark
    step = w // 3
    for x in range(-h, w + h, step):
        for y in range(-h, h + h, step // 2):
            draw.text(
                (x, y),
                text,
                font=font,
                fill=(180, 170, 160, 45),
            )

    # Rotasyon
    watermark = watermark.rotate(
        -30, resample=Image.BICUBIC, expand=False, center=(w // 2, h // 2)
    )

    result = img.convert("RGBA")
    result = Image.alpha_composite(result, watermark)
    return result.convert("RGB")


def generate_social_post(
    brand_name: str,
    caption: str,
    primary: str = "#0A0A0A",
    secondary: str = "#F1EBE1",
    size: tuple = (1080, 1080),
) -> Image.Image:
    """
    1:1 sosyal medya post.
    Hem koyu hem açık zemin desteklenir.
    """
    w, h = size
    bg_rgb = hex_to_rgb(primary)
    text_rgb = hex_to_rgb(secondary)

    img = Image.new("RGB", (w, h), bg_rgb)
    draw = ImageDraw.Draw(img)

    # Büyük arka plan harfi
    initials = extract_initials(brand_name)[0]
    bg_font = get_font(int(h * 1.2))
    draw.text((-h * 0.1, -h * 0.2), initials, font=bg_font, fill=ghost_color(primary))

    # Caption metin — alt kısım
    caption_font = get_font(int(h * 0.045))
    margin = 80
    max_width = w - margin * 2

    words = caption.split()
    lines = []
    current = []
    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=caption_font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))

    line_h = int(h * 0.06)
    total_text_h = len(lines) * line_h
    start_y = h - margin - total_text_h - 60

    for i, line in enumerate(lines):
        draw.text((margin, start_y + i * line_h), line, font=caption_font, fill=text_rgb)

    # Brand name alt satır — soluk
    name_font = get_font(int(h * 0.028), bold=False)
    sub_r = (text_rgb[0] + bg_rgb[0]) // 2
    sub_g = (text_rgb[1] + bg_rgb[1]) // 2
    sub_b = (text_rgb[2] + bg_rgb[2]) // 2
    draw.text(
        (margin, h - margin - 28),
        brand_name.upper(),
        font=name_font,
        fill=(sub_r, sub_g, sub_b),
    )

    # Üst sol köşe detayı
    draw.line([(margin, margin), (margin + 60, margin)], fill=text_rgb, width=1)
    draw.line([(margin, margin), (margin, margin + 60)], fill=text_rgb, width=1)

    return img


# ─────────────────────────────────────────────────────────────────────────────
#  SVG LOGO SİSTEMİ — HTML brand kit için yüksek kaliteli vektörel görseller
# ─────────────────────────────────────────────────────────────────────────────

def _svg_data_uri(svg: str) -> str:
    """SVG string → data:image/svg+xml;base64,... URI"""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _e(text: str) -> str:
    """SVG için HTML escape."""
    return html_esc.escape(str(text))


def _accent_from_brief_or_derive(primary: str, secondary: str) -> str:
    """Brief'te accent yoksa secondary kullan."""
    return secondary


def generate_logo_primary_svg(
    brand_name: str,
    primary: str = "#0A0A0A",
    secondary: str = "#F1EBE1",
    accent: str = "",
    tagline: str = "",
) -> str:
    """
    Ana logo SVG — modern, minimal, wordmark tarzı.
    Döner: data URI string.
    """
    acc = accent if accent else secondary
    name_upper = brand_name.upper()
    # Uzun isimler için font size küçült
    char_count = len(name_upper)
    font_size = 96 if char_count <= 6 else (80 if char_count <= 10 else 60)
    tag_text = _e(tagline.upper()) if tagline else ""

    svg = f"""<svg viewBox="0 0 800 320" xmlns="http://www.w3.org/2000/svg" width="800" height="320">
  <defs>
    <linearGradient id="ag" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{acc}" stop-opacity="1"/>
      <stop offset="100%" stop-color="{acc}" stop-opacity="0.4"/>
    </linearGradient>
  </defs>
  <!-- Zemin -->
  <rect width="800" height="320" fill="{primary}"/>
  <!-- Sol accent bar -->
  <rect x="60" y="80" width="4" height="160" fill="{acc}"/>
  <!-- Marka adı -->
  <text x="88" y="185"
        font-family="'Helvetica Neue', 'Arial Black', Arial, sans-serif"
        font-weight="800"
        font-size="{font_size}"
        letter-spacing="-1"
        fill="{secondary}">{_e(name_upper)}</text>
  <!-- Accent alt çizgi -->
  <rect x="88" y="208" width="320" height="2" fill="url(#ag)"/>
  {f'<text x="88" y="240" font-family="Arial, sans-serif" font-weight="400" font-size="13" letter-spacing="5" fill="{acc}" opacity="0.85">{tag_text}</text>' if tag_text else ''}
</svg>"""
    return _svg_data_uri(svg)


def generate_logo_icon_svg(
    brand_name: str,
    primary: str = "#0A0A0A",
    secondary: str = "#F1EBE1",
    accent: str = "",
) -> str:
    """
    İkon/monogram SVG — kare format, geometrik, modern.
    """
    acc = accent if accent else secondary
    initials = extract_initials(brand_name)[:2]
    font_size = 110 if len(initials) == 1 else 80

    svg = f"""<svg viewBox="0 0 320 320" xmlns="http://www.w3.org/2000/svg" width="320" height="320">
  <!-- Zemin -->
  <rect width="320" height="320" fill="{primary}"/>
  <!-- Dış çerçeve -->
  <rect x="12" y="12" width="296" height="296" fill="none" stroke="{acc}" stroke-width="1.5" opacity="0.6"/>
  <!-- İç nokta detayları — köşe -->
  <rect x="12" y="12" width="16" height="1.5" fill="{acc}"/>
  <rect x="12" y="12" width="1.5" height="16" fill="{acc}"/>
  <rect x="292" y="12" width="16" height="1.5" fill="{acc}"/>
  <rect x="306" y="12" width="1.5" height="16" fill="{acc}"/>
  <rect x="12" y="306" width="16" height="1.5" fill="{acc}"/>
  <rect x="12" y="292" width="1.5" height="16" fill="{acc}"/>
  <rect x="292" y="306" width="16" height="1.5" fill="{acc}"/>
  <rect x="306" y="292" width="1.5" height="16" fill="{acc}"/>
  <!-- Monogram -->
  <text x="160" y="195"
        font-family="'Helvetica Neue', 'Arial Black', Arial, sans-serif"
        font-weight="800"
        font-size="{font_size}"
        letter-spacing="-2"
        text-anchor="middle"
        fill="{secondary}">{_e(initials)}</text>
</svg>"""
    return _svg_data_uri(svg)


def generate_logo_reversed_svg(
    brand_name: str,
    primary: str = "#0A0A0A",
    secondary: str = "#F1EBE1",
    accent: str = "",
    tagline: str = "",
) -> str:
    """
    Reversed versiyonu — açık zemin, koyu metin.
    """
    # Renkleri ters çevir
    return generate_logo_primary_svg(brand_name, secondary, primary, accent, tagline)


# ─────────────────────────────────────────────────────────────────────────────
#  AJANS-GRADE LOGO TEMPLATE SİSTEMİ
#  Her template farklı bir stüdyo DNA'sı taşır.
#  Seçim: creative director'ın STÜDYO kararına göre dispatch edilir.
#
#  Template A — Collins:         Bold color block, full-canvas fill, accent stripe
#  Template B — Pentagram:       Dark cinematic, primary-color wordmark, structural bar
#  Template C — Sagmeister:      Oversized first letter, condensed rest
#  Template D — Bureau Borsche:  Diagonal color field, name spans both zones
#  Template E — Base Design:     Offset block, name in contrasting fill
#
#  Tüm fonksiyonlar SVG string döner (data URI DEĞİL — çağıran encode eder)
# ─────────────────────────────────────────────────────────────────────────────

def _is_dark_hex(hex_color: str) -> bool:
    try:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = h[0]*2 + h[1]*2 + h[2]*2
        r, g, b = int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
        return (0.2126*r + 0.7152*g + 0.0722*b) < 0.5
    except Exception:
        return True

def _on_color(hex_bg: str) -> str:
    """Bir renk üzerine okunacak kontrast metin rengi."""
    return "#FFFFFF" if _is_dark_hex(hex_bg) else "#0D0D0D"

def _logo_font_size(name_len: int, canvas_w: int = 720, factor: float = 0.60) -> int:
    """Marka adı karakter sayısına göre ölçülü font-size hesapla."""
    return min(96, max(28, int(canvas_w / max(name_len, 1) / factor)))


# ── Template A: COLOR BLOCK — Collins / Bureau Borsche ───────────────────────
def _tpl_color_block(name, primary, accent, bg, tagline, name_len):
    block_w, accent_w = 630, 42
    fs = _logo_font_size(name_len, canvas_w=block_w - 88)
    text_on = _on_color(primary)
    name_y = 162 if fs >= 70 else 168
    tag_y = min(name_y + 34, 262)
    tag = _e(tagline.upper()[:40])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 280">'
        f'<rect width="800" height="280" fill="{bg}"/>'
        f'<rect x="0" y="0" width="{block_w}" height="280" fill="{primary}"/>'
        f'<rect x="{block_w}" y="0" width="{accent_w}" height="280" fill="{accent}"/>'
        f'<text x="44" y="{name_y}" font-family="\'Arial Black\',\'Helvetica Neue\',Impact,sans-serif"'
        f' font-weight="900" font-size="{fs}" fill="{text_on}">{_e(name)}</text>'
        f'<text x="44" y="{tag_y}" font-family="Arial,sans-serif"'
        f' font-size="13" fill="{text_on}" opacity="0.72" letter-spacing="3">{tag}</text>'
        f'</svg>'
    )


# ── Template B: DARK STATEMENT — Pentagram / Wolff Olins / Landor ────────────
def _tpl_dark_statement(name, primary, secondary, bg, text, tagline, name_len):
    fs = _logo_font_size(name_len, canvas_w=680)
    name_y = 172
    bar_y = name_y + 16
    bar_w = min(int(fs * name_len * 0.58), 710)
    tag = _e(tagline.upper()[:40])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 280">'
        f'<rect width="800" height="280" fill="{bg}"/>'
        f'<text x="44" y="{name_y}" font-family="\'Arial Black\',\'Helvetica Neue\',Impact,sans-serif"'
        f' font-weight="900" font-size="{fs}" fill="{primary}">{_e(name)}</text>'
        f'<rect x="44" y="{bar_y}" width="{bar_w}" height="5" fill="{secondary}"/>'
        f'<text x="756" y="{bar_y + 36}" font-family="Arial,sans-serif"'
        f' font-size="12" fill="{text}" opacity="0.7" letter-spacing="4"'
        f' text-anchor="end">{tag}</text>'
        f'</svg>'
    )


# ── Template C: OVERSIZED INITIAL — Sagmeister & Walsh ───────────────────────
def _tpl_oversized_initial(name, primary, secondary, bg, text, tagline, name_len):
    first = name[0] if name else "?"
    rest  = name[1:] if len(name) > 1 else ""
    big_fs = min(210, 280)
    rest_fs = _logo_font_size(max(len(rest),1), canvas_w=580) if rest else 60
    # First letter approx width: 0.60 × font-size
    rest_x = min(int(big_fs * 0.58) + 28, 460)
    big_y  = 238
    rest_y = 184
    tag_y  = min(rest_y + 42, 264)
    tag = _e(tagline.upper()[:40])
    rest_el = (
        f'<text x="{rest_x}" y="{rest_y}" font-family="\'Arial Black\',\'Helvetica Neue\',Impact,sans-serif"'
        f' font-weight="900" font-size="{rest_fs}" fill="{text}">{_e(rest)}</text>'
        f'<rect x="{rest_x}" y="{rest_y + 12}" width="200" height="4" fill="{secondary}"/>'
        f'<text x="{rest_x}" y="{tag_y}" font-family="Arial,sans-serif"'
        f' font-size="12" fill="{text}" opacity="0.7" letter-spacing="3">{tag}</text>'
    ) if rest else f'<text x="44" y="{tag_y}" font-family="Arial,sans-serif" font-size="12" fill="{text}" opacity="0.7" letter-spacing="3">{tag}</text>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 280">'
        f'<rect width="800" height="280" fill="{bg}"/>'
        f'<text x="28" y="{big_y}" font-family="\'Arial Black\',\'Helvetica Neue\',Impact,sans-serif"'
        f' font-weight="900" font-size="{big_fs}" fill="{primary}">{_e(first)}</text>'
        f'{rest_el}'
        f'</svg>'
    )


# ── Template D: DIAGONAL FIELD — Bureau Borsche / bold brands ────────────────
def _tpl_diagonal_field(name, primary, accent, bg, text, tagline, name_len):
    fs = _logo_font_size(name_len, canvas_w=540)
    name_y = 170
    tag_y  = min(name_y + 36, 264)
    text_on = _on_color(primary)
    tag = _e(tagline.upper()[:40])
    # Diagonal polygon: top-left to mid-right
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 280">'
        f'<rect width="800" height="280" fill="{bg}"/>'
        f'<polygon points="0,0 510,0 370,280 0,280" fill="{primary}"/>'
        f'<rect x="370" y="0" width="36" height="280" fill="{accent}" opacity="0.55"/>'
        f'<text x="44" y="{name_y}" font-family="\'Arial Black\',\'Helvetica Neue\',Impact,sans-serif"'
        f' font-weight="900" font-size="{fs}" fill="{text_on}">{_e(name)}</text>'
        f'<text x="44" y="{tag_y}" font-family="Arial,sans-serif"'
        f' font-size="13" fill="{text_on}" opacity="0.78" letter-spacing="3">{tag}</text>'
        f'</svg>'
    )


# ── Template E: OFFSET BLOCK — Base Design / editorial ───────────────────────
def _tpl_offset_block(name, primary, bg, text, tagline, name_len):
    fs = _logo_font_size(name_len, canvas_w=680)
    blk_x, blk_y, blk_h = 32, 38, 192
    blk_w = min(int(fs * name_len * 0.60) + 64, 740)
    name_y = blk_y + int(blk_h * 0.68)
    tag_y  = min(blk_y + blk_h + 28, 268)
    text_on = _on_color(primary)
    tag = _e(tagline.upper()[:40])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 280">'
        f'<rect width="800" height="280" fill="{bg}"/>'
        f'<rect x="{blk_x}" y="{blk_y}" width="{blk_w}" height="{blk_h}" fill="{primary}"/>'
        f'<text x="{blk_x + 26}" y="{name_y}" font-family="\'Arial Black\',\'Helvetica Neue\',Impact,sans-serif"'
        f' font-weight="900" font-size="{fs}" fill="{text_on}">{_e(name)}</text>'
        f'<text x="{blk_x + 26}" y="{tag_y}" font-family="Arial,sans-serif"'
        f' font-size="13" fill="{text}" opacity="0.7" letter-spacing="3">{tag}</text>'
        f'</svg>'
    )


# ── MONO: Single-color wordmark, transparent background ──────────────────────
def _tpl_mono_wordmark(name, text_color, tagline, name_len):
    fs = _logo_font_size(name_len, canvas_w=700)
    name_y = 172
    tag_y  = min(name_y + 30, 264)
    tag = _e(tagline.upper()[:40])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 280">'
        f'<text x="44" y="{name_y}" font-family="\'Arial Black\',\'Helvetica Neue\',Impact,sans-serif"'
        f' font-weight="900" font-size="{fs}" fill="{text_color}">{_e(name)}</text>'
        f'<text x="44" y="{tag_y}" font-family="Arial,sans-serif"'
        f' font-size="13" fill="{text_color}" opacity="0.55" letter-spacing="3">{tag}</text>'
        f'</svg>'
    )


# ── Stüdyo → Template dispatcher ─────────────────────────────────────────────
_STUDIO_TEMPLATE_MAP = {
    "Collins":          "A",
    "Bureau Borsche":   "D",
    "Sagmeister&Walsh": "C",
    "Pentagram":        "B",
    "Landor":           "B",
    "Wolff Olins":      "B",
    "Base Design":      "E",
}

_ENERGY_TEMPLATE_MAP = {
    "bold":      "A",
    "urgent":    "A",
    "energetic": "A",
    "dynamic":   "D",
    "playful":   "E",
    "cinematic": "B",
    "premium":   "B",
    "luxury":    "B",
    "editorial": "E",
    "corporate": "B",
}


def select_logo_primary_svg(brief: dict, studio_label: str = "") -> str:
    """
    Brief + stüdyo kararına göre doğru template'i seç, SVG string döndür.
    Çağıran: _svg_data_uri() ile encode eder.
    """
    name      = brief.get("brand_name", "BRAND")
    primary   = brief.get("primary_color", "#C9A25A")
    secondary = brief.get("secondary_color", "#8B8B7A")
    accent    = brief.get("accent_color") or secondary
    bg        = brief.get("bg_color", "#0F0D0C")
    energy    = str(brief.get("energy", "cinematic")).lower()
    text      = "#F2EDE4" if _is_dark_hex(bg) else "#1A1A1A"
    tagline   = brief.get("tagline", "")
    name_len  = max(len(name), 1)

    # Stüdyo eşleşmesi (en güvenilir)
    tpl = _STUDIO_TEMPLATE_MAP.get(studio_label, "")

    # Stüdyo yoksa energy'den tahmin et
    if not tpl:
        for kw, t in _ENERGY_TEMPLATE_MAP.items():
            if kw in energy:
                tpl = t
                break

    if not tpl:
        tpl = "A"  # default: color block

    if tpl == "A":
        return _tpl_color_block(name, primary, accent, bg, tagline, name_len)
    elif tpl == "B":
        return _tpl_dark_statement(name, primary, secondary, bg, text, tagline, name_len)
    elif tpl == "C":
        return _tpl_oversized_initial(name, primary, secondary, bg, text, tagline, name_len)
    elif tpl == "D":
        return _tpl_diagonal_field(name, primary, accent, bg, text, tagline, name_len)
    elif tpl == "E":
        return _tpl_offset_block(name, primary, bg, text, tagline, name_len)
    else:
        return _tpl_color_block(name, primary, accent, bg, tagline, name_len)


def select_logo_mono_svg(brief: dict) -> str:
    """
    Mono logo: tek renk wordmark, şeffaf zemin.
    """
    name     = brief.get("brand_name", "BRAND")
    bg       = brief.get("bg_color", "#0F0D0C")
    text     = "#F2EDE4" if _is_dark_hex(bg) else "#1A1A1A"
    tagline  = brief.get("tagline", "")
    name_len = max(len(name), 1)
    return _tpl_mono_wordmark(name, text, tagline, name_len)


# ─────────────────────────────────────────────────────────────────────────────
#  İKON TEMPLATE SİSTEMİ — Python-rendered, Sonnet yok
#
#  I-A: NEGATIVE BLOCK  — Harf, primary blok üzerinden bg rengiyle oyulmuş
#  I-B: DIAGONAL CUT    — Harf üzerinden diagonal şerit kesip geçiyor (hız/enerji)
#  I-C: SPLIT COLOR     — Harf dikey ikiye bölünmüş, iki farklı renk
#  I-D: BOLD FRAME      — Harf bold primary, üst/alt accent şerit (sistematik)
#
#  Seçim: stüdyo kararına göre dispatch. Fallback: energy bazlı.
# ─────────────────────────────────────────────────────────────────────────────

def _icon_negative_block(first, primary, bg, accent):
    """I-A: Primary color bloğun içine harf bg rengiyle oyulmuş. Collins / Landor."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320">'
        f'<rect width="320" height="320" fill="{bg}"/>'
        f'<rect x="20" y="20" width="280" height="280" fill="{primary}"/>'
        f'<text x="160" y="248" text-anchor="middle" '
        f'font-family="\'Arial Black\',\'Helvetica Neue\',Impact,sans-serif" '
        f'font-weight="900" font-size="260" fill="{bg}">{_e(first)}</text>'
        f'<rect x="20" y="272" width="90" height="9" fill="{accent}"/>'
        f'</svg>'
    )


def _icon_diagonal_cut(first, primary, bg, accent):
    """I-B: Harf üzerinden diagonal şerit — hız, keskinlik. Bureau Borsche / bold energy."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320">'
        f'<rect width="320" height="320" fill="{bg}"/>'
        f'<text x="160" y="252" text-anchor="middle" '
        f'font-family="\'Arial Black\',\'Helvetica Neue\',Impact,sans-serif" '
        f'font-weight="900" font-size="268" fill="{primary}">{_e(first)}</text>'
        f'<polygon points="0,96 320,28 320,68 0,136" fill="{bg}"/>'
        f'<rect x="0" y="96" width="320" height="5" fill="{accent}"/>'
        f'</svg>'
    )


def _icon_split_color(first, primary, accent, bg):
    """I-C: Harf dikey ikiye bölünmüş, iki renk. Sagmeister & Walsh / playful."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320">'
        f'<defs>'
        f'<clipPath id="icp-l"><rect x="0" y="0" width="160" height="320"/></clipPath>'
        f'<clipPath id="icp-r"><rect x="160" y="0" width="160" height="320"/></clipPath>'
        f'</defs>'
        f'<rect width="320" height="320" fill="{bg}"/>'
        f'<text clip-path="url(#icp-l)" x="160" y="252" text-anchor="middle" '
        f'font-family="\'Arial Black\',\'Helvetica Neue\',Impact,sans-serif" '
        f'font-weight="900" font-size="268" fill="{primary}">{_e(first)}</text>'
        f'<text clip-path="url(#icp-r)" x="160" y="252" text-anchor="middle" '
        f'font-family="\'Arial Black\',\'Helvetica Neue\',Impact,sans-serif" '
        f'font-weight="900" font-size="268" fill="{accent}">{_e(first)}</text>'
        f'<rect x="158" y="0" width="4" height="320" fill="{bg}"/>'
        f'</svg>'
    )


def _icon_bold_frame(first, primary, bg, accent):
    """I-D: Harf primary renk, üst/alt accent şerit. Pentagram / Wolff Olins."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320">'
        f'<rect width="320" height="320" fill="{bg}"/>'
        f'<text x="160" y="252" text-anchor="middle" '
        f'font-family="\'Arial Black\',\'Helvetica Neue\',Impact,sans-serif" '
        f'font-weight="900" font-size="268" fill="{primary}">{_e(first)}</text>'
        f'<rect x="0" y="0" width="320" height="10" fill="{accent}"/>'
        f'<rect x="0" y="310" width="320" height="10" fill="{accent}"/>'
        f'</svg>'
    )


_STUDIO_ICON_MAP = {
    "Collins":          "A",   # negative block
    "Bureau Borsche":   "B",   # diagonal cut
    "Sagmeister&Walsh": "C",   # split color
    "Pentagram":        "D",   # bold frame
    "Landor":           "A",   # negative block
    "Wolff Olins":      "D",   # bold frame
    "Base Design":      "A",   # negative block
}

_ENERGY_ICON_MAP = {
    "bold":      "B",
    "urgent":    "B",
    "energetic": "B",
    "dynamic":   "C",
    "playful":   "C",
    "cinematic": "A",
    "premium":   "A",
    "luxury":    "A",
}


def select_logo_icon_svg(brief: dict, studio_label: str = "") -> str:
    """
    İkon SVG: Python template, Sonnet yok.
    Harfin kendi formu üzerinde çalışır — dışarıdan ekleme yok.
    """
    name     = brief.get("brand_name", "BRAND")
    first    = name[0] if name else "?"
    primary  = brief.get("primary_color", "#C9A25A")
    secondary= brief.get("secondary_color", "#8B8B7A")
    accent   = brief.get("accent_color") or secondary
    bg       = brief.get("bg_color", "#0F0D0C")
    energy   = str(brief.get("energy", "cinematic")).lower()

    tpl = _STUDIO_ICON_MAP.get(studio_label, "")
    if not tpl:
        for kw, t in _ENERGY_ICON_MAP.items():
            if kw in energy:
                tpl = t
                break
    if not tpl:
        tpl = "A"

    if tpl == "A":
        return _icon_negative_block(first, primary, bg, accent)
    elif tpl == "B":
        return _icon_diagonal_cut(first, primary, bg, accent)
    elif tpl == "C":
        return _icon_split_color(first, primary, accent, bg)
    elif tpl == "D":
        return _icon_bold_frame(first, primary, bg, accent)
    else:
        return _icon_negative_block(first, primary, bg, accent)


def generate_social_post_svg(
    brand_name: str,
    caption: str,
    primary: str = "#0A0A0A",
    secondary: str = "#F1EBE1",
    accent: str = "",
    post_num: int = 1,
) -> str:
    """
    1:1 Instagram post SVG — iki farklı layout.
    Post 1: büyük statement + brand
    Post 2: brand grid / pattern overlay
    """
    acc = accent if accent else secondary
    name_upper = brand_name.upper()
    # Caption'ı max 40 char'da kes, 2 satıra böl
    cap = str(caption)[:80]
    words = cap.split()
    line1, line2 = [], []
    for w in words:
        if len(" ".join(line1 + [w])) <= 28:
            line1.append(w)
        else:
            line2.append(w)
    l1 = " ".join(line1).upper()
    l2 = " ".join(line2).upper() if line2 else ""

    fn = "Helvetica Neue"
    fb = "Arial Black"
    fa = "Arial"

    if post_num == 1:
        l2_line = (
            f'<text x="80" y="610" font-family="{fn}, {fb}, {fa}, sans-serif"'
            f' font-weight="800" font-size="96" letter-spacing="-2"'
            f' fill="{acc}">{_e(l2)}</text>'
        ) if l2 else ""
        svg = (
            f'<svg viewBox="0 0 1080 1080" xmlns="http://www.w3.org/2000/svg" width="1080" height="1080">'
            f'<rect width="1080" height="1080" fill="{primary}"/>'
            f'<circle cx="900" cy="200" r="380" fill="{acc}" opacity="0.06"/>'
            f'<circle cx="900" cy="200" r="220" fill="{acc}" opacity="0.05"/>'
            f'<rect x="80" y="80" width="120" height="3" fill="{acc}"/>'
            f'<text x="80" y="500" font-family="{fn}, {fb}, {fa}, sans-serif"'
            f' font-weight="800" font-size="96" letter-spacing="-2"'
            f' fill="{secondary}">{_e(l1)}</text>'
            f'{l2_line}'
            f'<rect x="80" y="780" width="920" height="1" fill="{secondary}" opacity="0.15"/>'
            f'<text x="80" y="840" font-family="{fn}, {fa}, sans-serif"'
            f' font-weight="700" font-size="28" letter-spacing="8"'
            f' fill="{secondary}" opacity="0.5">{_e(name_upper)}</text>'
            f'<circle cx="980" cy="820" r="8" fill="{acc}"/>'
            f'</svg>'
        )
    else:
        l2_line = (
            f'<text x="80" y="675" font-family="{fn}, {fb}, {fa}, sans-serif"'
            f' font-weight="800" font-size="72" letter-spacing="-1"'
            f' fill="{secondary}">{_e(l2)}</text>'
        ) if l2 else ""
        svg = (
            f'<svg viewBox="0 0 1080 1080" xmlns="http://www.w3.org/2000/svg" width="1080" height="1080">'
            f'<defs><pattern id="grid" x="0" y="0" width="60" height="60" patternUnits="userSpaceOnUse">'
            f'<path d="M 60 0 L 0 0 0 60" fill="none" stroke="{secondary}" stroke-width="0.5" opacity="0.08"/>'
            f'</pattern></defs>'
            f'<rect width="1080" height="1080" fill="{primary}"/>'
            f'<rect width="1080" height="1080" fill="url(#grid)"/>'
            f'<rect x="0" y="400" width="6" height="280" fill="{acc}"/>'
            f'<text x="50" y="640" font-family="{fn}, {fb}, {fa}, sans-serif"'
            f' font-weight="800" font-size="160" letter-spacing="-4"'
            f' fill="{secondary}" opacity="0.08">{_e(name_upper)}</text>'
            f'<text x="80" y="490" font-family="{fn}, {fa}, sans-serif"'
            f' font-weight="400" font-size="18" letter-spacing="6"'
            f' fill="{acc}">{_e(name_upper)}</text>'
            f'<text x="80" y="590" font-family="{fn}, {fb}, {fa}, sans-serif"'
            f' font-weight="800" font-size="72" letter-spacing="-1"'
            f' fill="{secondary}">{_e(l1)}</text>'
            f'{l2_line}'
            f'<rect x="900" y="900" width="100" height="100" fill="none" stroke="{acc}" stroke-width="1.5" opacity="0.4"/>'
            f'<rect x="920" y="920" width="60" height="60" fill="{acc}" opacity="0.15"/>'
            f'</svg>'
        )

    return _svg_data_uri(svg)


def generate_card_front_svg(
    brand_name: str,
    primary: str = "#0A0A0A",
    secondary: str = "#F1EBE1",
    accent: str = "",
    tagline: str = "",
    contact: str = "",
) -> str:
    """
    Kartvizit ön yüz SVG — 3.5:2 oranı (1050x600).
    """
    acc = accent if accent else secondary
    name_upper = brand_name.upper()
    tag_text = tagline.upper() if tagline else ""

    svg = f"""<svg viewBox="0 0 1050 600" xmlns="http://www.w3.org/2000/svg" width="1050" height="600">
  <!-- Zemin -->
  <rect width="1050" height="600" fill="{primary}"/>
  <!-- Accent bar - sol -->
  <rect x="0" y="0" width="6" height="600" fill="{acc}"/>
  <!-- İçerik -->
  <text x="80" y="240"
        font-family="'Helvetica Neue', 'Arial Black', Arial, sans-serif"
        font-weight="800" font-size="64" letter-spacing="-1"
        fill="{secondary}">{_e(name_upper)}</text>
  <rect x="80" y="260" width="200" height="1.5" fill="{acc}" opacity="0.7"/>
  {f'<text x="80" y="310" font-family="Arial, sans-serif" font-weight="400" font-size="14" letter-spacing="4" fill="{acc}" opacity="0.9">{_e(tag_text)}</text>' if tag_text else ''}
  {f'<text x="80" y="420" font-family="Arial, sans-serif" font-weight="400" font-size="16" letter-spacing="1" fill="{secondary}" opacity="0.6">{_e(contact)}</text>' if contact else ''}
  <!-- Sağ alt köşe detayı -->
  <rect x="970" y="540" width="60" height="1" fill="{acc}" opacity="0.5"/>
  <rect x="1030" y="480" width="1" height="60" fill="{acc}" opacity="0.5"/>
</svg>"""
    return _svg_data_uri(svg)
