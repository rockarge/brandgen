"""
Logo üretimi — iki KATMAN (2 Tem 2026 audit sonrası güncellendi, eski "3. katman"
SVG template sistemi kullanılmadığı için legacy_svg_generator.py'ye taşındı):

  1. PIL RASTER (satır ~79-297): generate_logo_primary/icon/reversed/social_post()
     → pipeline.py besliyor (run_pipeline watermarklı preview + finalize_job ZIP).
  2. PIL v2 (satır ~900+): select_logo_primary_png/mono_png/icon_png()
     → html_preview.py besliyor (fal.ai ile birlikte, ödeme öncesi HTML preview).

_is_dark_hex(): her iki katman da kullanıyor, aşağıda tek yerde tanımlı kaldı.
"""

import base64
import html as html_esc
import io as _io
import os
import math
import urllib.request as _urlreq
from pathlib import Path as _Path
from PIL import Image, ImageDraw, ImageFont

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
#  Paylaşılan renk yardımcıları — hem eski PIL raster hem PIL v2 tarafından kullanılıyor
#  (Eski SVG template sistemi burada duruyordu — 2 Tem 2026'da legacy_svg_generator.py'ye
#   taşındı, kod tabanının hiçbir yerinden çağrılmıyordu. Bkz. o dosyanın başlığı.)
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



# ═════════════════════════════════════════════════════════════════════════════
#  PIL LOGO SİSTEMİ v2 — Gerçek font + geometrik marklar → PNG çıktı
#  SVG browser rendering yok. Bebas Neue + Space Grotesk ile PIL çiziyor.
#  Çıktı: data:image/png;base64,... (html_preview.py direkt kullanır)
# ═════════════════════════════════════════════════════════════════════════════

_PIL_FONTS_DIR = _Path(__file__).parent.parent / "assets" / "fonts"
_PIL_FONT_CACHE: dict = {}

_PIL_FONT_URLS = {
    "display": "https://cdn.jsdelivr.net/gh/dharmatype/Bebas-Neue@master/Fonts/BN/BebasNeue-Regular.ttf",
    "body":    "https://cdn.jsdelivr.net/gh/floriankarsten/space-grotesk@master/fonts/ttf/SpaceGrotesk-Bold.ttf",
}


def _pil_dl_fonts() -> None:
    """Font dosyalarını bir kez indir, önbelleğe al."""
    _PIL_FONTS_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in _PIL_FONT_URLS.items():
        dest = _PIL_FONTS_DIR / f"{name}.ttf"
        if dest.exists() and dest.stat().st_size > 8_000:
            continue
        try:
            req = _urlreq.Request(url, headers={"User-Agent": "BrandGen/2.0"})
            with _urlreq.urlopen(req, timeout=20) as r:
                data = r.read()
            if len(data) > 8_000:
                dest.write_bytes(data)
                print(f"[logo] Font indirildi: {name}")
        except Exception as e:
            print(f"[logo] Font indirilemedi ({name}): {e}")


try:
    _pil_dl_fonts()
except Exception:
    pass


def _pil_font(name: str = "display", size: int = 80) -> ImageFont.FreeTypeFont:
    key = (name, size)
    if key in _PIL_FONT_CACHE:
        return _PIL_FONT_CACHE[key]
    path = _PIL_FONTS_DIR / f"{name}.ttf"
    if path.exists():
        try:
            f = ImageFont.truetype(str(path), size)
            _PIL_FONT_CACHE[key] = f
            return f
        except Exception:
            pass
    for p in SYSTEM_FONTS:
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size)
                _PIL_FONT_CACHE[key] = f
                return f
            except Exception:
                continue
    return ImageFont.load_default()


def _png_uri(img: Image.Image) -> str:
    """PIL Image → data:image/png;base64,... URI"""
    buf = _io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _pil_rgb(h: str) -> tuple:
    """#RRGGBB → (R, G, B)"""
    try:
        h2 = h.lstrip("#")
        if len(h2) == 3:
            h2 = h2[0]*2 + h2[1]*2 + h2[2]*2
        return (int(h2[0:2], 16), int(h2[2:4], 16), int(h2[4:6], 16))
    except Exception:
        return (128, 128, 128)


def _bebas_size(char_count: int, avail_w: int, max_s: int = 220, min_s: int = 28) -> int:
    """
    Bebas Neue için yaklaşık font boyutu.
    Her karakter ≈ size × 0.50px genişlik (condensed font).
    """
    return max(min_s, min(max_s, int(avail_w / max(char_count, 1) / 0.50)))


# ── GEOMETRIK MARKLAR — sıfır typography, salt form ─────────────────────────

def _mark_slash(pc: str, ac: str, bg: str, S: int = 640) -> Image.Image:
    """
    Mark A: Üç diyagonal şerit — hız / enerji / ivme.
    Bureau Borsche / Collins / bold energy DNA.
    """
    img = Image.new("RGB", (S, S), _pil_rgb(bg))
    d = ImageDraw.Draw(img)
    y0, y1 = int(S * 0.07), int(S * 0.93)
    shift = int(S * 0.34)
    strips = [
        (int(S * 0.10), int(S * 0.10), ac),
        (int(S * 0.26), int(S * 0.17), pc),
        (int(S * 0.50), int(S * 0.13), pc),
    ]
    for bx, bw, col in strips:
        d.polygon([
            (bx,              y1),
            (bx + bw,         y1),
            (bx + bw + shift, y0),
            (bx + shift,      y0),
        ], fill=_pil_rgb(col))
    return img


def _mark_arc(pc: str, ac: str, bg: str, S: int = 640) -> Image.Image:
    """
    Mark B: Hedef halkası + sağ üst accent dilimi.
    Pentagram / Wolff Olins / premium DNA.
    """
    img = Image.new("RGB", (S, S), _pil_rgb(bg))
    d = ImageDraw.Draw(img)
    cx = cy = S // 2
    OR = int(S * 0.41)
    IR = int(S * 0.25)
    d.ellipse([cx - OR, cy - OR, cx + OR, cy + OR], fill=_pil_rgb(pc))
    d.ellipse([cx - IR, cy - IR, cx + IR, cy + IR], fill=_pil_rgb(bg))
    # Sağ üst çeyrek accent (PIL: 270°=üst, 360°=sağ, clockwise)
    d.pieslice([cx - OR, cy - OR, cx + OR, cy + OR], start=270, end=360, fill=_pil_rgb(ac))
    d.ellipse([cx - IR, cy - IR, cx + IR, cy + IR], fill=_pil_rgb(bg))
    DR = int(S * 0.065)
    d.ellipse([cx - DR, cy - DR, cx + DR, cy + DR], fill=_pil_rgb(ac))
    return img


def _mark_diamond(pc: str, ac: str, bg: str, S: int = 640) -> Image.Image:
    """
    Mark C: Eşkenar dörtgen, dikey iki renkli bölünmüş.
    Sagmeister & Walsh / dynamic DNA.
    """
    img = Image.new("RGB", (S, S), _pil_rgb(bg))
    d = ImageDraw.Draw(img)
    m = int(S * 0.09)
    cx = cy = S // 2
    d.polygon([(cx, m), (S - m, cy), (cx, S - m), (m, cy)], fill=_pil_rgb(pc))
    d.polygon([(cx, m), (S - m, cy), (cx, S - m)], fill=_pil_rgb(ac))
    lw = max(3, S // 100)
    d.line([(cx, m), (cx, S - m)], fill=_pil_rgb(bg), width=lw)
    return img


def _mark_bars(pc: str, ac: str, bg: str, S: int = 640) -> Image.Image:
    """
    Mark D: Üç yatay bar, azalan genişlik.
    Base Design / Pentagram / editorial DNA.
    """
    img = Image.new("RGB", (S, S), _pil_rgb(bg))
    d = ImageDraw.Draw(img)
    x0 = int(S * 0.125)
    bh = int(S * 0.135)
    gap = int(S * 0.065)
    total_h = 3 * bh + 2 * gap
    y0 = (S - total_h) // 2
    fw = S - 2 * x0
    for i, (frac, col) in enumerate([(1.0, ac), (0.72, pc), (0.46, pc)]):
        y = y0 + i * (bh + gap)
        w = int(fw * frac)
        d.rectangle([x0, y, x0 + w, y + bh], fill=_pil_rgb(col))
    return img


def _mark_plus(pc: str, ac: str, bg: str, S: int = 640) -> Image.Image:
    """
    Mark E: Kalın artı — Landor / architectural / corporate DNA.
    Yatay kol primary, dikey kol accent.
    """
    img = Image.new("RGB", (S, S), _pil_rgb(bg))
    d = ImageDraw.Draw(img)
    m = int(S * 0.12)
    arm = int(S * 0.22)
    cx = cy = S // 2
    d.rectangle([cx - arm // 2, m, cx + arm // 2, S - m], fill=_pil_rgb(ac))
    d.rectangle([m, cy - arm // 2, S - m, cy + arm // 2], fill=_pil_rgb(pc))
    return img


_MARK_FNS = {
    "A": _mark_slash,
    "B": _mark_arc,
    "C": _mark_diamond,
    "D": _mark_bars,
    "E": _mark_plus,
}

_STUDIO_MARK_MAP = {
    "Collins":          "A",
    "Bureau Borsche":   "A",
    "Sagmeister&Walsh": "C",
    "Pentagram":        "D",
    "Landor":           "E",
    "Wolff Olins":      "B",
    "Base Design":      "D",
}

_ENERGY_MARK_MAP = {
    "bold":      "A",
    "urgent":    "A",
    "energetic": "A",
    "dynamic":   "C",
    "playful":   "C",
    "cinematic": "B",
    "premium":   "B",
    "luxury":    "B",
    "editorial": "D",
    "corporate": "D",
    "minimal":   "E",
}


# ── HARF TABANLI PIL İKONLAR ──────────────────────────────────────────────────
# Geometrik markların yerini alan, marka adının ilk harfini kullanan ikonlar.
# Her birinin stüdyo DNA'sı var — "swap testi"ni geçen formlar.

def _pil_icon_negative(first: str, pc: str, bg: str, ac: str, S: int = 640) -> Image.Image:
    """
    I-A: Primary renk blok, harf bg rengiyle oyulmuş.
    Collins / Landor / Base Design / minimal.
    Güçlü kontrast, negatif alan — harfin formu boşluktan ortaya çıkar.
    """
    img = Image.new("RGB", (S, S), _pil_rgb(bg))
    d = ImageDraw.Draw(img)
    m = int(S * 0.06)
    d.rectangle([m, m, S - m, S - m], fill=_pil_rgb(pc))
    fs = int(S * 0.74)
    f = _pil_font("display", fs)
    bb = d.textbbox((0, 0), first, font=f)
    tx = (S - (bb[2] - bb[0])) // 2 - bb[0]
    ty = (S - (bb[3] - bb[1])) // 2 - bb[1] - int(S * 0.03)
    d.text((tx, ty), first, font=f, fill=_pil_rgb(bg))
    # Accent bar — alt sol köşe (imza detayı)
    bh = int(S * 0.048)
    d.rectangle([m, S - m - bh, int(S * 0.40), S - m], fill=_pil_rgb(ac))
    return img


def _pil_icon_diagonal(first: str, pc: str, bg: str, ac: str, S: int = 640) -> Image.Image:
    """
    I-B: Harf primary renk, üzerinden diagonal şerit kesiyor.
    Bureau Borsche / bold / energetic.
    Hız, hareket, keskinlik — kesim hattı marka konseptiyle örtüşüyor.
    """
    img = Image.new("RGB", (S, S), _pil_rgb(bg))
    d = ImageDraw.Draw(img)
    fs = int(S * 0.82)
    f = _pil_font("display", fs)
    bb = d.textbbox((0, 0), first, font=f)
    tx = (S - (bb[2] - bb[0])) // 2 - bb[0]
    ty = (S - (bb[3] - bb[1])) // 2 - bb[1] - int(S * 0.04)
    d.text((tx, ty), first, font=f, fill=_pil_rgb(pc))
    # Diagonal kesim şeridi — bg rengiyle üstüne yazıyor (harfi kesiyor)
    cut_top = int(S * 0.16)
    cut_bot = int(S * 0.40)
    drop = int(S * 0.12)
    d.polygon([
        (0, cut_top), (S, cut_top - drop),
        (S, cut_bot - drop), (0, cut_bot)
    ], fill=_pil_rgb(bg))
    # Accent çizgisi — kesim hattının üst kenarı
    stripe_h = int(S * 0.026)
    d.polygon([
        (0, cut_top), (S, cut_top - drop),
        (S, cut_top - drop + stripe_h), (0, cut_top + stripe_h)
    ], fill=_pil_rgb(ac))
    return img


def _pil_icon_split(first: str, pc: str, ac: str, bg: str, S: int = 640) -> Image.Image:
    """
    I-C: Harf dikey ikiye bölünmüş, iki farklı renk.
    Sagmeister & Walsh / playful / dynamic.
    Çift kimlik, gerilim — iki rengin birliği ya da çatışması.
    """
    base = Image.new("RGB", (S, S), _pil_rgb(bg))
    left = Image.new("RGB", (S, S), _pil_rgb(bg))
    right = Image.new("RGB", (S, S), _pil_rgb(bg))
    dl = ImageDraw.Draw(left)
    dr = ImageDraw.Draw(right)
    fs = int(S * 0.82)
    f = _pil_font("display", fs)
    bb = dl.textbbox((0, 0), first, font=f)
    tx = (S - (bb[2] - bb[0])) // 2 - bb[0]
    ty = (S - (bb[3] - bb[1])) // 2 - bb[1] - int(S * 0.04)
    dl.text((tx, ty), first, font=f, fill=_pil_rgb(pc))
    dr.text((tx, ty), first, font=f, fill=_pil_rgb(ac))
    # Sol yarısı left'ten, sağ yarısı right'tan
    base.paste(left.crop((0, 0, S // 2, S)), (0, 0))
    base.paste(right.crop((S // 2, 0, S, S)), (S // 2, 0))
    # Bölme çizgisi — bg rengiyle, ince
    d2 = ImageDraw.Draw(base)
    lw = max(2, S // 120)
    d2.line([(S // 2, 0), (S // 2, S)], fill=_pil_rgb(bg), width=lw)
    return base


def _pil_icon_frame(first: str, pc: str, bg: str, ac: str, S: int = 640) -> Image.Image:
    """
    I-D: Harf primary renk, üst/alt accent şeritleri.
    Pentagram / Wolff Olins / corporate / sistematik.
    Net hiyerarşi, güven veren çerçeveleme.
    """
    img = Image.new("RGB", (S, S), _pil_rgb(bg))
    d = ImageDraw.Draw(img)
    fs = int(S * 0.82)
    f = _pil_font("display", fs)
    bb = d.textbbox((0, 0), first, font=f)
    tx = (S - (bb[2] - bb[0])) // 2 - bb[0]
    ty = (S - (bb[3] - bb[1])) // 2 - bb[1] - int(S * 0.04)
    d.text((tx, ty), first, font=f, fill=_pil_rgb(pc))
    bar = int(S * 0.052)
    d.rectangle([0, 0, S, bar], fill=_pil_rgb(ac))
    d.rectangle([0, S - bar, S, S], fill=_pil_rgb(ac))
    return img


_LETTER_ICON_FNS = {
    "A": _pil_icon_negative,
    "B": _pil_icon_diagonal,
    "C": _pil_icon_split,
    "D": _pil_icon_frame,
}

_STUDIO_LETTER_ICON_MAP = {
    "Collins":          "A",   # negative block — negatif alan = Collins imzası
    "Bureau Borsche":   "B",   # diagonal cut — hız ve kültürel keskinlik
    "Sagmeister&Walsh": "C",   # split — beklenmedik duality, kural kırma
    "Pentagram":        "A",   # negative block — anlam yüklü negatif alan
    "Landor":           "A",   # negative block — temiz, güven veren, kurumsal derinlik
    "Wolff Olins":      "D",   # frame — sistemik, modüler çerçeve
    "Base Design":      "A",   # negative block — minimal, yapısal kesinlik
}

_ENERGY_LETTER_ICON_MAP = {
    "bold":      "B",   # diagonal cut
    "urgent":    "B",
    "energetic": "B",
    "dynamic":   "C",   # split
    "playful":   "C",
    "cinematic": "A",   # negative block
    "premium":   "A",
    "luxury":    "A",
    "editorial": "A",
    "corporate": "D",   # frame
    "minimal":   "A",
}


def _parse_icon_concept(concept: str) -> str:
    """
    Locked icon concept cümlesini parse et → harf ikon variant tipi döner.
    Anatomik talimat → PIL variant eşlemesi.
    """
    if not concept:
        return ""
    c = concept.lower()
    # Diagonal / kesim / şerit → B
    if any(kw in c for kw in ["kes", "cut", "diagonal", "çapraz", "yatay şerit", "şerit", "dilim", "kesik"]):
        return "B"
    # Bölünme / iki renk / yarı → C
    if any(kw in c for kw in ["böl", "split", "ikiye", "iki renk", "yarı", "left", "right", "sağ yarı", "sol yarı"]):
        return "C"
    # Çerçeve / bar / şerit üst+alt → D
    if any(kw in c for kw in ["çerçeve", "frame", "bar", "bantlar", "şerit üst", "şerit alt", "üst ve alt"]):
        return "D"
    # Negatif alan / oyma / boşluk → A
    if any(kw in c for kw in ["negatif", "oyul", "çıkar", "boşluk", "carved", "hollow", "iç boşluk", "dışarıdan"]):
        return "A"
    return ""  # tanımlanamadı → stüdyo/energy dispatch'e bırak


def _draw_wordmark(d: ImageDraw.ImageDraw, name: str, tag: str,
                   x: int, avail_w: int, area_top: int, area_h: int,
                   color: str) -> None:
    """
    Bebas Neue ile brand adı + Space Grotesk ile tagline çizer.
    area_top + area_h alanının içine dikey olarak ortalar.
    """
    fs = _bebas_size(len(name), avail_w)
    f = _pil_font("display", fs)
    bb = d.textbbox((0, 0), name, font=f)
    nh = bb[3] - bb[1]
    name_y = area_top + (area_h - nh) // 2 - int(area_h * 0.05)
    d.text((x, name_y), name, font=f, fill=_pil_rgb(color))
    if tag:
        ts = max(22, fs // 5)
        tf = _pil_font("body", ts)
        d.text((x, name_y + nh + 18), tag.upper()[:42], font=tf, fill=_pil_rgb(color))


# ── ANA LOGO ─────────────────────────────────────────────────────────────────
# NOT (3 Tem 2026 hotfix): Bu iki dict, ölü SVG kodu temizliği sırasında (2 Tem)
# yanlışlıkla legacy_svg_generator.py'ye taşınmıştı — ama select_logo_primary_png
# (aşağıda, CANLI fonksiyon) bunlara bağımlıydı. Üretimde "_STUDIO_TEMPLATE_MAP is
# not defined" hatasına yol açtı, buraya geri taşındı. Ders: dead-code temizliğinde
# fonksiyon çağrılarını grep'lemek yetmiyor, module-level sabitleri de ayrı kontrol
# etmek gerekiyor — statik syntax kontrolü (py_compile) bu tür hatayı yakalamaz,
# sadece çalışma zamanında patlar.
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


def select_logo_primary_png(brief: dict, studio_label: str = "", pil_params: dict | None = None) -> str:
    """
    ANA logo: PIL composition + Bebas Neue.
    Seçim önceliği: pil_params["template"] → stüdyo map → energy_tier map → default A.

    pil_params: Tasarım direktörünün PIL_LOGO kararı (html_preview.py parse eder).
                {"template": "A"/"B"/"C"/"D"/"E"} — override yapar.

    PNG data URI döner (SVG yok, browser font yok).
    """
    name   = brief.get("brand_name", "BRAND").upper()
    pc     = brief.get("primary_color", "#C9A25A")
    sc     = brief.get("secondary_color", "#8B8B7A")
    ac     = brief.get("accent_color") or sc
    bg     = brief.get("bg_color", "#0F0D0C")
    tag    = brief.get("tagline", "")
    # energy_tier varsa daha granüler, yoksa eski energy'e bak
    energy = str(brief.get("energy_tier", brief.get("energy", "cinematic"))).lower()

    # 1. Tasarım direktörü override (en yüksek öncelik)
    tpl = (pil_params or {}).get("template", "")

    # 2. Stüdyo eşlemesi
    if not tpl:
        tpl = _STUDIO_TEMPLATE_MAP.get(studio_label, "")

    # 3. Energy_tier → template
    if not tpl:
        _ENERGY_TIER_TEMPLATE = {
            "bold":      "A",  # color block — cesur, dolu
            "luxury":    "B",  # dark statement — ağır, premium
            "cinematic": "B",  # dark statement — dramatik zemin
            "playful":   "E",  # offset block — hafif, asimetrik
            "minimal":   "B",  # dark statement — sessiz güç
        }
        tpl = _ENERGY_TIER_TEMPLATE.get(energy, "")

    # 4. Legacy energy keyword fallback (eski davranış korunuyor)
    if not tpl:
        for kw, t in _ENERGY_TEMPLATE_MAP.items():
            if kw in energy:
                tpl = t
                break

    if not tpl:
        tpl = "A"

    W, H = 1600, 560
    img = Image.new("RGB", (W, H), _pil_rgb(bg))
    d = ImageDraw.Draw(img)

    if tpl == "A":
        # Bold color block — Collins / Bureau Borsche
        bw = int(W * 0.785)
        aw = int(W * 0.055)
        d.rectangle([0, 0, bw, H], fill=_pil_rgb(pc))
        d.rectangle([bw, 0, bw + aw, H], fill=_pil_rgb(ac))
        tc = "#FFFFFF" if _is_dark_hex(pc) else "#0D0D0D"
        _draw_wordmark(d, name, tag, 88, bw - 100, 0, H, tc)

    elif tpl == "B":
        # Dark statement — Pentagram / Wolff Olins
        tc = "#F2EDE4" if _is_dark_hex(bg) else "#1A1A1A"
        _draw_wordmark(d, name, "", 88, W - 176, 0, H, pc)
        fs = _bebas_size(len(name), W - 176)
        f = _pil_font("display", fs)
        bb = d.textbbox((0, 0), name, font=f)
        nh = bb[3] - bb[1]
        name_y = (H - nh) // 2 - int(H * 0.05)
        bar_y = name_y + nh + 16
        bar_w = min(bb[2] - bb[0] + 8, W - 200)
        d.rectangle([88, bar_y, 88 + bar_w, bar_y + 10], fill=_pil_rgb(ac))
        if tag:
            tf = _pil_font("body", 28)
            tw_bb = d.textbbox((0, 0), tag.upper()[:42], font=tf)
            tw = tw_bb[2] - tw_bb[0]
            d.text((W - 88 - tw, bar_y + 28), tag.upper()[:42], font=tf, fill=_pil_rgb(sc))

    elif tpl == "C":
        # Oversized initial — Sagmeister & Walsh
        first = name[0] if name else "?"
        rest = name[1:]
        big_fs = min(490, H + 60)
        bf = _pil_font("display", big_fs)
        d.text((20, -int(H * 0.09)), first, font=bf, fill=_pil_rgb(pc))
        if rest:
            bb1 = d.textbbox((20, -int(H * 0.09)), first, font=bf)
            rx = max(bb1[2] - 15, int(W * 0.30))
            rest_fs = _bebas_size(len(rest), W - rx - 60)
            rf = _pil_font("display", rest_fs)
            rbb = d.textbbox((0, 0), rest, font=rf)
            rh = rbb[3] - rbb[1]
            ry = (H - rh) // 2 - int(H * 0.05)
            d.text((rx, ry), rest, font=rf, fill=_pil_rgb(sc))

    elif tpl == "D":
        # Diagonal field — Bureau Borsche
        px = int(W * 0.64)
        d.polygon([(0, 0), (px, 0), (int(W * 0.46), H), (0, H)], fill=_pil_rgb(pc))
        acc_pts = [(px, 0), (px + int(W * 0.05), 0),
                   (int(W * 0.46) + int(W * 0.05), H), (int(W * 0.46), H)]
        d.polygon(acc_pts, fill=_pil_rgb(ac))
        tc = "#FFFFFF" if _is_dark_hex(pc) else "#0D0D0D"
        _draw_wordmark(d, name, tag, 88, px - 100, 0, H, tc)

    elif tpl == "E":
        # Offset block — Base Design
        bx, by = 64, int(H * 0.13)
        bw2 = int(W * 0.82)
        bh = int(H * 0.62)
        d.rectangle([bx, by, bx + bw2, by + bh], fill=_pil_rgb(pc))
        tc = "#FFFFFF" if _is_dark_hex(pc) else "#0D0D0D"
        _draw_wordmark(d, name, tag, bx + 48, bw2 - 100, by, bh, tc)

    return _png_uri(img)


# ── MONO LOGO ─────────────────────────────────────────────────────────────────

def select_logo_mono_png(brief: dict) -> str:
    """
    MONO logo: tek renk wordmark, GERÇEK şeffaf zemin (RGBA) — herhangi bir
    zemin rengine yerleştirilebilir (kit'in "mono" logo vaadi budur).
    PNG data URI döner.

    2 Tem 2026 fix (audit B12/B13):
    - Önceden Image.new("RGB", ...) ile bg_color dolgulu üretiliyordu — "şeffaf zemin"
      dokümantasyonu yalandı, kutu farklı renk zemine konunca kendi rengiyle blok
      olarak duruyordu. Artık gerçek RGBA + alpha=0 zemin.
    - Önceden dikey hizalama bb[1] (top bearing) düşülmeden hesaplanıyordu, wordmark
      kutu içinde gözle görülür şekilde aşağı kaçıyordu. Artık merkezleme matematiği
      top bearing'i hesaba katıyor.
    - Font hâlâ sabit Bebas Neue — brief'in seçtiği font_display'e (örn. "Playfair
      Display", "Fredoka") dinamik eşleme bu pass'e dahil değil: bu sandbox'tan
      Google Fonts CDN'ine erişim yok (network allowlist), doğrulamadan yeni font
      URL'si eklemek B14'ün (sessiz font kırılması) aynısını tekrar üretir riski
      taşıyor. Ayrı bir P1 olarak bırakıldı — Fly.io ortamında doğrulanabilir.
    """
    name = brief.get("brand_name", "BRAND").upper()
    bg   = brief.get("bg_color", "#0F0D0C")
    tc   = "#F2EDE4" if _is_dark_hex(bg) else "#1A1A1A"
    tag  = brief.get("tagline", "")

    W, H = 1600, 420
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))   # gerçek şeffaflık
    d   = ImageDraw.Draw(img)
    tc_rgba = _pil_rgb(tc) + (255,)

    fs = _bebas_size(len(name), W - 100)
    f  = _pil_font("display", fs)
    bb = d.textbbox((0, 0), name, font=f)
    nh = bb[3] - bb[1]
    name_y = (H - nh) // 2 - bb[1]          # top bearing düşüldü — artık gerçekten ortalı
    d.text((50, name_y), name, font=f, fill=tc_rgba)

    if tag:
        ts = max(24, fs // 5)
        tf = _pil_font("body", ts)
        d.text((50, name_y + nh + 18), tag.upper()[:42], font=tf, fill=tc_rgba)

    return _png_uri(img)


# ── İKON LOGO ─────────────────────────────────────────────────────────────────

def select_logo_icon_png(brief: dict, studio_label: str = "", concept: str = "") -> str:
    """
    İKON: Marka adının ilk harfi + stüdyo DNA stilizasyonu.
    Öncelik: concept cümlesi → stüdyo map → energy map → default (A).

    concept: _generate_locked_icon_concept() çıktısı — anatomik SVG talimatı.
             Bu cümle parse edilerek harf ikon varyantı seçilir.

    PNG data URI döner.
    """
    name = brief.get("brand_name", "BRAND")
    first = (name[0] if name else "?").upper()
    pc = brief.get("primary_color", "#C9A25A")
    ac = brief.get("accent_color") or brief.get("secondary_color", "#8B8B7A")
    bg = brief.get("bg_color", "#0F0D0C")
    en = str(brief.get("energy_tier", brief.get("energy", "cinematic"))).lower()

    # 1. Concept cümlesinden parse et (en özgün, marka-spesifik)
    key = _parse_icon_concept(concept)

    # 2. Stüdyo eşlemesi
    if not key:
        key = _STUDIO_LETTER_ICON_MAP.get(studio_label, "")

    # 3. Energy_tier fallback
    if not key:
        for kw, k in _ENERGY_LETTER_ICON_MAP.items():
            if kw in en:
                key = k
                break

    if not key:
        key = "A"  # default: negative block

    fn = _LETTER_ICON_FNS.get(key, _pil_icon_negative)
    return _png_uri(fn(first, pc, bg, ac))
