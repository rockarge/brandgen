"""
Logo üretimi — iki KATMAN (2 Tem 2026 audit sonrası güncellendi, eski "3. katman"
SVG template sistemi kullanılmadığı için legacy_svg_generator.py'ye taşındı):

  1. PIL RASTER (satır ~79-297): generate_logo_primary/icon/reversed/social_post()
     → pipeline.py besliyor (run_pipeline watermarklı preview + finalize_job ZIP).
  2. PIL v2 (satır ~900+): select_logo_primary_png/mono_png/tipo_png/icon_png()
     → html_preview.py besliyor (fal.ai ile birlikte, ödeme öncesi HTML preview).

_is_dark_hex(): her iki katman da kullanıyor, aşağıda tek yerde tanımlı kaldı.
"""
# Python 3.9 uyumu (Mac'te lokal QA koşabilsin): 3.10+ tip
# annotation'larini (dict | None) string'e cevirir, runtime degismez.
from __future__ import annotations


import base64
import html as html_esc
import io as _io
import os
import math
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


def _tr_upper(s: str) -> str:
    """Turkce-dogru buyuk harf: i->I noktali (Python .upper() i->I yapar; 20 Tem 2026
    QA v2 bulgusu: 'Meridyen'->'MERIDYEN' yanlisti, 'MERIDYEN'.replace ile duzeltildi).
    SADECE canli select_* yolunda kullanilir; legacy collage fonksiyonlarina dokunulmadi."""
    return (s or "").replace("i", "\u0130").upper()


def _brand_upper(brief: dict) -> str:
    """Marka adinin buyuk harfli hali — DIL BILINCLI. (20 Tem 2026)

    SORUN: _tr_upper her ismi Turkce sanip i -> noktali I yapiyordu.
    "Sigorta" dogru cikiyordu ama "Axis" / "Logistics" YANLIS cikiyordu.
    Kod tek basina bir kelimenin Turkce mi yabanci mi oldugunu bilemez.

    COZUM: karari dili bilen katman versin — Sonnet `brand_name_upper` alanini
    kelime kelime dogru buyutuyor (semada ornekli kural var). Burada sadece
    okunuyor. Alan bossa (eski job / Sonnet atladi) eski davranisa dusulur:
    Turkce varsayimi, cunku musteri tabani agirlikli Turkce.

    Guvenlik: donen deger marka adiyla ayni harf sayisinda degilse (Sonnet
    kisaltmis/uydurmus olabilir) guvenilmez sayilir, fallback devreye girer.
    """
    raw = (brief.get("brand_name") or "").strip()
    up = (brief.get("brand_name_upper") or "").strip()
    if up and len(up) == len(raw):
        return up
    return _tr_upper(raw)


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

# NOT (3 Tem 2026 hotfix #2 — GERİ ALINDI, bkz. calisma-kurallari.md kural 8):
# Burada önce eski kırık CDN URL'lerini (404 veriyordu, bkz. B14) çalışan bir
# google/fonts linkiyle "düzeltmiştim". Serhat bunu durdurdu: (1) Bebas Neue yeni
# işlerde zaten terk edildi — burada "düzeltip" geri getirmek yanlış yön, (2) sunucu
# runtime'da kendi kendine internetten dosya indirmesi — onay almadan hiçbir yerden
# dosya indirilmeyecek kuralına giriyor, sunucu tarafı otomatik indirme de dahil.
# Otomatik CDN indirme mekanizması bu yüzden TAMAMEN KALDIRILDI.
#
# Şu an: assets/fonts/ klasörüne Serhat kendi koyduğu .ttf dosyaları varsa onlar
# kullanılır (aşağıdaki _pil_font() zaten önce oraya bakıyor); yoksa SYSTEM_FONTS
# fallback'e düşer (DejaVu/Liberation). Yeni display/body fontu kararı Serhat'tan
# gelmeden burada font ismi/URL varsayımı yapılmayacak.
_PIL_FONT_URLS: dict = {}


def _pil_font(name: str = "display", size: int = 80) -> ImageFont.FreeTypeFont:
    key = (name, size)
    if key in _PIL_FONT_CACHE:
        return _PIL_FONT_CACHE[key]
    path = _PIL_FONTS_DIR / f"{name}.ttf"
    if path.exists():
        try:
            f = ImageFont.truetype(str(path), size)
            if name == "body":
                # Eğer buraya konan body.ttf variable font ise (örn. Space Grotesk),
                # bold ekseni açıkça set edilmezse Regular (400) ağırlıkta çıkar.
                # Statik bir Bold .ttf konursa bu satır no-op kalır (except'e düşer).
                try:
                    f.set_variation_by_axes([700])
                except Exception:
                    pass
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


# ── TEMPLATE FONT SİSTEMİ v3 (20 Tem 2026 — font havuzu genişletildi) ─────────
# Her template'in KENDİ karakter fontu var (Serhat onayıyla Google Fonts'tan
# static/instance ttf indirildi, latin-ext/Türkçe destekli):
#   A Anton · B Bodoni Moda · C Unbounded(700) · D Archivo Black · E Space Grotesk
#   F Bungee · G DM Serif Display · H Alfa Slab One · I Libre Franklin(700)
#   J Fredoka (eski tpl_C dosyası; yedek: _bak_tpl_C_fredoka.ttf.bak)
# _TPL_FONT_ALIAS artık sadece EMNİYET AĞI: tpl_X.ttf diskte yoksa alias'a düşer
# (eski davranış), dosya varsa her template kendi fontunu kullanır.
_TPL_FONT_ALIAS = {
    "F": "D",   # fallback: Archivo Black
    "G": "B",   # fallback: Bodoni Moda
    "H": "E",   # fallback: Space Grotesk
    "I": "E",   # fallback: Space Grotesk
    "J": "C",   # fallback: (artık Unbounded — J dosyası var olduğu sürece kullanılmaz)
}


def _tpl_font_name(tpl: str) -> str:
    """Template kodu → font dosya adı. Dosya-öncelikli: tpl_X.ttf varsa o,
    yoksa alias fallback (v3, 20 Tem 2026)."""
    if (_PIL_FONTS_DIR / f"tpl_{tpl}.ttf").exists():
        return f"tpl_{tpl}"
    return f"tpl_{_TPL_FONT_ALIAS.get(tpl, tpl)}"


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


def _fit_font_size(text: str, font_name: str, avail_w: int, max_s: int = 220, min_s: int = 28) -> int:
    """
    3 Tem 2026 hotfix #5 — font-agnostic sığdırma. `_bebas_size()`nin aksine
    tek bir fontun karakter/genişlik oranını varsaymaz: GERÇEK fontta (tpl_A..E
    veya body) referans boyutta metni ölçüp avail_w'ye orantılı olarak ölçekler.
    5 curated font çok farklı genişliklere sahip olduğu için (Anton dar,
    Bodoni Moda/Archivo Black geniş) tek formülle hepsini doğru sığdırmak
    mümkün değildi — bu yüzden her font kendi gerçek metriğiyle ölçülüyor.
    %4 güvenlik payı bırakır (hinting/subpixel farkları taşırmasın diye).
    """
    ref = 200
    f = _pil_font(font_name, ref)
    try:
        w = f.getlength(text)
    except Exception:
        tmp = Image.new("RGB", (10, 10))
        d = ImageDraw.Draw(tmp)
        bb = d.textbbox((0, 0), text, font=f)
        w = bb[2] - bb[0]
    if not w or w <= 0:
        return max_s
    size = int(ref * (avail_w / w) * 0.96)
    return max(min_s, min(max_s, size))


# ── HARF TABANLI PIL İKONLAR ──────────────────────────────────────────────────
# (Not: bu bölümden önce eskiden "geometrik marklar" — _mark_slash/_arc/_diamond/
#  _bars/_plus, _MARK_FNS, _STUDIO_MARK_MAP, _ENERGY_MARK_MAP — vardı. Letter-icon
#  sistemi bunların yerini aldı (select_logo_icon_png artık _LETTER_ICON_FNS
#  kullanıyor). Hiçbir yerden çağrılmadığı grep ile doğrulandı, 4 Tem 2026'da
#  legacy_svg_generator.py'ye taşındı — bkz. o dosyanın sonu.)
# Geometrik markların yerini alan, marka adının ilk harfini kullanan ikonlar.
# Her birinin stüdyo DNA'sı var — "swap testi"ni geçen formlar.

def _pil_icon_negative(first: str, pc: str, bg: str, ac: str, S: int = 640, tpl: str = "A") -> Image.Image:
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
    f = _pil_font(_tpl_font_name(tpl), fs)
    bb = d.textbbox((0, 0), first, font=f)
    tx = (S - (bb[2] - bb[0])) // 2 - bb[0]
    ty = (S - (bb[3] - bb[1])) // 2 - bb[1] - int(S * 0.03)
    d.text((tx, ty), first, font=f, fill=_pil_rgb(bg))
    # Accent bar — alt sol köşe (imza detayı)
    bh = int(S * 0.048)
    d.rectangle([m, S - m - bh, int(S * 0.40), S - m], fill=_pil_rgb(ac))
    return img


def _pil_icon_diagonal(first: str, pc: str, bg: str, ac: str, S: int = 640, tpl: str = "A") -> Image.Image:
    """
    I-B: Harf primary renk, üzerinden diagonal şerit kesiyor.
    Bureau Borsche / bold / energetic.
    Hız, hareket, keskinlik — kesim hattı marka konseptiyle örtüşüyor.
    """
    img = Image.new("RGB", (S, S), _pil_rgb(bg))
    d = ImageDraw.Draw(img)
    fs = int(S * 0.82)
    f = _pil_font(_tpl_font_name(tpl), fs)
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


def _pil_icon_split(first: str, pc: str, ac: str, bg: str, S: int = 640, tpl: str = "A") -> Image.Image:
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
    f = _pil_font(_tpl_font_name(tpl), fs)
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


def _pil_icon_frame(first: str, pc: str, bg: str, ac: str, S: int = 640, tpl: str = "A") -> Image.Image:
    """
    I-D: Harf primary renk, üst/alt accent şeritleri.
    Pentagram / Wolff Olins / corporate / sistematik.
    Net hiyerarşi, güven veren çerçeveleme.
    """
    img = Image.new("RGB", (S, S), _pil_rgb(bg))
    d = ImageDraw.Draw(img)
    fs = int(S * 0.82)
    f = _pil_font(_tpl_font_name(tpl), fs)
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
    "Sagmeister & Walsh": "C",   # split — beklenmedik duality, kural kırma
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
                   color: str, tpl: str = "A") -> None:
    """
    tpl'e göre seçilmiş kürasyonlu marka fontuyla (tpl_A..E.ttf) brand adı,
    Manrope (body.ttf) ile tagline çizer — 3 Tem 2026: artık her marka kendi
    template'ine (A-E) bağlı kürasyonlu bir display fontu kullanıyor, sabit tek
    font değil (bkz. _resolve_template).
    area_top + area_h alanının içine dikey olarak ortalar.
    """
    fs = _fit_font_size(name, _tpl_font_name(tpl), avail_w)
    f = _pil_font(_tpl_font_name(tpl), fs)
    bb = d.textbbox((0, 0), name, font=f)
    nh = bb[3] - bb[1]
    # NOT (3 Tem 2026 hotfix #3 — GERÇEK KÖK NEDEN): "name_y" PIL'in text-çizme
    # ORİJİNİ (anchor "la" — ascender hattı), ink'in görsel üst kenarı DEĞİL. Eski
    # kod bunu aynı şey sanıp `name_y + nh` ile tagline'ı konumlandırıyordu — Bebas
    # Neue'de bb[1] (üst boşluk) ~0 olduğu için tesadüfen doğru gibi duruyordu.
    # Bodoni Moda gibi bb[1]=81px olan bir fontta bu hata accent çubuğunu/tagline'ı
    # doğrudan HARFLERİN ORTASINA düşürdü (font-per-marka testinde yakalandı).
    # Doğrusu: ink_top hedefi hesapla, ORIGIN'i ink_top - bb[1] olarak geriye çöz.
    ink_top = area_top + (area_h - nh) // 2 - int(area_h * 0.05)
    name_y = ink_top - bb[1]
    d.text((x, name_y), name, font=f, fill=_pil_rgb(color))
    if tag:
        ts = max(22, fs // 5)
        tf = _pil_font("body", ts)
        # Boşluk fs ile orantılı (büyük fontlarda sabit px yetmiyordu) — 0.16'dan
        # 0.20'ye çıkarıldı, farklı fontların descender/line-gap farklarına pay bırakır.
        gap = max(20, int(fs * 0.20))
        ink_bottom = ink_top + nh
        d.text((x, ink_bottom + gap), _tr_upper(tag)[:42], font=tf, fill=_pil_rgb(color))


# ═════════════════════════════════════════════════════════════════════════════
#  OPTİK DİZGİ MOTORU + STİL SİNYALLERİ (20 Tem 2026 — Görev 2A)
#  Kalite kök nedeni: "dizilmiş" görünüm. Çözüm: template başına tracking kararı,
#  gerçek font metriğiyle tracked sığdırma, merkezî kontrast guard'ı ve brief'ten
#  stil sinyali okuyan resolver. Not: _draw_tracked/_tracked_width TİPO bölümünde
#  tanımlı — modül seviyesinde sıra önemsiz, çağrı runtime'da çözülür.
# ═════════════════════════════════════════════════════════════════════════════

# Template başına optik tracking (fs oranı). A-E'de 0 — mevcut davranış DEĞİŞMEZ
# (tpl B'nin bar geometrisi _fit_font_size ile senkron, ona dokunulmuyor).
_TPL_TRACKING = {
    "F": 0.02, "G": 0.06, "H": 0.10, "I": 0.04, "J": 0.0,
}


def _fit_tracked(text: str, font_name: str, avail_w: int, k: float,
                 max_s: int = 220, min_s: int = 28) -> int:
    """Tracking'i hesaba katan font sığdırma (tipo'daki kapalı formülün genel hali)."""
    ref = 200
    f_ref = _pil_font(font_name, ref)
    try:
        w_ref = sum(f_ref.getlength(ch) for ch in text)
    except Exception:
        return min_s
    per_fs = w_ref / ref + k * max(0, len(text) - 1)
    if per_fs <= 0:
        return max_s
    return max(min_s, min(max_s, int((avail_w * 0.96) / per_fs)))


def _cguard(color: str, bg: str) -> str:
    """Kontrast guard'ı — hotfix #7 pattern'inin merkezî hali. color, bg ile aynı
    koyu/açık kategorideyse güvenli nötre düşer (Meridyen Galeri dersi)."""
    return color if _is_dark_hex(color) != _is_dark_hex(bg) else (
        "#F2EDE4" if _is_dark_hex(bg) else "#1A1A1A"
    )


# Brief'ten stil sinyali → template. Sıra ÖNEMLİ: kurumsal önce (VonArt koşullu
# kararı, 20 Tem: kurumsal sinyal gelirse classic corporate template; default
# anti-jenerik kalır — stil-referans.md §1c2).
_CORPORATE_SIGNALS = (
    "corporate", "kurumsal", "hukuk", "law firm", "legal", "avukat", "finans",
    "finance", "banka", "bank", "sigorta", "insurance", "muhasebe", "accounting",
    "danışmanlık", "consulting", "kamu", "holding", "gayrimenkul", "real estate",
)
_EDITORIAL_SIGNALS = (
    "luxury", "lüks", "editorial", "editoryal", "couture", "galeri", "gallery",
    "sanat", "dergi", "magazine", "mücevher", "jewel", "parfüm", "fine dining",
)
_RETRO_SIGNALS = (
    "retro", "synth", "arcade", "gaming", "oyun stüdyo", "siber", "cyber",
    "uzay", "space", "fütür", "futur", "neon", "yazılım", "software", "tech",
    # 20 Tem canlı test bulgusu (Piksel Işık): Sonnet dna_sector'e "Lüks/Premium"
    # yazınca retro marka editorial'e (G) düştü — retro kelime dağarcığı genişletildi
    "nostalj", "piksel", "pixel", "synthwave", "8-bit", "jeton", "atari", "vhs",
)
_CRAFT_SIGNALS = (
    "kahve", "coffee", "craft", "el yapımı", "handmade", "bira", "brew",
    "roast", "atölye", "bakery", "fırın", "şarap", "wine", "organik",
    "organic", "doğal", "natural",
)


def _style_signal(brief: dict) -> str:
    """Sektör/konsept/mood metninden template sinyali çıkarır. Bulamazsa ''."""
    parts = [
        str(brief.get("sector", "")),
        str((brief.get("studio_dna") or {}).get("sector", "")),
        str(brief.get("concept_statement", "")),
        " ".join(str(m) for m in (brief.get("mood_words") or [])),
        str(brief.get("energy", "")),
    ]
    blob = " ".join(parts).lower()
    # Sıra (20 Tem revizyonu): retro, editorial'den ÖNCE — Sonnet retro markalara
    # "Lüks/Premium" dna_sector'ü yazabiliyor (Piksel Işık canlı bulgusu); gerçek
    # lüks/editoryal markada ise retro kelimesi geçmez, yanlış pozitif riski düşük.
    for signals, tpl in (
        (_CORPORATE_SIGNALS, "I"),
        (_RETRO_SIGNALS, "F"),
        (_EDITORIAL_SIGNALS, "G"),
        (_CRAFT_SIGNALS, "H"),
    ):
        if any(s in blob for s in signals):
            return tpl
    return ""


def _qa_flags(tpl: str, fs: int, name: str) -> None:
    """QA kapısı (ölçülebilir kısım) — anti-jenerik checklist'in koda dökülebilen
    maddeleri. Swap testi insan gözü ister; burada sadece log uyarısı üretilir,
    pipeline ASLA kırılmaz."""
    if fs <= 34:
        print(f"[logo_qa] UYARI tpl={tpl}: '{name}' için fs={fs} çok küçük — uzun isim, lockup sıkışıyor")
    if len(name) > 24:
        print(f"[logo_qa] UYARI tpl={tpl}: isim {len(name)} karakter — kit önizlemede manuel kontrol önerilir")


# ── ANA LOGO ─────────────────────────────────────────────────────────────────
# NOT (3 Tem 2026 hotfix): Bu iki dict, ölü SVG kodu temizliği sırasında (2 Tem)
# yanlışlıkla legacy_svg_generator.py'ye taşınmıştı — ama select_logo_primary_png
# (aşağıda, CANLI fonksiyon) bunlara bağımlıydı. Üretimde "_STUDIO_TEMPLATE_MAP is
# not defined" hatasına yol açtı, buraya geri taşındı. Ders: dead-code temizliğinde
# fonksiyon çağrılarını grep'lemek yetmiyor, module-level sabitleri de ayrı kontrol
# etmek gerekiyor — statik syntax kontrolü (py_compile) bu tür hatayı yakalamaz,
# sadece çalışma zamanında patlar.
#
# NOT (3 Tem 2026 hotfix #6): "Sagmeister & Walsh" anahtarı üç stüdyo sözlüğünde
# de (_STUDIO_TEMPLATE_MAP, _STUDIO_MARK_MAP, _STUDIO_LETTER_ICON_MAP) boşluksuz
# yazılmıştı ("Sagmeister&Walsh"), ama brand_brief.py'nin gerçek studio_dna
# label'ı boşluklu ("Sagmeister & Walsh") — string eşitliği asla sağlanmadığı
# için bu stüdyoya atanan HİÇBİR marka template C'ye (oversized initial), mark
# C'ye (diamond) veya letter-icon C'ye (split) hiç ulaşamıyordu, sessizce
# fallback'e düşüyordu. 3 farklı prompt'la (Rampa Skate/Meridyen Galeri/Hız
# Rotası) yapılan canlı testte "hepsi B'ye düşüyor" bulgusunun bir kısmı bu
# yüzdendi. Üç sözlükte de boşluklu hale getirildi.
_STUDIO_TEMPLATE_MAP = {
    "Collins":          "A",
    "Bureau Borsche":   "D",
    "Sagmeister & Walsh": "C",
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

_ENERGY_TIER_TEMPLATE = {
    "bold":      "A",  # color block — cesur, dolu
    "luxury":    "G",  # editorial masthead — 20 Tem 2026 v2: B yerine G (serif, editoryal)
    "cinematic": "B",  # dark statement — dramatik zemin
    "playful":   "J",  # playful stack — 20 Tem 2026 v2: E yerine J (Fredoka, stacked lockup)
    "minimal":   "B",  # dark statement — sessiz güç
}


def _resolve_template(brief: dict, studio_label: str = "") -> str:
    """
    ANA logo, MONO/TİPO ve İKON'un font+şekil kişiliğini paylaşması için TEK
    şablon karar mekanizması (3 Tem 2026 font-per-marka eklenirken çıkarıldı).
    Önceden bu mantık sadece select_logo_primary_png içinde vardı — mono/icon
    hiç template hesaplamıyordu, bu yüzden hep aynı sabit fontu kullanıyorlardı.

    3 Tem 2026 hotfix #4 (KÖK NEDEN BUG — Pepito testinde yakalandı):
    Öncelik ESKİDEN stüdyo eşlemesi → energy_tier idi. Bu, sector detect_sector()
    tarafından yanlış/hiç eşleşmeyince (bkz. brand_brief.py — 7 sektörden hiçbiri
    "çocuk ürünü/oyuncak" içermiyor) rastgele/varsayılan bir studio_label'a
    (örn. "Wolff Olins") düşen markaları, o studio'nun SABİT template'ine
    (Wolff Olins → B, "dark statement" — salt wordmark + ince çubuk, RENK BLOĞU
    YOK) kilitliyordu — brief'in kendi energy_tier'ı "playful" olsa bile. Sonuç:
    Pepito (energy=playful, kırmızı/yeşil/krem palet) template B'ye düştü, "sadece
    yazı" göründü. Kanıt: jobs tablosunda studio_label="Wolff Olins",
    energy_tier="playful", ama render B (renk bloksuz) çıktı.

    Düzeltme (ilk hali): energy_tier'ı İLK öncelik yaptım — Pepito'yu (playful →
    yanlışlıkla B) düzeltti. AMA aynı gün 3 farklı brief'le (Rampa Skate/bold,
    Meridyen Galeri/kural-kıran, Hız Rotası/dinamik) test edince HEPSİ "cinematic"e
    düştüğünü gördüm — hiçbiri A/C/D'ye ulaşamadı. Kanıt: brand_brief_contract.py
    satır 128-129 Sonnet'in ham "energy" alanını zaten SADECE "playful" veya
    "cinematic"e indirgiyor (`"playful" if "playful" in energy_raw else "cinematic"`
    — 2 değerli bir kapı). 5-tier `_ENERGY_TIER_MAP` bu aynı 2 değerli alanı
    keyword'lerle tarıyor; Sonnet hiç "bold"/"luxury"/"minimal" yazmadığı için o üç
    tier PRATİKTE HİÇ TETİKLENMİYOR — energy_tier fiilen sadece "playful" ya da
    "cinematic" olabiliyor. "cinematic" olduğunda önce onu kontrol etmek, aslında
    zayıf/varsayılan bir sinyali 7 değerli (çok daha çeşitli) stüdyo eşlemesinin
    ÖNÜNE koyup A/C/D'yi neredeyse ulaşılamaz kılıyordu.

    Son düzeltme (bugünkü hâli): "playful" hâlâ güvenilir ve İLK sırada (Pepito
    kanıtı geçerli — yanlış template'e düşen gerçek bir bug'dı). Ama "cinematic"
    özel muamele görüyor: bu neredeyse her markanın ulaştığı bir DEFAULT olduğu
    için, tek başına stüdyo eşlemesinin üzerine çıkmasına izin verilmiyor —
    stüdyo etiketi (Collins/Bureau Borsche/Sagmeister&Walsh/Pentagram/Landor/
    Wolff Olins/Base Design → A/D/C/B/B/B/E) önce denenir, o da yoksa ancak o
    zaman "cinematic" → B'ye düşülür. Sonuç: playful markalar hâlâ doğru renk
    bloğuna gidiyor, geri kalan her şey stüdyo çeşitliliğinden (5 template) pay
    alıyor — hepsi B'de birikmiyor.
    (pil_params override'ı burada YOK — o sadece select_logo_primary_png'ye özel,
    tasarım direktörünün elle seçtiği bir override, mono/icon'a sızmıyor.)
    """
    energy = str(brief.get("energy_tier", brief.get("energy", "cinematic"))).lower()

    tpl = ""
    if energy and energy != "cinematic":
        # Güvenilir, ayrışan sinyal (bugün itibarıyla fiilen sadece "playful" bu
        # koşulu tetikliyor — bkz. yukarıdaki not). Gelecekte bold/luxury/minimal
        # gerçekten üretilmeye başlarsa onlar da buradan otomatik faydalanır.
        tpl = _ENERGY_TIER_TEMPLATE.get(energy, "")
    if not tpl:
        # 20 Tem 2026 v2: brief'in sektör/konsept/mood metninden stil sinyali —
        # kurumsal→I (VonArt koşullu), editoryal/lüks→G, retro/tech→F, craft→H.
        # Stüdyo map'inden ÖNCE denenir: sinyal marka-spesifik, stüdyo etiketi
        # ise detect_sector()'ün zayıf 7-sektör eşlemesinden geliyor.
        tpl = _style_signal(brief)
    if not tpl:
        tpl = _STUDIO_TEMPLATE_MAP.get(studio_label, "")
    if not tpl:
        # energy "cinematic" (varsayılan) VE studio_label eşleşmediyse — buraya
        # düşer, cinematic→B ile sonuçlanır.
        tpl = _ENERGY_TIER_TEMPLATE.get(energy, "")
    if not tpl:
        for kw, t in _ENERGY_TEMPLATE_MAP.items():
            if kw in energy:
                tpl = t
                break
    return tpl or "A"


def select_logo_primary_png(brief: dict, studio_label: str = "", pil_params: dict | None = None) -> str:
    """
    ANA logo: PIL composition + Bebas Neue.
    Seçim önceliği: pil_params["template"] → stüdyo map → energy_tier map → default A.

    pil_params: Tasarım direktörünün PIL_LOGO kararı (html_preview.py parse eder).
                {"template": "A"/"B"/"C"/"D"/"E"} — override yapar.

    PNG data URI döner (SVG yok, browser font yok).
    """
    name   = _brand_upper(brief)
    pc     = brief.get("primary_color", "#C9A25A")
    sc     = brief.get("secondary_color", "#8B8B7A")
    ac     = brief.get("accent_color") or sc
    bg     = brief.get("bg_color", "#0F0D0C")
    tag    = brief.get("tagline", "")

    # 1. Tasarım direktörü override (en yüksek öncelik) → 2-4. paylaşılan resolver
    tpl = (pil_params or {}).get("template", "") or _resolve_template(brief, studio_label)

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
        _draw_wordmark(d, name, tag, 88, bw - 100, 0, H, tc, tpl)

    elif tpl == "B":
        # Dark statement — Pentagram / Wolff Olins
        tc = "#F2EDE4" if _is_dark_hex(bg) else "#1A1A1A"
        _draw_wordmark(d, name, "", 88, W - 176, 0, H, pc, tpl)
        fs = _fit_font_size(name, _tpl_font_name(tpl), W - 176)
        f = _pil_font(_tpl_font_name(tpl), fs)
        bb = d.textbbox((0, 0), name, font=f)
        nh = bb[3] - bb[1]
        # NOT (3 Tem 2026 hotfix #3): bu hesap _draw_wordmark'ın İÇİNDEKİ çizimi
        # tekrar etmiyor, sadece bar'ı doğru yere koymak için aynı geometriyi
        # tekrar hesaplıyor — o yüzden _draw_wordmark'taki ink_top/ink_bottom
        # düzeltmesiyle BİREBİR aynı formülü kullanmak zorunda (yoksa bar, gerçek
        # çizilen metinle hizasız kalır). bb[1] burada kullanılmıyor çünkü ink_top
        # zaten mutlak bir hedef pozisyon — bb[1] sadece "name_y" (çizim orijini)
        # hesaplarken devreye girer, o hesap burada hiç yapılmıyor.
        ink_top = (H - nh) // 2 - int(H * 0.05)
        ink_bottom = ink_top + nh
        bar_gap = max(16, int(nh * 0.10))
        bar_y = ink_bottom + bar_gap
        bar_w = min(bb[2] - bb[0] + 8, W - 200)
        d.rectangle([88, bar_y, 88 + bar_w, bar_y + 10], fill=_pil_rgb(ac))
        if tag:
            tf = _pil_font("body", 28)
            tw_bb = d.textbbox((0, 0), _tr_upper(tag)[:42], font=tf)
            tw = tw_bb[2] - tw_bb[0]
            d.text((W - 88 - tw, bar_y + 10 + max(18, int(nh * 0.08))), _tr_upper(tag)[:42], font=tf, fill=_pil_rgb(sc))

    elif tpl == "C":
        # Oversized initial — Sagmeister & Walsh
        first = name[0] if name else "?"
        rest = name[1:]
        big_fs = min(490, H + 60)
        bf = _pil_font(_tpl_font_name(tpl), big_fs)
        d.text((20, -int(H * 0.09)), first, font=bf, fill=_pil_rgb(pc))
        if rest:
            bb1 = d.textbbox((20, -int(H * 0.09)), first, font=bf)
            rx = max(bb1[2] - 15, int(W * 0.30))
            rest_fs = _fit_font_size(rest, _tpl_font_name(tpl), W - rx - 60)
            rf = _pil_font(_tpl_font_name(tpl), rest_fs)
            rbb = d.textbbox((0, 0), rest, font=rf)
            rh = rbb[3] - rbb[1]
            ry = (H - rh) // 2 - int(H * 0.05)
            # NOT (3 Tem 2026 hotfix #7): "rest" metni körü körüne secondary_color
            # ile çiziliyordu — bg de koyu, secondary_color de koyu olduğunda
            # (örn. Meridyen Galeri: sc=#1A0A2E, bg=#0E0618) metin neredeyse görünmez
            # oluyordu. sc, bg ile kontrast oluşturmuyorsa güvenli bir nötr renge düş.
            rest_color = sc if _is_dark_hex(bg) != _is_dark_hex(sc) else (
                "#F2EDE4" if _is_dark_hex(bg) else "#1A1A1A"
            )
            d.text((rx, ry), rest, font=rf, fill=_pil_rgb(rest_color))

    elif tpl == "D":
        # Diagonal field — Bureau Borsche
        px = int(W * 0.64)
        d.polygon([(0, 0), (px, 0), (int(W * 0.46), H), (0, H)], fill=_pil_rgb(pc))
        acc_pts = [(px, 0), (px + int(W * 0.05), 0),
                   (int(W * 0.46) + int(W * 0.05), H), (int(W * 0.46), H)]
        d.polygon(acc_pts, fill=_pil_rgb(ac))
        tc = "#FFFFFF" if _is_dark_hex(pc) else "#0D0D0D"
        _draw_wordmark(d, name, tag, 88, px - 100, 0, H, tc, tpl)

    elif tpl == "E":
        # Offset block — Base Design
        bx, by = 64, int(H * 0.13)
        bw2 = int(W * 0.82)
        bh = int(H * 0.62)
        d.rectangle([bx, by, bx + bw2, by + bh], fill=_pil_rgb(pc))
        tc = "#FFFFFF" if _is_dark_hex(pc) else "#0D0D0D"
        _draw_wordmark(d, name, tag, bx + 48, bw2 - 100, by, bh, tc, tpl)

    # ── TEMPLATE v2 (20 Tem 2026, Görev 2A): F-J art-directed lockup'lar ─────
    # No.1 kuralı her blokta: tek güçlü element, boşluk aktif, max 2 renk + aksan.

    elif tpl == "F":
        # F: RETRO-FÜTÜRİST ECHO — Archivo Black, kayan renk kopyaları + ufuk çizgileri.
        # Trend: retro-fütürizm. Tek güçlü element: echo'lu wordmark.
        fname = _tpl_font_name(tpl)
        k = _TPL_TRACKING["F"]
        tc = "#F2EDE4" if _is_dark_hex(bg) else "#1A1A1A"
        fs = _fit_tracked(name, fname, W - 320, k)
        f = _pil_font(fname, fs)
        tr = int(k * fs)
        tw = int(_tracked_width(name, f, tr))
        bb = d.textbbox((0, 0), name, font=f)
        nh = bb[3] - bb[1]
        ink_top = (H - nh) // 2 - int(H * 0.08)
        y = ink_top - bb[1]
        x = (W - tw) // 2
        for off, col in ((int(fs * 0.055) + 8, ac), (int(fs * 0.03) + 4, sc)):
            _draw_tracked(d, name, f, x + off, y + off, _pil_rgb(_cguard(col, bg)), tr)
        _draw_tracked(d, name, f, x, y, _pil_rgb(tc), tr)
        line_y = ink_top + nh + int(H * 0.09)
        acr = _pil_rgb(_cguard(ac, bg))
        for i, lh in enumerate((6, 4, 2, 1)):
            ly = line_y + i * int(H * 0.045)
            if ly + lh < H - 36:
                d.rectangle([x, ly, x + tw, ly + lh], fill=acr)
        if tag:
            ts = max(22, fs // 6)
            tf = _pil_font("body", ts)
            tg = _tr_upper(tag)[:42]
            ttr = int(0.30 * ts)
            tag_w = _tracked_width(tg, tf, ttr)
            _draw_tracked(d, tg, tf, (W - tag_w) // 2, 34,
                          _pil_rgb(_cguard(sc, bg)), ttr)
        _qa_flags(tpl, fs, name)

    elif tpl == "G":
        # G: EDITORIAL MASTHEAD — Bodoni Moda, çift editoryal çizgi, tracked serif.
        # Lüks/editoryal sinyali. Tek güçlü element: masthead dizgisi.
        fname = _tpl_font_name(tpl)
        k = _TPL_TRACKING["G"]
        fs = _fit_tracked(name, fname, W - 360, k)
        f = _pil_font(fname, fs)
        tr = int(k * fs)
        tw = int(_tracked_width(name, f, tr))
        bb = d.textbbox((0, 0), name, font=f)
        nh = bb[3] - bb[1]
        ink_top = (H - nh) // 2 - int(H * 0.02)
        y = ink_top - bb[1]
        x = (W - tw) // 2
        _draw_tracked(d, name, f, x, y, _pil_rgb(_cguard(pc, bg)), tr)
        rule_w = min(int(tw * 1.16), W - 220)
        rx = (W - rule_w) // 2
        top_y = ink_top - int(H * 0.13)
        bot_y = ink_top + nh + int(H * 0.11)
        acr = _pil_rgb(_cguard(ac, bg))
        d.rectangle([rx, top_y, rx + rule_w, top_y + 3], fill=acr)
        d.rectangle([rx, top_y + 8, rx + rule_w, top_y + 9], fill=acr)
        d.rectangle([rx, bot_y, rx + rule_w, bot_y + 1], fill=acr)
        d.rectangle([rx, bot_y + 6, rx + rule_w, bot_y + 9], fill=acr)
        cxm = W // 2
        dr = max(5, int(fs * 0.045))
        dy = top_y - int(H * 0.05)
        d.polygon([(cxm, dy - dr), (cxm + dr, dy), (cxm, dy + dr), (cxm - dr, dy)], fill=acr)
        if tag:
            ts = max(22, fs // 7)
            tf = _pil_font("body", ts)
            tg = _tr_upper(tag)[:42]
            ttr = int(0.32 * ts)
            tag_w = _tracked_width(tg, tf, ttr)
            _draw_tracked(d, tg, tf, (W - tag_w) // 2, bot_y + 9 + int(H * 0.05),
                          _pil_rgb(_cguard(sc, bg)), ttr)
        _qa_flags(tpl, fs, name)

    elif tpl == "H":
        # H: LINEWORK BADGE — ince çizgi rozet, geniş tracking, köşe tikleri.
        # Craft/artisanal sinyali. Badge lockup.
        fname = _tpl_font_name(tpl)
        k = _TPL_TRACKING["H"]
        tc = "#F2EDE4" if _is_dark_hex(bg) else "#1A1A1A"
        bx0, by0 = int(W * 0.14), int(H * 0.14)
        bx1, by1 = W - bx0, H - by0
        line_c = _pil_rgb(_cguard(pc, bg))
        acr = _pil_rgb(_cguard(ac, bg))
        try:
            d.rounded_rectangle([bx0, by0, bx1, by1], radius=int(H * 0.06),
                                outline=line_c, width=3)
            d.rounded_rectangle([bx0 + 12, by0 + 12, bx1 - 12, by1 - 12],
                                radius=int(H * 0.045), outline=acr, width=1)
        except AttributeError:
            d.rectangle([bx0, by0, bx1, by1], outline=line_c, width=3)
            d.rectangle([bx0 + 12, by0 + 12, bx1 - 12, by1 - 12], outline=acr, width=1)
        avail = (bx1 - bx0) - 160
        fs = _fit_tracked(name, fname, avail, k, max_s=150)
        f = _pil_font(fname, fs)
        tr = int(k * fs)
        tw = int(_tracked_width(name, f, tr))
        bb = d.textbbox((0, 0), name, font=f)
        nh = bb[3] - bb[1]
        ink_top = (H - nh) // 2 - (int(H * 0.05) if tag else 0)
        y = ink_top - bb[1]
        x = (W - tw) // 2
        _draw_tracked(d, name, f, x, y, _pil_rgb(tc), tr)
        tick = int(H * 0.035)
        for cx0, cy0, sx, sy in ((bx0 + 26, by0 + 26, 1, 1), (bx1 - 26, by0 + 26, -1, 1),
                                 (bx0 + 26, by1 - 26, 1, -1), (bx1 - 26, by1 - 26, -1, -1)):
            d.line([(cx0, cy0), (cx0 + sx * tick, cy0)], fill=acr, width=3)
            d.line([(cx0, cy0), (cx0, cy0 + sy * tick)], fill=acr, width=3)
        if tag:
            ts = max(20, fs // 6)
            tf = _pil_font("body", ts)
            tg = _tr_upper(tag)[:42]
            ttr = int(0.30 * ts)
            tag_w = _tracked_width(tg, tf, ttr)
            _draw_tracked(d, tg, tf, (W - tag_w) // 2, ink_top + nh + int(fs * 0.24),
                          _pil_rgb(_cguard(sc, bg)), ttr)
        _qa_flags(tpl, fs, name)

    elif tpl == "I":
        # I: CLASSIC CORPORATE — VonArt koşullu lockup (SADECE kurumsal sinyalde
        # seçilir, bkz. _style_signal). Sol wordmark + dikey ayraç + sağ tagline.
        fname = _tpl_font_name(tpl)
        k = _TPL_TRACKING["I"]
        avail = int(W * 0.52) if tag else (W - 320)
        fs = _fit_tracked(name, fname, avail, k, max_s=170)
        f = _pil_font(fname, fs)
        tr = int(k * fs)
        tw = int(_tracked_width(name, f, tr))
        bb = d.textbbox((0, 0), name, font=f)
        nh = bb[3] - bb[1]
        ink_top = (H - nh) // 2
        y = ink_top - bb[1]
        x = 120 if tag else (W - tw) // 2
        _draw_tracked(d, name, f, x, y, _pil_rgb(_cguard(pc, bg)), tr)
        if tag:
            div_x = x + tw + 64
            d.rectangle([div_x, int(H * 0.30), div_x + 2, int(H * 0.70)],
                        fill=_pil_rgb(_cguard(ac, bg)))
            ts = max(22, fs // 5)
            tg = _tr_upper(tag)[:42]
            allowed = W - 100 - (div_x + 40)
            while ts > 18:
                tf = _pil_font("body", ts)
                ttr = int(0.14 * ts)
                if _tracked_width(tg, tf, ttr) <= allowed:
                    break
                ts -= 2
            tf = _pil_font("body", ts)
            ttr = int(0.14 * ts)
            tbb = d.textbbox((0, 0), tg, font=tf)
            th = tbb[3] - tbb[1]
            ty = (H - th) // 2 - tbb[1]
            _draw_tracked(d, tg, tf, div_x + 40, ty, _pil_rgb(_cguard(sc, bg)), ttr)
        else:
            uy = ink_top + nh + int(H * 0.07)
            d.rectangle([x, uy, x + tw, uy + 3], fill=_pil_rgb(_cguard(ac, bg)))
        _qa_flags(tpl, fs, name)

    elif tpl == "J":
        # J: PLAYFUL STACK — Fredoka. Çok kelime: staircase stack; tek kelime:
        # dönüşümlü renk + baseline zıplaması. Playful energy'nin yeni evi (eski E).
        fname = _tpl_font_name(tpl)
        tc = "#F2EDE4" if _is_dark_hex(bg) else "#1A1A1A"
        words = [w for w in name.split() if w]
        if len(words) >= 2:
            l1, l2 = words[0], " ".join(words[1:])
            fs = min(_fit_font_size(l1, fname, W - 460),
                     _fit_font_size(l2, fname, W - 460), int(H * 0.38))
            f = _pil_font(fname, fs)
            bb1 = d.textbbox((0, 0), l1, font=f)
            nh1 = bb1[3] - bb1[1]
            bb2 = d.textbbox((0, 0), l2, font=f)
            nh2 = bb2[3] - bb2[1]
            gap = int(fs * 0.16)
            top = (H - (nh1 + gap + nh2)) // 2 - (int(H * 0.05) if tag else 0)
            x1 = 140
            x2 = 140 + int(fs * 0.55)
            d.text((x1, top - bb1[1]), l1, font=f, fill=_pil_rgb(_cguard(pc, bg)))
            d.text((x2, top + nh1 + gap - bb2[1]), l2, font=f, fill=_pil_rgb(tc))
            ascent, _desc = f.getmetrics()
            dot_r = max(6, int(fs * 0.09))
            dot_cx = x2 + int(f.getlength(l2)) + int(fs * 0.18)
            dot_cy = top + nh1 + gap - bb2[1] + ascent - dot_r
            d.ellipse([dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r],
                      fill=_pil_rgb(_cguard(ac, bg)))
            tag_x, tag_y = x1, top + nh1 + gap + nh2 + int(fs * 0.22)
        else:
            fs = _fit_font_size(name, fname, W - 360)
            f = _pil_font(fname, fs)
            bb = d.textbbox((0, 0), name, font=f)
            nh = bb[3] - bb[1]
            ink_top = (H - nh) // 2
            y = ink_top - bb[1]
            x = int((W - f.getlength(name)) // 2)
            cols = [_pil_rgb(tc), _pil_rgb(_cguard(pc, bg)), _pil_rgb(_cguard(ac, bg))]
            cx = float(x)
            for i, ch in enumerate(name):
                bounce = int(fs * 0.04) * (-1 if i % 2 else 1)
                d.text((cx, y + bounce), ch, font=f, fill=cols[i % 3])
                cx += f.getlength(ch)
            tag_x, tag_y = x, ink_top + nh + int(fs * 0.24)
        if tag:
            ts = max(22, fs // 6)
            tf = _pil_font("body", ts)
            d.text((tag_x, tag_y), _tr_upper(tag)[:42], font=tf,
                   fill=_pil_rgb(_cguard(sc, bg)))
        _qa_flags(tpl, fs, name)

    return _png_uri(img)


# ── MONO LOGO ─────────────────────────────────────────────────────────────────

def select_logo_mono_png(brief: dict, studio_label: str = "") -> str:
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

    3 Tem 2026 fix (P1 kapandı — font artık markaya özgü):
    - Önceden font sabit/hardcoded'dı (Bebas Neue → sonra kırık URL → sessiz sistem
      fontu fallback'i). Artık ANA logo ile AYNI `_resolve_template()` kararını
      kullanıyor (studio_label parametresi bunun için eklendi) — MONO/TİPO, ANA'yla
      aynı tpl_X.ttf fontunu kullanır. Aynı markanın iki logo varyantı farklı
      fontlarla çıkmasın diye şart: çağıran kod (html_preview.py, pipeline.py)
      select_logo_primary_png'ye verdiği AYNI studio_label'ı buraya da vermeli.
    """
    name = _brand_upper(brief)
    bg   = brief.get("bg_color", "#0F0D0C")
    tc   = "#F2EDE4" if _is_dark_hex(bg) else "#1A1A1A"
    tag  = brief.get("tagline", "")
    tpl  = _resolve_template(brief, studio_label)

    W, H = 1600, 420
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))   # gerçek şeffaflık
    d   = ImageDraw.Draw(img)
    tc_rgba = _pil_rgb(tc) + (255,)

    fs = _fit_font_size(name, _tpl_font_name(tpl), W - 100)
    f  = _pil_font(_tpl_font_name(tpl), fs)
    bb = d.textbbox((0, 0), name, font=f)
    nh = bb[3] - bb[1]
    ink_top = (H - nh) // 2
    name_y = ink_top - bb[1]                # top bearing düşüldü — artık gerçekten ortalı
    d.text((50, name_y), name, font=f, fill=tc_rgba)

    if tag:
        ts = max(24, fs // 5)
        tf = _pil_font("body", ts)
        # NOT (3 Tem 2026 hotfix #3): eskiden "name_y + nh" kullanılıyordu — name_y
        # zaten -bb[1] içerdiği için bu, tagline'ı bb[1] kadar (Bodoni Moda'da 81px)
        # gerçek ink_bottom'ın ÜSTÜNE çekiyordu, büyük bb[1]'li fontlarda üst üste
        # binme riski yaratıyordu. Doğrusu ink_top + nh (= ink_bottom).
        gap = max(20, int(fs * 0.20))
        ink_bottom = ink_top + nh
        d.text((50, ink_bottom + gap), _tr_upper(tag)[:42], font=tf, fill=tc_rgba)

    return _png_uri(img)


# ── TİPO LOGO ─────────────────────────────────────────────────────────────────
# 3 Tem 2026 eklendi. TİPO, MONO'nun kopyası DEĞİL — html_preview.py'de
# `svgs["logo_tipo"] = svgs["logo_mono"]` bug'ı burada düzeltiliyor (bkz.
# html_preview.py ve pipeline.py'deki ilgili değişiklikler). Bu fonksiyon A/B/C/D/E
# layout sistemine (select_logo_primary_png) GİRMEZ — ayrı, tek bir kompozisyon:
# bg_color dolu zemin + ortalanmış letter-spaced wordmark + accent nokta + tracked
# tagline. Font kararı yine _resolve_template()'ten gelir — marka tutarlılığı korunur.

_TIPO_TRACKING = {
    "playful":   0.03,
    "cinematic": 0.08,
    "luxury":    0.14,
    "minimal":   0.14,
    "premium":   0.14,
}


def _tracked_width(text: str, font: "ImageFont.FreeTypeFont", tracking: int) -> float:
    """Harf harf ölçülen genişlik + harfler arası tracking boşluğu (son harften sonra yok)."""
    return sum(font.getlength(ch) for ch in text) + tracking * max(0, len(text) - 1)


def _draw_tracked(d: "ImageDraw.ImageDraw", text: str, font: "ImageFont.FreeTypeFont",
                   x: float, y: float, fill, tracking: int) -> float:
    """Harf harf, tracking px aralıkla çizer. Son harfin sağ kenarının x'ini döner
    (accent nokta / sonraki eleman konumlandırması için)."""
    cx = x
    for ch in text:
        d.text((cx, y), ch, font=font, fill=fill)
        cx += font.getlength(ch) + tracking
    return cx - tracking


def select_logo_tipo_png(brief: dict, studio_label: str = "") -> str:
    """
    TİPO logo: markaya özgü tipografik kimlik — marka renkleriyle, bg_color
    dolu zemin üstünde, geometrik blok/şekil OLMADAN.

    MONO'dan farkı (yapısal, garanti — bkz. test_logo_tipo.py):
      - RGB dolu zemin (bg_color)  ← mono RGBA gerçek şeffaf
      - primary_color wordmark     ← mono nötr (#F2EDE4/#1A1A1A)
      - ortalı + letter-spacing    ← mono sola yaslı, tracking yok
      - accent nokta devicesi      ← mono'da yok
    PRIMARY'den farkı: renk bloğu/polygon/bar yok — salt tipografi + tracking.

    Font: _resolve_template() → tpl_X.ttf (ANA/MONO ile aynı — marka tutarlılığı,
    3 Tem 2026 font-per-marka kuralı).

    PNG data URI döner. Deterministik — diffusion yok, Türkçe karakter riski yok.
    """
    name   = _brand_upper(brief)
    pc     = brief.get("primary_color", "#C9A25A")
    sc     = brief.get("secondary_color", "#8B8B7A")
    ac     = brief.get("accent_color") or sc
    bg     = brief.get("bg_color", "#0F0D0C")
    tag    = brief.get("tagline", "")
    tpl    = _resolve_template(brief, studio_label)

    energy = str(brief.get("energy_tier", brief.get("energy", "cinematic"))).lower()
    k = _TIPO_TRACKING.get(energy, _TIPO_TRACKING["cinematic"])

    # Kontrast guard — pc bg ile aynı koyu/açık kategorideyse nötre düş
    # (Meridyen Galeri dersi, hotfix #7 ile aynı pattern — bkz. select_logo_primary_png tpl C).
    wm_color = pc if _is_dark_hex(pc) != _is_dark_hex(bg) else (
        "#F2EDE4" if _is_dark_hex(bg) else "#1A1A1A"
    )
    tag_color = sc if _is_dark_hex(sc) != _is_dark_hex(bg) else (
        "#F2EDE4" if _is_dark_hex(bg) else "#1A1A1A"
    )

    W, H = 1600, 520
    img = Image.new("RGB", (W, H), _pil_rgb(bg))
    d = ImageDraw.Draw(img)

    avail_w = W - 160  # kenar payı

    # fs sığdırma — _fit_font_size tracking bilmiyor, kapalı formülle orantılı çözülüyor
    ref = 200
    f_ref = _pil_font(_tpl_font_name(tpl), ref)
    w_ref = sum(f_ref.getlength(ch) for ch in name)
    per_fs = w_ref / ref + k * max(0, len(name) - 1)
    fs = int((avail_w * 0.96) / per_fs) if per_fs > 0 else 120
    fs = max(28, min(200, fs))
    if fs <= 28:
        # Uzun marka adı guard'ı — tracking'i sıfırla, yeniden hesapla (taşmasın)
        k = 0
        per_fs = w_ref / ref
        fs = int((avail_w * 0.96) / per_fs) if per_fs > 0 else 120
        fs = max(28, min(200, fs))

    f = _pil_font(_tpl_font_name(tpl), fs)
    tracking = int(k * fs)

    total_w = _tracked_width(name, f, tracking)
    dot_r = max(2, int(fs * 0.14) // 2)
    dot_gap = int(0.35 * tracking + fs * 0.08)
    total_w_with_dot = total_w + dot_gap + dot_r

    bb = d.textbbox((0, 0), name, font=f)
    nh = bb[3] - bb[1]
    # hotfix #3 pattern: ink_top hedef, origin (y) = ink_top - bb[1]
    ink_top = (H - nh) // 2 - int(H * 0.04)
    y = ink_top - bb[1]
    x = (W - total_w_with_dot) // 2

    last_x = _draw_tracked(d, name, f, x, y, _pil_rgb(wm_color), tracking)

    # Accent nokta — gerçek font baseline'ında (ascent üzerinden hesaplanır)
    ascent, _descent = f.getmetrics()
    baseline_y = y + ascent
    dot_cx = last_x + dot_gap
    d.ellipse(
        [dot_cx - dot_r, baseline_y - dot_r, dot_cx + dot_r, baseline_y + dot_r],
        fill=_pil_rgb(ac),
    )

    if tag:
        ts = max(22, fs // 6)
        tf = _pil_font("body", ts)
        tag_text = _tr_upper(tag)[:42]
        tag_tracking = int(0.30 * ts)
        tag_w = _tracked_width(tag_text, tf, tag_tracking)
        tag_x = (W - tag_w) // 2
        ink_bottom = ink_top + nh
        tag_y = ink_bottom + int(fs * 0.22)
        _draw_tracked(d, tag_text, tf, tag_x, tag_y, _pil_rgb(tag_color), tag_tracking)

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

    # Font: ikonun kendi şekil-key'i (A-D, negative/diagonal/split/frame) ile
    # KARIŞTIRILMASIN — bu ayrı bir karar uzayı. Font, ANA logoyla aynı markaya
    # özgü tpl_X.ttf olsun diye AYNI _resolve_template() çağrılıyor (3 Tem 2026).
    font_tpl = _resolve_template(brief, studio_label)

    fn = _LETTER_ICON_FNS.get(key, _pil_icon_negative)
    return _png_uri(fn(first, pc, bg, ac, tpl=font_tpl))
