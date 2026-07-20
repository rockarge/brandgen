"""
asset_generator.py — Genişletilmiş marka asset'leri v2 (Görev 2B, 20 Tem 2026)

╔══════════════════════════════════════════════════════════════════════════════╗
║  DEMİR KURAL ("Preview ≠ İndirilen" bug ailesi — bkz. brandgen.md):          ║
║  Bu modül, genişletilmiş asset'lerin TEK üretim kaynağıdır.                  ║
║  html_preview.py (kit sayfası) ve pipeline.finalize_job (ödenen ZIP)         ║
║  İKİSİ DE generate_extended_pil_assets()'i çağırır.                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v2 (aynı gün revizyon — Serhat kritiği): v1 "tüm markalara aynı kompozisyon ║
║  farklı renk" üretiyordu → swap testi FAIL (stil-referans §5). v2'de her     ║
║  asset, markanın ANA logosunun template DNA'sını (A-J) miras alır:           ║
║  A block / B statement / C oversize / D diagonal / E offset / F echo /       ║
║  G editorial / H badge / I corporate / J playful. Kartvizit, banner,         ║
║  highlight ve profil KOMPOZİSYONU template'e göre değişir — iki farklı       ║
║  markanın asset'i yer değiştirilemez olmalı.                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

Üretilenler (hepsi PIL — $0, deterministik, Türkçe karakter riski yok):
  card_front / card_back       — kartvizit 1050×600 (3.5"×2" @300dpi)
  profile_dark / profile_light — profil fotoğrafı 1080×1080
  highlight_1..4               — IG highlight kapağı 1080×1080 (circle-safe)
  banner_linkedin (1584×396) / banner_twitter (1500×500)
  logo_reversed                — mono'nun polarite-ters hali

Mobil hero (foto-gerçekçi) BURADA DEĞİL — image_generator.generate_all_images
hero_dark/hero_light üretir (tüm fal çağrıları tek gather'da).
"""
# Python 3.9 uyumu (Mac'te lokal QA koşabilsin): 3.10+ tip
# annotation'larini (dict | None) string'e cevirir, runtime degismez.
from __future__ import annotations


import io
import base64
from PIL import Image, ImageDraw

from .logo_generator import (
    _resolve_template,
    _brand_upper,          # dil bilincli marka adi buyutme (20 Tem 2026)
    _tpl_font_name,
    _pil_font,
    _pil_rgb,
    _png_uri,
    _cguard,
    _is_dark_hex,
    _fit_font_size,
    _fit_tracked,
    _tracked_width,
    _draw_tracked,
    _TPL_TRACKING,
)

# Fallback highlight etiketleri — brief'te highlight_labels yoksa (Sonnet artık
# markaya özgü 4 etiket üretiyor, bkz. brand_brief.py şeması; bu sadece emniyet)
_DEFAULT_HIGHLIGHTS = ["HİKAYE", "İŞLER", "EKİP", "İLETİŞİM"]

_LIGHT_NEUTRAL = "#F2EDE4"
_DARK_NEUTRAL = "#1A1A1A"

# Template → kompozisyon ekseni (ANA logo lockup'ının DNA'sı — logo_generator
# select_logo_primary_png ile birebir aynı eksen adları/ruhu)
_COMP = {
    "A": "block", "B": "statement", "C": "oversize", "D": "diagonal",
    "E": "offset", "F": "echo", "G": "editorial", "H": "badge",
    "I": "corporate", "J": "playful",
}


def _neutral(bg_hex: str) -> str:
    return _LIGHT_NEUTRAL if _is_dark_hex(bg_hex) else _DARK_NEUTRAL


def _tr_upper(s: str) -> str:
    """Türkçe-doğru büyük harf: i→İ (Python .upper() i→I yapar — QA v2'de
    'Ateşin'→'ATEŞIN', 'Meridyen'→'MERIDYEN' hatası yakalandı). ı→I zaten doğru."""
    return (s or "").replace("i", "İ").upper()


def _datauri_to_rgba(uri: str) -> "Image.Image | None":
    if not uri or "," not in uri:
        return None
    try:
        raw = base64.b64decode(uri.split(",", 1)[1])
        img = Image.open(io.BytesIO(raw))
        img.load()
        return img.convert("RGBA")
    except Exception as e:
        print(f"[asset_generator] data URI decode hatası: {e}")
        return None


def _mix(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _tpl_ctx(brief: dict, studio_label: str) -> dict:
    """Ortak bağlam — tüm asset'ler ANA logoyla AYNI template kararından beslenir."""
    tpl = "A"
    try:
        tpl = _resolve_template(brief, studio_label)
    except Exception as e:
        print(f"[asset_generator] template kararı alınamadı, A'ya düşüldü: {e}")
    return {
        "tpl": tpl,
        "comp": _COMP.get(tpl, "block"),
        "font": _tpl_font_name(tpl),
        "track": _TPL_TRACKING.get(tpl, 0.0),
        "name": _brand_upper(brief),   # 20 Tem: dil bilincli buyutme — tum
        # asset'ler (kartvizit/banner/profil) bu tek kaynaktan besleniyor,
        # sonraki _tr_upper cagrilari zaten-buyuk metne dokunmaz.
        "tagline": brief.get("tagline", ""),
        "primary": brief.get("primary_color", "#C9A25A"),
        "secondary": brief.get("secondary_color", "#8B8B7A"),
        "accent": brief.get("accent_color") or brief.get("secondary_color", "#8B8B7A"),
        "bg": brief.get("bg_color", "#0F0D0C"),
    }


# ── Çizim primitifleri (motifler — logo template'lerinin dilinden) ────────────

def _tracked_line(d, text, fname, fs, k, fill, cx=None, x=None, y_ink=0):
    """Tracked metin çiz (ink-top düzeltmeli). cx verilirse o merkeze, x verilirse
    sola hizalar. Döner (x, tw, nh)."""
    f = _pil_font(fname, fs)
    tr = int(k * fs)
    tw = int(_tracked_width(text, f, tr))
    tmp_bb = d.textbbox((0, 0), text, font=f)
    nh = tmp_bb[3] - tmp_bb[1]
    if x is None:
        x = int(cx - tw / 2)
    _draw_tracked(d, text, f, x, y_ink - tmp_bb[1], fill, tr)
    return x, tw, nh


def _echo_text(d, text, fname, fs, k, x, y_ink, base_rgb, ac_rgb, sc_rgb):
    """F dili: kayan renk kopyaları + ana metin. Döner (tw, nh)."""
    f = _pil_font(fname, fs)
    tr = int(k * fs)
    tw = int(_tracked_width(text, f, tr))
    bb = d.textbbox((0, 0), text, font=f)
    nh = bb[3] - bb[1]
    y = y_ink - bb[1]
    for off, col in ((int(fs * 0.055) + 6, ac_rgb), (int(fs * 0.03) + 3, sc_rgb)):
        _draw_tracked(d, text, f, x + off, y + off, col, tr)
    _draw_tracked(d, text, f, x, y, base_rgb, tr)
    return tw, nh


def _horizon_lines(d, x, w, y0, step, ac_rgb, limit_y):
    """F dili: incelen ufuk çizgileri."""
    for i, lh in enumerate((6, 4, 2, 1)):
        ly = y0 + i * step
        if ly + lh < limit_y:
            d.rectangle([x, ly, x + w, ly + lh], fill=ac_rgb)


def _editorial_rules(d, cx, w, top_y, bot_y, ac_rgb, diamond=True, dr=8):
    """G dili: çift editoryal çizgi + elmas."""
    rx = int(cx - w / 2)
    d.rectangle([rx, top_y, rx + w, top_y + 3], fill=ac_rgb)
    d.rectangle([rx, top_y + 8, rx + w, top_y + 9], fill=ac_rgb)
    d.rectangle([rx, bot_y, rx + w, bot_y + 1], fill=ac_rgb)
    d.rectangle([rx, bot_y + 6, rx + w, bot_y + 9], fill=ac_rgb)
    if diamond:
        dy = top_y - int(dr * 2.2)
        d.polygon([(cx, dy - dr), (cx + dr, dy), (cx, dy + dr), (cx - dr, dy)], fill=ac_rgb)


def _badge_ticks(d, box, ac_rgb, tick, width=3):
    """H dili: köşe tikleri."""
    x0, y0, x1, y1 = box
    for cx0, cy0, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(cx0, cy0), (cx0 + sx * tick, cy0)], fill=ac_rgb, width=width)
        d.line([(cx0, cy0), (cx0, cy0 + sy * tick)], fill=ac_rgb, width=width)


def _bounce_text(d, text, fname, fs, x, y_ink, cols):
    """J dili: harf harf renk dönüşümü + baseline zıplaması. Döner (tw, nh)."""
    f = _pil_font(fname, fs)
    bb = d.textbbox((0, 0), text, font=f)
    nh = bb[3] - bb[1]
    y = y_ink - bb[1]
    cx = float(x)
    for i, ch in enumerate(text):
        bounce = int(fs * 0.045) * (-1 if i % 2 else 1)
        d.text((cx, y + bounce), ch, font=f, fill=cols[i % len(cols)])
        cx += f.getlength(ch)
    return int(cx - x), nh


# ═════════════════════════════════════════════════════════════════════════════
#  PROFİL FOTOĞRAFI — 1080×1080, dark + light. Template DNA'lı monogram sahnesi
#  (v1'in "dairede baş harf" avatar klişesi terk edildi — her comp kendi dilinde)
# ═════════════════════════════════════════════════════════════════════════════

def _profile(brief: dict, studio_label: str, dark: bool) -> Image.Image:
    c = _tpl_ctx(brief, studio_label)
    S = 1080
    bg_hex = c["bg"] if dark else _LIGHT_NEUTRAL
    if dark and not _is_dark_hex(bg_hex):
        bg_hex = _DARK_NEUTRAL
    bg = _pil_rgb(bg_hex)
    pc = _pil_rgb(_cguard(c["primary"], bg_hex))
    ac = _pil_rgb(_cguard(c["accent"], bg_hex))
    sc = _pil_rgb(_cguard(c["secondary"], bg_hex))
    tc = _pil_rgb(_neutral(bg_hex))
    initial = _tr_upper((c["name"] or "B")[0])
    comp, fname = c["comp"], c["font"]

    img = Image.new("RGB", (S, S), bg)
    d = ImageDraw.Draw(img)

    if comp == "block":
        # A: dev renk bloğu + aksan şeridi, harf bloktan oyulmuş
        bx0, by0, bx1, by1 = int(S*0.12), int(S*0.12), int(S*0.82), int(S*0.88)
        d.rectangle([bx0, by0, bx1, by1], fill=pc)
        d.rectangle([bx1, by0, bx1 + int(S*0.05), by1], fill=ac)
        f = _pil_font(fname, int(S*0.52))
        bb = d.textbbox((0, 0), initial, font=f)
        d.text((( (bx0+bx1) - (bb[2]-bb[0]) )//2 - bb[0], (S-(bb[3]-bb[1]))//2 - bb[1]),
               initial, font=f, fill=bg)
    elif comp == "diagonal":
        # D: diyagonal alan + aksan şerit
        d.polygon([(0, 0), (int(S*0.78), 0), (int(S*0.50), S), (0, S)], fill=pc)
        d.polygon([(int(S*0.78), 0), (int(S*0.86), 0), (int(S*0.58), S), (int(S*0.50), S)], fill=ac)
        f = _pil_font(fname, int(S*0.5))
        fill = _pil_rgb("#FFFFFF" if _is_dark_hex(c["primary"]) else "#0D0D0D")
        bb = d.textbbox((0, 0), initial, font=f)
        d.text((int(S*0.14), (S-(bb[3]-bb[1]))//2 - bb[1]), initial, font=f, fill=fill)
    elif comp == "oversize":
        # C: %130 kesilen dev harf — kadrajı taşırır (crop bilinçli karar)
        f = _pil_font(fname, int(S*1.25))
        bb = d.textbbox((0, 0), initial, font=f)
        d.text((-int((bb[2]-bb[0])*0.12) - bb[0], -int((bb[3]-bb[1])*0.18) - bb[1]),
               initial, font=f, fill=pc)
        f2 = _pil_font(fname, int(S*0.30))
        bb2 = d.textbbox((0, 0), initial, font=f2)
        d.text((S - (bb2[2]-bb2[0]) - int(S*0.09) - bb2[0], S - (bb2[3]-bb2[1]) - int(S*0.09) - bb2[1]),
               initial, font=f2, fill=ac)
    elif comp == "offset":
        # E: offset blok üstünde harf
        bx, by = int(S*0.16), int(S*0.20)
        bw, bh = int(S*0.62), int(S*0.52)
        d.rectangle([bx+18, by+18, bx+bw+18, by+bh+18], outline=ac, width=3)
        d.rectangle([bx, by, bx+bw, by+bh], fill=pc)
        f = _pil_font(fname, int(bh*0.62))
        fill = _pil_rgb("#FFFFFF" if _is_dark_hex(c["primary"]) else "#0D0D0D")
        bb = d.textbbox((0, 0), initial, font=f)
        d.text((bx + (bw-(bb[2]-bb[0]))//2 - bb[0], by + (bh-(bb[3]-bb[1]))//2 - bb[1]),
               initial, font=f, fill=fill)
    elif comp == "echo":
        # F: echo kopyalı harf + ufuk çizgileri
        f = _pil_font(fname, int(S*0.56))
        bb = d.textbbox((0, 0), initial, font=f)
        x = (S-(bb[2]-bb[0]))//2 - bb[0]
        y_ink = (S-(bb[3]-bb[1]))//2 - int(S*0.06)
        for off, col in ((int(S*0.035), ac), (int(S*0.018), sc)):
            d.text((x+off, y_ink - bb[1] + off), initial, font=f, fill=col)
        d.text((x, y_ink - bb[1]), initial, font=f, fill=tc)
        _horizon_lines(d, int(S*0.30), int(S*0.40), y_ink + (bb[3]-bb[1]) + int(S*0.07),
                       int(S*0.045), ac, S - int(S*0.08))
    elif comp == "editorial":
        # G: serif harf + çift çizgi + elmas
        f = _pil_font(fname, int(S*0.5))
        bb = d.textbbox((0, 0), initial, font=f)
        nh = bb[3]-bb[1]
        ink_top = (S-nh)//2
        d.text(((S-(bb[2]-bb[0]))//2 - bb[0], ink_top - bb[1]), initial, font=f, fill=pc)
        _editorial_rules(d, S//2, int(S*0.46), ink_top - int(S*0.10),
                         ink_top + nh + int(S*0.08), ac, dr=int(S*0.012))
    elif comp == "badge":
        # H: çift ring + pusula tikleri + harf (rozet dili)
        r1, r2 = int(S*0.40), int(S*0.365)
        d.ellipse([S//2-r1, S//2-r1, S//2+r1, S//2+r1], outline=pc, width=4)
        d.ellipse([S//2-r2, S//2-r2, S//2+r2, S//2+r2], outline=ac, width=1)
        tk = int(S*0.035)
        for dx, dy in ((0, -r1), (0, r1), (-r1, 0), (r1, 0)):
            x0, y0 = S//2 + dx, S//2 + dy
            if dx == 0:
                d.line([(x0, y0 - tk//2), (x0, y0 + tk//2)], fill=ac, width=4)
            else:
                d.line([(x0 - tk//2, y0), (x0 + tk//2, y0)], fill=ac, width=4)
        f = _pil_font(fname, int(S*0.40))
        bb = d.textbbox((0, 0), initial, font=f)
        d.text(((S-(bb[2]-bb[0]))//2 - bb[0], (S-(bb[3]-bb[1]))//2 - bb[1]),
               initial, font=f, fill=tc)
    elif comp == "playful":
        # J: renk dönüşümlü zıplayan harf + aksan nokta
        f = _pil_font(fname, int(S*0.58))
        bb = d.textbbox((0, 0), initial, font=f)
        x = (S-(bb[2]-bb[0]))//2 - bb[0]
        ink = (S-(bb[3]-bb[1]))//2
        d.text((x + int(S*0.03), ink - bb[1] + int(S*0.03)), initial, font=f, fill=ac)
        d.text((x, ink - bb[1]), initial, font=f, fill=pc)
        dot_r = int(S*0.045)
        d.ellipse([x + (bb[2]-bb[0]) + int(S*0.03), ink + (bb[3]-bb[1]) - dot_r*2,
                   x + (bb[2]-bb[0]) + int(S*0.03) + dot_r*2, ink + (bb[3]-bb[1])], fill=ac)
    elif comp == "statement":
        # B: harf + altında aksan bar (statement dili)
        f = _pil_font(fname, int(S*0.52))
        bb = d.textbbox((0, 0), initial, font=f)
        nh = bb[3]-bb[1]
        ink_top = (S-nh)//2 - int(S*0.04)
        d.text(((S-(bb[2]-bb[0]))//2 - bb[0], ink_top - bb[1]), initial, font=f, fill=pc)
        bar_w = int((bb[2]-bb[0]) * 1.1)
        by = ink_top + nh + int(S*0.06)
        d.rectangle([(S-bar_w)//2, by, (S+bar_w)//2, by + 10], fill=ac)
    else:
        # I corporate: ring + harf + kısa çizgi (ölçülü, simetrik)
        r = int(S*0.40)
        d.ellipse([S//2-r, S//2-r, S//2+r, S//2+r], outline=ac, width=5)
        f = _pil_font(fname, int(S*0.38))
        bb = d.textbbox((0, 0), initial, font=f)
        nh = bb[3]-bb[1]
        ink_top = (S-nh)//2 - int(S*0.02)
        d.text(((S-(bb[2]-bb[0]))//2 - bb[0], ink_top - bb[1]), initial, font=f, fill=pc)
        rw = int(S*0.12)
        d.rectangle([(S-rw)//2, ink_top + nh + int(S*0.05), (S+rw)//2,
                     ink_top + nh + int(S*0.05) + 4], fill=ac)
    return img


# ═════════════════════════════════════════════════════════════════════════════
#  IG HIGHLIGHT KAPAKLARI — 1080×1080, circle-safe (r≈0.40S). Template DNA'lı.
# ═════════════════════════════════════════════════════════════════════════════

def _highlight(brief: dict, studio_label: str, label: str) -> Image.Image:
    c = _tpl_ctx(brief, studio_label)
    S = 1080
    cx = S // 2
    r = int(S * 0.40)
    bg_hex = c["bg"]
    bg = _pil_rgb(bg_hex)
    pc = _pil_rgb(_cguard(c["primary"], bg_hex))
    ac = _pil_rgb(_cguard(c["accent"], bg_hex))
    sc = _pil_rgb(_cguard(c["secondary"], bg_hex))
    tc = _pil_rgb(_neutral(bg_hex))
    label = _tr_upper(label)
    comp, fname, k = c["comp"], c["font"], max(c["track"], 0.08)

    img = Image.new("RGB", (S, S), bg)
    d = ImageDraw.Draw(img)

    # Etiketi daire güvenli alanına sığdır (tüm comp'lar için ortak ölçüm)
    avail = int(r * 1.35)
    fs = _fit_tracked(label, fname, avail, k, max_s=int(S * 0.12), min_s=30)
    f = _pil_font(fname, fs)
    tr = int(k * fs)
    tw = int(_tracked_width(label, f, tr))
    bb = d.textbbox((0, 0), label, font=f)
    nh = bb[3] - bb[1]
    ink_top = (S - nh) // 2

    if comp == "block":
        # A: dolu renk disk, etiket zeminden oyulmuş + aksan yay
        d.ellipse([cx-r, cx-r, cx+r, cx+r], fill=pc)
        d.arc([cx-r+14, cx-r+14, cx+r-14, cx+r-14], start=300, end=45, fill=ac, width=8)
        lab_fill = bg
        _draw_tracked(d, label, f, (S-tw)//2, ink_top - bb[1], lab_fill, tr)
    elif comp == "diagonal":
        # D: diyagonal bölünmüş disk
        d.ellipse([cx-r, cx-r, cx+r, cx+r], fill=pc)
        mask = Image.new("L", (S, S), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse([cx-r, cx-r, cx+r, cx+r], fill=255)
        half = Image.new("L", (S, S), 0)
        hd = ImageDraw.Draw(half)
        hd.polygon([(cx + int(r*0.45), cx-r-10), (S, cx-r-10), (S, cx+r+10),
                    (cx - int(r*0.25), cx+r+10)], fill=255)
        from PIL import ImageChops
        overlay_mask = ImageChops.multiply(mask, half)
        overlay = Image.new("RGB", (S, S), ac)
        img.paste(overlay, (0, 0), overlay_mask)
        d = ImageDraw.Draw(img)
        lab_fill = _pil_rgb("#FFFFFF" if _is_dark_hex(c["primary"]) else "#0D0D0D")
        _draw_tracked(d, label, f, (S-tw)//2, ink_top - bb[1], lab_fill, tr)
    elif comp == "oversize":
        # C: arkada kesilen dev ghost harf + önde etiket
        initial = _tr_upper((c["name"] or "B")[0])
        gf = _pil_font(fname, int(S*0.95))
        gbb = d.textbbox((0, 0), initial, font=gf)
        ghost = _mix(bg, pc, 0.22)
        d.text(((S-(gbb[2]-gbb[0]))//2 - gbb[0], (S-(gbb[3]-gbb[1]))//2 - gbb[1]),
               initial, font=gf, fill=ghost)
        _draw_tracked(d, label, f, (S-tw)//2, ink_top - bb[1], tc, tr)
    elif comp == "offset":
        # E: etiketin arkasında offset renk bloğu
        pad = int(fs*0.42)
        bx0, by0 = (S-tw)//2 - pad, ink_top - pad
        bx1, by1 = (S+tw)//2 + pad, ink_top + nh + pad
        d.rectangle([bx0+14, by0+14, bx1+14, by1+14], outline=ac, width=3)
        d.rectangle([bx0, by0, bx1, by1], fill=pc)
        lab_fill = _pil_rgb("#FFFFFF" if _is_dark_hex(c["primary"]) else "#0D0D0D")
        _draw_tracked(d, label, f, (S-tw)//2, ink_top - bb[1], lab_fill, tr)
    elif comp == "echo":
        # F: echo etiketi + ufuk çizgileri
        _echo_text(d, label, fname, fs, k, (S-tw)//2, ink_top, tc, ac, sc)
        _horizon_lines(d, (S-tw)//2, tw, ink_top + nh + int(S*0.05),
                       int(S*0.035), ac, cx + r - 20)
    elif comp == "editorial":
        # G: çift çizgi + elmas + serif etiket
        _draw_tracked(d, label, f, (S-tw)//2, ink_top - bb[1], pc, tr)
        _editorial_rules(d, cx, min(int(tw*1.3), int(r*1.7)), ink_top - int(S*0.07),
                         ink_top + nh + int(S*0.05), ac, dr=int(S*0.010))
    elif comp == "badge":
        # H: çift ring + pusula tikleri + tracked etiket
        d.ellipse([cx-r, cx-r, cx+r, cx+r], outline=pc, width=4)
        r2 = r - int(S*0.03)
        d.ellipse([cx-r2, cx-r2, cx+r2, cx+r2], outline=ac, width=1)
        tk = int(S*0.03)
        for dx, dy in ((0, -r), (0, r), (-r, 0), (r, 0)):
            x0, y0 = cx + dx, cx + dy
            if dx == 0:
                d.line([(x0, y0 - tk//2), (x0, y0 + tk//2)], fill=ac, width=4)
            else:
                d.line([(x0 - tk//2, y0), (x0 + tk//2, y0)], fill=ac, width=4)
        _draw_tracked(d, label, f, (S-tw)//2, ink_top - bb[1], tc, tr)
    elif comp == "playful":
        # J: zıplayan renkli etiket + üçlü nokta kümesi
        cols = [pc, tc, ac]
        tw2, nh2 = _bounce_text(d, label, fname, fs, (S - int(_pil_font(fname, fs).getlength(label)))//2,
                                ink_top, cols)
        dot_r = int(S*0.028)
        base_y = ink_top - int(S*0.12)
        for i, (dx, col) in enumerate(((-int(S*0.07), ac), (0, pc), (int(S*0.07), sc))):
            yy = base_y + (dot_r if i % 2 else 0)
            d.ellipse([cx+dx-dot_r, yy-dot_r, cx+dx+dot_r, yy+dot_r], fill=col)
    elif comp == "statement":
        # B: etiket + altında aksan bar
        _draw_tracked(d, label, f, (S-tw)//2, ink_top - bb[1], pc, tr)
        by = ink_top + nh + int(S*0.045)
        d.rectangle([(S-tw)//2, by, (S+tw)//2, by + 8], fill=ac)
    else:
        # I corporate: ince ring + etiket + kısa orta çizgi
        d.ellipse([cx-r, cx-r, cx+r, cx+r], outline=ac, width=4)
        _draw_tracked(d, label, f, (S-tw)//2, ink_top - bb[1], tc, tr)
        rw = int(tw*0.4)
        d.rectangle([(S-rw)//2, ink_top + nh + int(S*0.045), (S+rw)//2,
                     ink_top + nh + int(S*0.045) + 4], fill=ac)
    return img


# ═════════════════════════════════════════════════════════════════════════════
#  SOSYAL BANNERLAR — LinkedIn 1584×396, X 1500×500. ANA logonun lockup dilinin
#  banner oranına uyarlanmış hali (marka tanınırlığı lockup'tan miras alınır).
# ═════════════════════════════════════════════════════════════════════════════

def _banner(brief: dict, studio_label: str, W: int, H: int) -> Image.Image:
    c = _tpl_ctx(brief, studio_label)
    bg_hex = c["bg"]
    bg = _pil_rgb(bg_hex)
    pc = _pil_rgb(_cguard(c["primary"], bg_hex))
    ac = _pil_rgb(_cguard(c["accent"], bg_hex))
    sc = _pil_rgb(_cguard(c["secondary"], bg_hex))
    tc = _pil_rgb(_neutral(bg_hex))
    name = _tr_upper(c["name"])
    tag = _tr_upper(c["tagline"])[:42]
    comp, fname, k = c["comp"], c["font"], c["track"]

    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    def _tagline(x, y, fill, center=False, max_w=None):
        """Tagline çiz — genişliğe SIĞDIRARAK (QA v2: J'de sağa taşma yakalandı).
        Hiyerarşi: tagline hiçbir zaman wordmark'la yarışmaz (H*0.07 tavan)."""
        if not tag:
            return
        limit = max_w if max_w else (W - x - int(W * 0.05))
        ts = max(18, int(H * 0.07))
        while ts > 16:
            tf = _pil_font("body", ts)
            ttr = int(0.22 * ts)
            if _tracked_width(tag, tf, ttr) <= limit:
                break
            ts -= 2
        tf = _pil_font("body", ts)
        ttr = int(0.22 * ts)
        tw_ = _tracked_width(tag, tf, ttr)
        tx = int((W - tw_) // 2) if center else x
        _draw_tracked(d, tag, tf, tx, y, fill, ttr)

    if comp == "block":
        # A: renk alanı + aksan şeridi; wordmark alanda (logo A'nın banner hali)
        bw = int(W * 0.72)
        d.rectangle([0, 0, bw, H], fill=pc)
        d.rectangle([bw, 0, bw + int(W * 0.035), H], fill=ac)
        fill = _pil_rgb("#FFFFFF" if _is_dark_hex(c["primary"]) else "#0D0D0D")
        fs = _fit_tracked(name, fname, bw - 200, k, max_s=int(H * 0.42))
        f = _pil_font(fname, fs)
        bb = d.textbbox((0, 0), name, font=f)
        nh = bb[3] - bb[1]
        ink = (H - nh) // 2 - (int(H * 0.07) if tag else 0)
        _draw_tracked(d, name, f, 90, ink - bb[1], fill, int(k * fs))
        _tagline(90, ink + nh + int(H * 0.10), _mix(_pil_rgb(c["primary"]), fill, 0.62))
    elif comp == "diagonal":
        # D: diyagonal alan + aksan şerit
        px = int(W * 0.58)
        d.polygon([(0, 0), (px, 0), (int(W * 0.44), H), (0, H)], fill=pc)
        d.polygon([(px, 0), (px + int(W * 0.035), 0),
                   (int(W * 0.44) + int(W * 0.035), H), (int(W * 0.44), H)], fill=ac)
        fill = _pil_rgb("#FFFFFF" if _is_dark_hex(c["primary"]) else "#0D0D0D")
        fs = _fit_tracked(name, fname, int(W * 0.38), k, max_s=int(H * 0.36))
        f = _pil_font(fname, fs)
        bb = d.textbbox((0, 0), name, font=f)
        nh = bb[3] - bb[1]
        ink = (H - nh) // 2 - (int(H * 0.07) if tag else 0)
        _draw_tracked(d, name, f, 80, ink - bb[1], fill, int(k * fs))
        _tagline(80, ink + nh + int(H * 0.10), _mix(_pil_rgb(c["primary"]), fill, 0.62))
    elif comp == "oversize":
        # C: solda kesilen dev harf + sağda isim
        initial = name[0] if name else "?"
        gf = _pil_font(fname, int(H * 1.35))
        gbb = d.textbbox((0, 0), initial, font=gf)
        d.text((-int((gbb[2]-gbb[0]) * 0.18) - gbb[0], -int(H * 0.22) - gbb[1]),
               initial, font=gf, fill=pc)
        rx = int((gbb[2]-gbb[0]) * 0.75) + 60
        rest = name[1:] if len(name) > 1 else name
        fs = _fit_tracked(rest, fname, W - rx - 90, k, max_s=int(H * 0.34))
        f = _pil_font(fname, fs)
        bb = d.textbbox((0, 0), rest, font=f)
        nh = bb[3] - bb[1]
        ink = (H - nh) // 2 - (int(H * 0.06) if tag else 0)
        _draw_tracked(d, rest, f, rx, ink - bb[1], tc, int(k * fs))
        _tagline(rx, ink + nh + int(H * 0.09), tuple(_mix(bg, tc, 0.6)))
    elif comp == "offset":
        # E: offset blok içinde wordmark
        bx, by = int(W * 0.05), int(H * 0.16)
        bw2, bh = int(W * 0.66), int(H * 0.62)
        d.rectangle([bx + 12, by + 12, bx + bw2 + 12, by + bh + 12], outline=ac, width=3)
        d.rectangle([bx, by, bx + bw2, by + bh], fill=pc)
        fill = _pil_rgb("#FFFFFF" if _is_dark_hex(c["primary"]) else "#0D0D0D")
        fs = _fit_tracked(name, fname, bw2 - 120, k, max_s=int(bh * 0.52))
        f = _pil_font(fname, fs)
        bb = d.textbbox((0, 0), name, font=f)
        _draw_tracked(d, name, f, bx + 60, by + (bh - (bb[3]-bb[1]))//2 - bb[1], fill, int(k * fs))
        _tagline(bx + bw2 + 44, H // 2 - int(H * 0.05), tuple(_mix(bg, tc, 0.6)))
    elif comp == "echo":
        # F: echo wordmark + ufuk çizgileri (logo F'in banner hali)
        # QA v2: avail 0.62→0.72 — wordmark kart/banner'da cılız kalıyordu
        fs = _fit_tracked(name, fname, int(W * 0.72), k, max_s=int(H * 0.44))
        f = _pil_font(fname, fs)
        tr = int(k * fs)
        tw = int(_tracked_width(name, f, tr))
        bb = d.textbbox((0, 0), name, font=f)
        nh = bb[3] - bb[1]
        ink = (H - nh) // 2 - int(H * 0.10)
        x = (W - tw) // 2
        _echo_text(d, name, fname, fs, k, x, ink, tc, ac, sc)
        _horizon_lines(d, x, tw, ink + nh + int(H * 0.10), int(H * 0.055), ac, H - 24)
        _tagline(0, int(H * 0.06), tuple(_mix(bg, tc, 0.55)), center=True)
    elif comp == "editorial":
        # G: masthead — çift çizgi + elmas + tracked serif (logo G'nin banner hali)
        fs = _fit_tracked(name, fname, int(W * 0.56), k, max_s=int(H * 0.38))
        f = _pil_font(fname, fs)
        tr = int(k * fs)
        tw = int(_tracked_width(name, f, tr))
        bb = d.textbbox((0, 0), name, font=f)
        nh = bb[3] - bb[1]
        ink = (H - nh) // 2
        _draw_tracked(d, name, f, (W - tw) // 2, ink - bb[1], pc, tr)
        _editorial_rules(d, W // 2, min(int(tw * 1.18), W - 260), ink - int(H * 0.14),
                         ink + nh + int(H * 0.11), ac, dr=max(6, int(H * 0.02)))
        _tagline(0, ink + nh + int(H * 0.11) + 14 + int(H * 0.05),
                 tuple(_mix(bg, tc, 0.6)), center=True)
    elif comp == "badge":
        # H: yatay linework çerçeve + tikler (logo H'nin banner hali)
        bx0, by0 = int(W * 0.05), int(H * 0.14)
        bx1, by1 = W - bx0, H - by0
        try:
            d.rounded_rectangle([bx0, by0, bx1, by1], radius=int(H * 0.07), outline=pc, width=3)
            d.rounded_rectangle([bx0 + 10, by0 + 10, bx1 - 10, by1 - 10],
                                radius=int(H * 0.055), outline=ac, width=1)
        except AttributeError:
            d.rectangle([bx0, by0, bx1, by1], outline=pc, width=3)
        _badge_ticks(d, (bx0 + 22, by0 + 22, bx1 - 22, by1 - 22), ac, int(H * 0.05))
        fs = _fit_tracked(name, fname, (bx1 - bx0) - 220, max(k, 0.08), max_s=int(H * 0.30))
        f = _pil_font(fname, fs)
        tr = int(max(k, 0.08) * fs)
        tw = int(_tracked_width(name, f, tr))
        bb = d.textbbox((0, 0), name, font=f)
        nh = bb[3] - bb[1]
        ink = (H - nh) // 2 - (int(H * 0.06) if tag else 0)
        _draw_tracked(d, name, f, (W - tw) // 2, ink - bb[1], tc, tr)
        _tagline(0, ink + nh + int(H * 0.08), tuple(_mix(bg, tc, 0.6)), center=True)
    elif comp == "playful":
        # J: staircase stack veya zıplayan harfler + nokta (logo J'nin banner hali)
        words = [w for w in name.split() if w]
        if len(words) >= 2:
            l1, l2 = words[0], " ".join(words[1:])
            fs = min(_fit_font_size(l1, fname, int(W * 0.44)),
                     _fit_font_size(l2, fname, int(W * 0.44)), int(H * 0.34))
            f = _pil_font(fname, fs)
            bb1 = d.textbbox((0, 0), l1, font=f)
            bb2 = d.textbbox((0, 0), l2, font=f)
            nh1, nh2 = bb1[3]-bb1[1], bb2[3]-bb2[1]
            gap = int(fs * 0.14)
            top = (H - (nh1 + gap + nh2)) // 2
            x1 = int(W * 0.06)
            x2 = x1 + int(fs * 0.55)
            d.text((x1, top - bb1[1]), l1, font=f, fill=pc)
            d.text((x2, top + nh1 + gap - bb2[1]), l2, font=f, fill=tc)
            dot_r = max(6, int(fs * 0.09))
            asc, _ = f.getmetrics()
            dcx = x2 + int(f.getlength(l2)) + int(fs * 0.18)
            dcy = top + nh1 + gap - bb2[1] + asc - dot_r
            d.ellipse([dcx - dot_r, dcy - dot_r, dcx + dot_r, dcy + dot_r], fill=ac)
            # QA v2 fix: tagline sağ kolonda taşıyordu — stack'in altına, x1 hizasına
            _tagline(x1, top + nh1 + gap + nh2 + int(H * 0.06), tuple(_mix(bg, tc, 0.6)))
        else:
            fs = _fit_font_size(name, fname, int(W * 0.6))
            fs = min(fs, int(H * 0.42))
            f = _pil_font(fname, fs)
            bb = d.textbbox((0, 0), name, font=f)
            nh = bb[3] - bb[1]
            ink = (H - nh) // 2 - (int(H * 0.07) if tag else 0)
            x = int((W - f.getlength(name)) // 2)
            _bounce_text(d, name, fname, fs, x, ink, [tc, pc, ac])
            _tagline(0, ink + nh + int(H * 0.12), tuple(_mix(bg, tc, 0.6)), center=True)
    elif comp == "statement":
        # B: sol wordmark + altında aksan bar + sağ altta tagline (logo B'nin banner hali)
        fs = _fit_tracked(name, fname, int(W * 0.60), k, max_s=int(H * 0.42))
        f = _pil_font(fname, fs)
        tr = int(k * fs)
        tw = int(_tracked_width(name, f, tr))
        bb = d.textbbox((0, 0), name, font=f)
        nh = bb[3] - bb[1]
        ink = (H - nh) // 2 - int(H * 0.07)
        x = int(W * 0.055)
        _draw_tracked(d, name, f, x, ink - bb[1], pc, tr)
        bar_y = ink + nh + max(12, int(nh * 0.12))
        d.rectangle([x, bar_y, x + tw + 8, bar_y + 8], fill=ac)
        if tag:
            # QA v3: sığdırma güvenliği (uzun tagline sağdan taşmasın)
            ts = max(20, int(H * 0.07))
            while ts > 16:
                tf = _pil_font("body", ts)
                ttr = int(0.22 * ts)
                if _tracked_width(tag, tf, ttr) <= W - int(W * 0.11):
                    break
                ts -= 2
            tf = _pil_font("body", ts)
            ttr = int(0.22 * ts)
            tw_ = _tracked_width(tag, tf, ttr)
            _draw_tracked(d, tag, tf, W - int(W * 0.055) - int(tw_), bar_y + 8 + int(H * 0.06),
                          sc, ttr)
    else:
        # I corporate: sol wordmark + dikey ayraç + sağ tagline (logo I'nin banner hali)
        avail = int(W * 0.48) if tag else int(W * 0.7)
        fs = _fit_tracked(name, fname, avail, k, max_s=int(H * 0.36))
        f = _pil_font(fname, fs)
        tr = int(k * fs)
        tw = int(_tracked_width(name, f, tr))
        bb = d.textbbox((0, 0), name, font=f)
        nh = bb[3] - bb[1]
        ink = (H - nh) // 2
        x = int(W * 0.06) if tag else (W - tw) // 2
        _draw_tracked(d, name, f, x, ink - bb[1], pc, tr)
        if tag:
            div_x = x + tw + int(W * 0.035)
            d.rectangle([div_x, int(H * 0.30), div_x + 2, int(H * 0.70)], fill=ac)
            # QA v3 fix: tagline sabit boyutla kartta taşıyordu — genişliğe fit et
            allowed = W - int(W * 0.05) - (div_x + int(W * 0.025))
            ts = max(20, int(H * 0.09))
            while ts > 16:
                tf = _pil_font("body", ts)
                ttr = int(0.14 * ts)
                if _tracked_width(tag, tf, ttr) <= allowed:
                    break
                ts -= 2
            tf = _pil_font("body", ts)
            ttr = int(0.14 * ts)
            tbb = d.textbbox((0, 0), tag, font=tf)
            _draw_tracked(d, tag, tf, div_x + int(W * 0.025),
                          (H - (tbb[3]-tbb[1])) // 2 - tbb[1], sc, ttr)
        else:
            uy = ink + nh + int(H * 0.08)
            d.rectangle([x, uy, x + tw, uy + 3], fill=ac)
    return img


# ═════════════════════════════════════════════════════════════════════════════
#  KARTVİZİT — 1050×600 (3.5"×2" @300dpi)
#  Arka yüz: markanın lockup dili (banner motoruyla AYNI kaynak, kart oranında)
#  Ön yüz: iletişim bloğu sabit (okunurluk) + sol bölge template DNA'lı motif
# ═════════════════════════════════════════════════════════════════════════════

CARD_W, CARD_H = 1050, 600


def generate_card_back_v2(brief: dict, studio_label: str = "") -> Image.Image:
    """Arka yüz = lockup dilinin kart oranına uyarlanmış hali + print crop mark."""
    img = _banner(brief, studio_label, CARD_W, CARD_H)
    d = ImageDraw.Draw(img)
    c = _tpl_ctx(brief, studio_label)
    # comp'a göre zemin değişiyor — crop mark rengini gerçek köşe pikselinden türet
    corner = img.getpixel((6, 6))
    tone = _mix(corner, _pil_rgb(_neutral(c["bg"])) if sum(corner) < 380 else (20, 20, 20), 0.5)
    m = 26
    for (x0, y0, dx, dy) in ((m, m, 1, 1), (CARD_W - m, CARD_H - m, -1, -1)):
        d.line([(x0, y0), (x0 + 34 * dx, y0)], fill=tone, width=1)
        d.line([(x0, y0), (x0, y0 + 34 * dy)], fill=tone, width=1)
    return img


def generate_card_front_v2(brief: dict, studio_label: str = "") -> Image.Image:
    c = _tpl_ctx(brief, studio_label)
    bg_hex = c["bg"]
    bg = _pil_rgb(bg_hex)
    pc = _pil_rgb(_cguard(c["primary"], bg_hex))
    ac = _pil_rgb(_cguard(c["accent"], bg_hex))
    tc = _pil_rgb(_cguard(c["secondary"], bg_hex))
    ghost = _mix(bg, tc, 0.08)
    muted = _mix(bg, tc, 0.58)
    dim = _mix(bg, tc, 0.30)
    initial = _tr_upper((c["name"] or "B")[0])
    comp, fname = c["comp"], c["font"]

    img = Image.new("RGB", (CARD_W, CARD_H), bg)
    d = ImageDraw.Draw(img)

    info_x = int(CARD_W * 0.52) + 40  # varsayılan bilgi bloğu başlangıcı

    # ── Sol bölge: template DNA'lı motif ─────────────────────────────────────
    if comp in ("block", "diagonal", "offset"):
        # Renk alanı + oyulmuş harf (A/D/E aileleri; D'de alan diyagonal kesilir)
        fw = int(CARD_W * 0.46)
        if comp == "diagonal":
            d.polygon([(0, 0), (fw + 60, 0), (fw - 60, CARD_H), (0, CARD_H)], fill=pc)
            d.polygon([(fw + 60, 0), (fw + 84, 0), (fw - 36, CARD_H), (fw - 60, CARD_H)], fill=ac)
        elif comp == "offset":
            d.rectangle([26, 26, fw, CARD_H - 26], fill=pc)
            d.rectangle([38, 38, fw + 12, CARD_H - 14], outline=ac, width=2)
        else:
            d.rectangle([0, 0, fw, CARD_H], fill=pc)
            d.rectangle([fw, 0, fw + 14, CARD_H], fill=ac)
        f = _pil_font(fname, int(CARD_H * 0.52))
        bb = d.textbbox((0, 0), initial, font=f)
        fill = _pil_rgb("#FFFFFF" if _is_dark_hex(c["primary"]) else "#0D0D0D")
        d.text(((fw - (bb[2]-bb[0])) // 2 - bb[0], (CARD_H - (bb[3]-bb[1])) // 2 - bb[1]),
               initial, font=f, fill=fill)
        info_x = fw + 64
    elif comp == "echo":
        gf = _pil_font(fname, int(CARD_H * 1.15))
        gbb = d.textbbox((0, 0), initial, font=gf)
        gx, gy = -int(CARD_W * 0.04) - gbb[0], -int(CARD_H * 0.16) - gbb[1]
        d.text((gx + 14, gy + 14), initial, font=gf, fill=_mix(bg, _pil_rgb(_cguard(c["accent"], bg_hex)), 0.16))
        d.text((gx, gy), initial, font=gf, fill=ghost)
    elif comp == "editorial":
        _editorial_rules(d, int(CARD_W * 0.26), int(CARD_W * 0.34),
                         int(CARD_H * 0.20), int(CARD_H * 0.76), ac, dr=7)
        f = _pil_font(fname, int(CARD_H * 0.42))
        bb = d.textbbox((0, 0), initial, font=f)
        d.text((int(CARD_W * 0.26) - (bb[2]-bb[0])//2 - bb[0],
                (CARD_H - (bb[3]-bb[1]))//2 - bb[1]), initial, font=f, fill=pc)
    elif comp == "badge":
        try:
            d.rounded_rectangle([22, 22, CARD_W - 22, CARD_H - 22], radius=30, outline=pc, width=2)
            d.rounded_rectangle([32, 32, CARD_W - 32, CARD_H - 32], radius=24, outline=ac, width=1)
        except AttributeError:
            d.rectangle([22, 22, CARD_W - 22, CARD_H - 22], outline=pc, width=2)
        _badge_ticks(d, (44, 44, CARD_W - 44, CARD_H - 44), ac, 20, width=2)
        f = _pil_font(fname, int(CARD_H * 0.40))
        bb = d.textbbox((0, 0), initial, font=f)
        d.text((int(CARD_W * 0.26) - (bb[2]-bb[0])//2 - bb[0],
                (CARD_H - (bb[3]-bb[1]))//2 - bb[1]), initial, font=f, fill=tc)
    elif comp == "playful":
        f = _pil_font(fname, int(CARD_H * 0.62))
        bb = d.textbbox((0, 0), initial, font=f)
        x0 = int(CARD_W * 0.24) - (bb[2]-bb[0])//2
        d.text((x0 + 10 - bb[0], (CARD_H - (bb[3]-bb[1]))//2 - bb[1] + 10), initial, font=f, fill=ac)
        d.text((x0 - bb[0], (CARD_H - (bb[3]-bb[1]))//2 - bb[1]), initial, font=f, fill=pc)
        dr = int(CARD_H * 0.035)
        d.ellipse([x0 + (bb[2]-bb[0]) + 16, int(CARD_H * 0.64), x0 + (bb[2]-bb[0]) + 16 + dr*2,
                   int(CARD_H * 0.64) + dr*2], fill=ac)
    elif comp == "oversize":
        gf = _pil_font(fname, int(CARD_H * 1.4))
        gbb = d.textbbox((0, 0), initial, font=gf)
        d.text((-int((gbb[2]-gbb[0]) * 0.16) - gbb[0], -int(CARD_H * 0.24) - gbb[1]),
               initial, font=gf, fill=_mix(bg, pc, 0.30))
    elif comp == "statement":
        f = _pil_font(fname, int(CARD_H * 0.48))
        bb = d.textbbox((0, 0), initial, font=f)
        nh = bb[3]-bb[1]
        ix = int(CARD_W * 0.24) - (bb[2]-bb[0])//2
        iy = (CARD_H - nh)//2 - int(CARD_H * 0.04)
        d.text((ix - bb[0], iy - bb[1]), initial, font=f, fill=pc)
        d.rectangle([ix, iy + nh + int(CARD_H * 0.05), ix + (bb[2]-bb[0]),
                     iy + nh + int(CARD_H * 0.05) + 7], fill=ac)
    else:
        # I corporate: v1'in ölçülü ghost+ayraç dili zaten kurumsal — korunur
        gf = _pil_font(fname, int(CARD_H * 1.5))
        gbb = d.textbbox((0, 0), initial, font=gf)
        d.text((-int(CARD_W * 0.06) - gbb[0], -int(CARD_H * 0.22) - gbb[1]),
               initial, font=gf, fill=ghost)
        div_x = int(CARD_W * 0.52)
        d.line([(div_x, CARD_H * 0.16), (div_x, CARD_H * 0.84)], fill=dim, width=1)
        d.ellipse([div_x - 3, CARD_H * 0.16 - 3, div_x + 3, CARD_H * 0.16 + 3], fill=ac)

    # ── Sağ bilgi bloğu (tüm comp'larda ortak — okunurluk pazarlık edilmez) ──
    x = info_x
    fs_wm = min(_fit_tracked(_tr_upper(c["name"]), fname, CARD_W - x - 40, max(c["track"], 0.04),
                             max_s=int(CARD_H * 0.105)), int(CARD_H * 0.105))
    f_wm = _pil_font(fname, fs_wm)
    wm_bb = d.textbbox((0, 0), _tr_upper(c["name"]), font=f_wm)
    y = int(CARD_H * 0.18)
    _draw_tracked(d, _tr_upper(c["name"]), f_wm, x, y - wm_bb[1],
                  _pil_rgb(_cguard(c["accent"], bg_hex)), int(max(c["track"], 0.04) * fs_wm))
    y += (wm_bb[3] - wm_bb[1]) + int(CARD_H * 0.055)

    d.text((x, y), "Ad Soyad", font=_pil_font("body", int(CARD_H * 0.075)), fill=tc)
    y += int(CARD_H * 0.115)
    d.text((x, y), "Kurucu", font=_pil_font("body", int(CARD_H * 0.05)), fill=muted)
    y += int(CARD_H * 0.115)
    d.line([(x, y), (CARD_W - 44, y)], fill=dim, width=1)
    y += int(CARD_H * 0.055)
    slug = c["name"].lower().replace(" ", "").replace("ı", "i").replace("ş", "s") \
        .replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")
    cf = _pil_font("body", int(CARD_H * 0.045))
    d.text((x, y), f"hello@{slug}.com", font=cf, fill=muted)
    y += int(CARD_H * 0.09)
    d.text((x, y), f"{slug}.com", font=cf, fill=muted)
    return img


# ═════════════════════════════════════════════════════════════════════════════
#  LOGO REVERSED — mono'nun polarite-ters hali (kanal inversiyonu DEĞİL)
# ═════════════════════════════════════════════════════════════════════════════

def generate_logo_reversed(brief: dict, mono_uri: str) -> Image.Image:
    bg_hex = brief.get("bg_color", "#0F0D0C")
    dark = _is_dark_hex(bg_hex)
    zemin = _pil_rgb(_LIGHT_NEUTRAL if dark else _DARK_NEUTRAL)
    glyph = _pil_rgb(_DARK_NEUTRAL if dark else _LIGHT_NEUTRAL)
    mono = _datauri_to_rgba(mono_uri)
    if mono is None:
        return Image.new("RGB", (1600, 420), zemin)
    base = Image.new("RGB", mono.size, zemin)
    layer = Image.new("RGB", mono.size, glyph)
    base.paste(layer, mask=mono.split()[-1])
    return base


# ═════════════════════════════════════════════════════════════════════════════
#  ANA GİRİŞ — tek kaynak (html_preview + finalize_job ikisi de bunu çağırır)
# ═════════════════════════════════════════════════════════════════════════════

def generate_extended_pil_assets(brief: dict, studio_label: str = "",
                                 mono_uri: str = "") -> dict:
    """Tüm PIL asset'lerini üretir → {anahtar: data URI}. Hata durumunda slot ""
    döner (kit o bölümü gizler, pipeline kırılmaz).

    Anahtarlar: card_front, card_back, profile_dark, profile_light,
    highlight_1..4, banner_linkedin, banner_twitter, logo_reversed
    """
    out: dict = {}

    def _safe(key, fn, *a):
        try:
            out[key] = _png_uri(fn(*a))
        except Exception as e:
            print(f"[asset_generator] {key} üretilemedi: {e}")
            out[key] = ""

    _safe("card_front", generate_card_front_v2, brief, studio_label)
    _safe("card_back", generate_card_back_v2, brief, studio_label)
    _safe("profile_dark", _profile, brief, studio_label, True)
    _safe("profile_light", _profile, brief, studio_label, False)

    labels = [str(l).strip() for l in (brief.get("highlight_labels") or []) if str(l).strip()]
    # Daire güvenli alanı için üst sınır — KELİME GÜVENLİ kısaltma (canlı test
    # bulgusu, 20 Tem: sert [:12] "BUGÜNÜN EKMEK"i "BUGÜNÜN EKME" yapıyordu).
    # Uzun etiketten ilk kelime alınır; tek kelime de uzunsa ancak o zaman kesilir.
    def _fit_label(l: str) -> str:
        if len(l) <= 12:
            return l
        first = l.split()[0]
        return first if len(first) <= 12 else first[:12]
    labels = [_fit_label(l) for l in labels]
    labels = (labels + _DEFAULT_HIGHLIGHTS)[:4]
    for i, lbl in enumerate(labels, start=1):
        _safe(f"highlight_{i}", _highlight, brief, studio_label, lbl)

    _safe("banner_linkedin", _banner, brief, studio_label, 1584, 396)
    _safe("banner_twitter", _banner, brief, studio_label, 1500, 500)
    _safe("logo_reversed", generate_logo_reversed, brief, mono_uri)

    out["_highlight_labels"] = labels
    return out
