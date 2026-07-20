"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  DOKUNMA BÖLGESİ: BACKEND / GENERATOR                                        ║
║  Deploy: deploy_backend.command                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

ANA LOGO LOCKUP — AI mark + PIL wordmark (Görev 2E, 20 Temmuz 2026)

NEDEN VAR (Serhat, AXIS LOGISTICS örneği):
"hep markanın ismi tamamı metin olarak yazılıyor" — BrandGen'in ana logosu
bugüne kadar sadece WORDMARK'tı. AXIS'te olan şey ise üstte harflerden türemiş
bir İŞARET, altında isim. Bu dosya o lockup'ı kuruyor.

SLOT YENİDEN DÜZENİ (Serhat kararı, 20 Tem):
    Ana   = AI mark + altında wordmark        ← BU DOSYA
    Tipo  = eski Ana (template lockup'lı wordmark, select_logo_primary_png)
    İkon  = markın tek başına hali (aynı SVG, ikinci çağrı YOK)
    Mono / Ters = mevcut mantık

NEDEN SVG İÇİNE PNG GÖMÜYORUZ:
Mark gerçek SVG (Recraft V4.1), wordmark ise PIL PNG. Rasterize etmek için
cairosvg/rsvg gibi SİSTEM bağımlılığı gerekirdi — Fly imajında garanti değil,
kırılma riski yüksek. Bunun yerine mark'ın vektör yapısı AYNEN korunur ve
wordmark <image> olarak gömülür. Tek dosya, tarayıcıda ve Illustrator'da açılır,
sistem bağımlılığı sıfır.

TÜRKÇE GÜVENLİĞİ: wordmark'ı model YAZMIYOR, PIL basıyor → "PEPİTO" hep doğru.
(20 Tem'deki tofu bug'ı bu yüzden lockup'ta yapısal olarak imkânsız.)
"""
# Python 3.9 uyumu (Mac'te lokal QA koşabilsin): 3.10+ tip
# annotation'larini (dict | None) string'e cevirir, runtime degismez.
from __future__ import annotations


import base64
import re

from PIL import Image, ImageDraw

try:
    from .logo_generator import (
        _pil_font, _pil_rgb, _tr_upper, _brand_upper, _tpl_font_name,
        _resolve_template, _is_dark_hex, _png_uri,
        _tracked_width, _draw_tracked,
    )
except ImportError:  # doğrudan çalıştırma / test
    from logo_generator import (
        _pil_font, _pil_rgb, _tr_upper, _brand_upper, _tpl_font_name,
        _resolve_template, _is_dark_hex, _png_uri,
        _tracked_width, _draw_tracked,
    )

# Lockup tuvali — mark üstte kare alan, wordmark altta
LW, LH = 1200, 900
MARK_BOX = 470          # markın oturacağı kare alanın kenarı
GAP = 74                # mark ile wordmark arası nefes


def _fit(draw, text, font_name, avail_w, max_s=200, min_s=24):
    s = max_s
    while s > min_s:
        f = _pil_font(font_name, s)
        if draw.textbbox((0, 0), text, font=f)[2] <= avail_w:
            return s
        s -= 3
    return min_s


def _wordmark_png(brief: dict, tpl: str, text_color: str) -> str:
    """Markın ALTINA girecek wordmark — şeffaf zemin, ortalı.

    İki kelimeli isimlerde AXIS mantığı: ilk kelime büyük, kalanı ince ve
    tracked (AXIS / LOGISTICS). Tek kelimede sadece isim basılır.
    """
    name = _brand_upper(brief)
    parts = [p for p in name.split() if p]
    head = parts[0] if len(parts) >= 2 else name
    rest = " ".join(parts[1:]) if len(parts) >= 2 else ""

    # Tuval bilerek YÜKSEK; sonunda gerçek içeriğe göre kırpılır.
    # (20 Tem: H=300 sabiti "LOGISTICS"/"SİGORTA"yı alttan kesiyordu — sabit
    # yükseklik varsayımı font boyutuna göre tutmuyor.)
    W, H = 1200, 620
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fn = _tpl_font_name(tpl)
    col = _pil_rgb(text_color)

    size = _fit(d, head, fn, int(W * 0.80), max_s=190)
    f = _pil_font(fn, size)
    b = d.textbbox((0, 0), head, font=f)
    hw, hh = b[2] - b[0], b[3] - b[1]
    hx, hy = (W - hw) / 2 - b[0], 30 - b[1]
    d.text((hx, hy), head, font=f, fill=col)

    if rest:
        # ikinci kelime: ince, tracked, ana kelimenin altına ortalanır
        #
        # BUG (İ noktası kopukluğu, açık konu — 20 Tem'de bulundu, bu oturumda
        # düzeltildi): önceki hali HER HARFİ KENDİ bbox'ının TEPESİNE göre
        # hizalıyordu (`ry - bb[1]` harf başına ayrı hesaplanıyordu). "İ"nin
        # noktası diğer harflerden (N/C/A/F) daha yükseğe çıktığı için, o ortak
        # tepe çizgisine göre hizalanınca İ'nin GÖVDESİ diğer harflerin
        # gövdesinden daha AŞAĞIDA kaldı — nokta üstte harflerle hizalı, gövde
        # aşağıda kayık: "FİNCAN" → nokta koptu gibi göründü ("F¡NCAN").
        # Çözüm: mevcut kod tabanında zaten kanıtlanmış tek-baseline deseni
        # (_tracked_width/_draw_tracked, banner/kartvizit'te kullanılıyor) —
        # bbox TÜM kelimeden TEK SEFER alınır, tüm harfler AYNI baseline'da
        # basılır; harf harf ilerleme sadece x ekseninde (advance + tracking).
        rs = max(26, int(size * 0.30))
        fr = _pil_font("body", rs)
        track = max(3, int(rs * 0.22))
        tw = int(_tracked_width(rest, fr, track))
        bb = d.textbbox((0, 0), rest, font=fr)
        cx = (W - tw) / 2
        ry = 30 + hh + int(rs * 0.85)
        _draw_tracked(d, rest, fr, cx, ry - bb[1], col, track)
        used = ry + (bb[3] - bb[1]) + 20
    else:
        used = 30 + hh + 18

    # Gerçek içerik sınırına göre kırp — sabit sayıya güvenme.
    bbox = img.getbbox()
    if bbox:
        img = img.crop((0, max(0, bbox[1] - 12), W, min(H, bbox[3] + 14)))
    else:
        img = img.crop((0, 0, W, int(used)))
    return _png_uri(img)


def _svg_inner(svg_text: str):
    """SVG gövdesini ve viewBox ölçülerini çıkarır. (içerik, w, h)"""
    m = re.search(r"<svg[^>]*>(.*)</svg>", svg_text, re.S | re.I)
    inner = m.group(1) if m else ""
    vb = re.search(r'viewBox="0\s+0\s+([\d.]+)\s+([\d.]+)"', svg_text, re.I)
    if vb:
        return inner, float(vb.group(1)), float(vb.group(2))
    return inner, 2048.0, 2048.0


def _decode_data_uri(uri: str) -> str:
    try:
        return base64.b64decode(uri.split(",", 1)[1]).decode("utf-8", "ignore")
    except Exception:
        return ""


def build_primary_lockup(brief: dict, mark_svg_uri: str, studio_label: str = "") -> str:
    """AI mark + wordmark → tek SVG data URI (ANA logo).

    mark_svg_uri boş veya bozuksa "" döner → çağıran taraf eski PIL ana logoya
    düşer (üretim asla kırılmaz).
    """
    if not mark_svg_uri or "svg+xml" not in mark_svg_uri:
        return ""
    svg_text = _decode_data_uri(mark_svg_uri)
    inner, mw, mh = _svg_inner(svg_text)
    if not inner.strip():
        return ""

    tpl = _resolve_template(brief, studio_label)
    bg = brief.get("bg_color", "#0F0D0C")
    # Wordmark rengi: zemine göre okunur ana metin tonu
    text_color = "#F2EDE4" if _is_dark_hex(bg) else "#151515"
    wm_uri = _wordmark_png(brief, tpl, text_color)

    # wordmark ölçüsü (gömülü PNG'nin gerçek oranı)
    try:
        import io
        wm_img = Image.open(io.BytesIO(base64.b64decode(wm_uri.split(",", 1)[1])))
        ww, wh = wm_img.size
    except Exception:
        ww, wh = 1200, 240

    # Mark'ı MARK_BOX içine oranı bozmadan sığdır, üstte ortala
    scale = MARK_BOX / max(mw, mh)
    sw, sh = mw * scale, mh * scale
    mx, my = (LW - sw) / 2, 60 + (MARK_BOX - sh) / 2

    # Wordmark: markın altında, tuval genişliğinin %52'si
    target_w = LW * 0.52
    wscale = target_w / ww
    wdw, wdh = ww * wscale, wh * wscale
    wx, wy = (LW - wdw) / 2, 60 + MARK_BOX + GAP

    total_h = int(wy + wdh + 70)

    # ZEMİN (20 Tem canlı bulgu): lockup ŞEFFAF bırakılırsa, açık zeminli
    # markalarda koyu wordmark koyu hücrede kayboluyordu (Axis testi). ANA logo
    # markanın kendi zeminini taşır — eski ana logo da böyleydi ve kitte doğru
    # duruyordu. "Kutu içinde kutu" riski yok, çünkü mark'ın kendi zemini
    # _strip_svg_bg ile zaten silinmiş durumda; burada TEK katman zemin var.
    # (İkon slotu şeffaf kalır — o tek başına, her yüzeyde kullanılacak.)
    return "data:image/svg+xml;base64," + base64.b64encode(
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="0 0 {LW} {total_h}" width="{LW}" height="{total_h}">'
            f'<rect x="0" y="0" width="{LW}" height="{total_h}" fill="{bg}"/>'
            f'<g transform="translate({mx:.2f},{my:.2f}) scale({scale:.5f})">{inner}</g>'
            f'<image x="{wx:.2f}" y="{wy:.2f}" width="{wdw:.2f}" height="{wdh:.2f}" '
            f'href="{wm_uri}" xlink:href="{wm_uri}"/>'
            f"</svg>"
        ).encode("utf-8")
    ).decode("ascii")
