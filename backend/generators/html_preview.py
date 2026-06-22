"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  DOKUNMA BÖLGESİ: BACKEND / GENERATOR                                      ║
║  Deploy: deploy_backend.command (çift tıkla)                                ║
║  Etkilediği katman: Fly.io backend — sadece bu katmanı değiştirir           ║
║                                                                              ║
║  BU DOSYAYA Frontend (Next.js/Vercel) değişikliği sırasında DOKUNMA.       ║
║  Dashboard veya admin UI düzenlerken bu dosyaya DOKUNMA.                    ║
║  window.BRAND şemasına yeni alan eklenirse: brand_brief_contract.py'yi      ║
║  ve brandgen-mimari.md §5'i de güncelle.                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

BrandGen HTML Kit v2 — İki Aşamalı Pipeline

Aşama 1 (Python): window.BRAND config'ini brief verisinden doldur.
  - name, tagline, energy, colors, palette, type → brief'ten direkt
  - story, concept, voice → brand_brief.py'nin ürettiği değerleri kullan (Sonnet, yeniden üretme)

Aşama 2 (Sonnet): Sadece SVG tasarımı — logo primary/icon/mono + 2 uygulama görseli.
  Claude raw SVG XML yazar → Python UTF-8 base64 encode eder (hallüsinasyon riski = 0).

Değişiklikler:
- Haiku → Sonnet (kalite)
- Claude'dan base64 isteme → raw SVG al, Python encode et (bozuk SVG sorunu çözüldü)
- Brief strateji verisi direkt inject (concept, story, voice yeniden üretilmiyor)
"""

import os
import re
import json
import base64
import colorsys

import anthropic

from generators.brand_brief_contract import normalize_brief, has_feature  # sözleşme

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "brandkit-template.html")


def _lighten_hex(hex_color: str, amount: int = 18) -> str:
    """Hex rengi RGB olarak ayrıştır, her kanalı amount kadar artır (surface türetme)."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r, g, b = min(r + amount, 255), min(g + amount, 255), min(b + amount, 255)
    return f"#{r:02X}{g:02X}{b:02X}"


def _darken_hex(hex_color: str, amount: int = 12) -> str:
    """Hex rengi RGB olarak ayrıştır, her kanalı amount kadar azalt."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r, g, b = max(r - amount, 0), max(g - amount, 0), max(b - amount, 0)
    return f"#{r:02X}{g:02X}{b:02X}"


def _is_dark(hex_color: str) -> bool:
    """Rengin koyu mu açık mı olduğunu luminance ile belirle."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = int(hex_color[0:2], 16) / 255, int(hex_color[2:4], 16) / 255, int(hex_color[4:6], 16) / 255
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return luminance < 0.5

_SVG_SYSTEM = """Sen Bureau Borsche, Sagmeister & Walsh, Pentagram, Collins seviyesinde çalışan bir marka kimlik tasarımcısısın.
Bu ajansların ortak özelliği: her logo bir KAVRAMDAN türer — şekil kütüphanesinden değil.
Sana stüdyo DNA'sı, marka paleti, isim ve konsept verilecek. Tam olarak 5 SVG tasarımı üreteceksin.

ÇIKTI FORMAT — her SVG için bu bloğu kullan:
===SVG:logo_primary===
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 280">
  ... tasarım ...
</svg>
===END===

5 blok: logo_primary, logo_icon, logo_mono, app1, app2
Bloklar arasında başka HİÇBİR ŞEY yazma.

SVG TEKNİK KURALLAR:
- Her açılan tag kapanmalı: <text>KAYA</text> ✓ / <text>KAYA<text> ✗
- Marka adındaki özel karakterler (İ Ş Ğ Ü Ö Ç) direkt UTF-8 olarak yaz — SVG bunu destekler, dönüştürme
- viewBox dışına taşan element yazma
- Font-family SVG içinde belirtme — sistem san-serif yeterli
- Türkçe karakter içeren kelimeleri ASLA letter-by-letter ayrı <text> elementine bölme
  YANLIŞ: <text>Ş</text><text>İ</text><text>P</text> → DOĞRU: <text>ŞİPŞAK</text> (tek element)

KAVRAMSAL TASARIM SÜRECİ — her logo için bu sırayı izle:
1. Bu markanın tek cümlelik özü nedir? (konseptten)
2. Bu özü temsil eden GÖRSEL METAFOR nedir? (şekil değil, anlam)
3. O metaforu forma çevir. Sadece sonra harf/isim ekle.

SWAP TESTİ — geçmeden teslim etme:
"Bu logoyu başka bir markaya koyabilir miyim?" → Eğer evet, tasarımı sil ve baştan başla.
Logo bu markaya ÖZGÜ olmalı. Genel "modern streetwear" logosu değil.

KESİN YASAKLAR (bunları yapan tasarım geçersiz):
- Harf/monogram içinde ya da etrafında dörtgen/daire çerçeve — bu 2010 tarzı, yasaklı
- "metin + yatay çizgi + küçük altyazı" kombinasyonu — template, tasarım değil
- İnce dekoratif çizgi, küçük nokta serpme, rastgele geometri
- Boş zemin üzerine sadece metin
- "BRAND IDENTITY", "EST. 2024" gibi placeholder metinler
- Rastgele geometric accent shape — her şeklin konseptle bağı olsun

STÜDYO DNA UYGULAMASI:
- Collins → Harfin kendi geometrisini kır, grid sistemini görünür kıl, renk bloğu harfi taşısın
- Bureau Borsche → Tipografi BİR grafik obje gibi davransın. Dev, çarpıcı, kültürel punch
- Sagmeister & Walsh → Beklenmedik ölçek ve angle. Metin + form çakışabilir, kural kırılabilir
- Pentagram → Harfin içinde gizli anlam. Negatif boşluk çalıştır. Minimal ama derin
- Landor → Formun kendisi güven verir. Net hiyerarşi, her eleman kendi yerinde
- Wolff Olins → İsim SİSTEM olur. Renk kimliği taşır, harfler modüler sisteme dönüşür

LOGO_ICON için (320x320) — monogram kuralı:
YASAK: harf + dörtgen/daire çerçeve
DOĞRU: Harfin kendi formundan türeyen sembol. Harfi kesen şekil. Harfin içindeki boşluktan doğan form.
Konsept metaforu burada en saf haliyle olsun.

UYGULAMA GÖRSELLERİ — editorial design enerjisi:
- app1 (1080x1080): Tagline'dan en güçlü 2-3 kelime, her kelime ayrı satırda, devasa boyut.
  Arka plan renk bloğu veya diagonal şerit. Kompozisyon poster gibi çalışsın, reklam gibi değil.
- app2 (1080x1080): app1'den tamamen farklı dil. Marka adı büyük stroke-only (fill="none").
  Arka planda konseptten türeyen tekrarlayan element. Renk aksan bloğu köşede.

Her eleman için kendine sor: "Bu element neden burada, ne anlatıyor?" — cevabı yoksa siliyorsun."""


def _ascii_safe(name: str) -> str:
    """
    SVG <text> için marka adını güvenli hale getir.
    Türkçe büyük harfleri ASCII eşdeğerine çevir (İ→I, Ş→S, vb.)
    Böylece font rendering problemi yaşanmaz.
    """
    tr_map = str.maketrans("İĞÜŞÖÇığüşöç", "IGUSSOigusso")
    return name.translate(tr_map)


def _build_svg_prompt(brief: dict) -> str:
    name = brief.get("brand_name", "BRAND")
    # SVG UTF-8'i destekler — orijinal Türkçe ismi kullan, dönüştürme
    # _ascii_safe sadece font-size hesabı için (karakter sayısı aynı)
    name_safe = name  # display için orijinal isim
    primary = brief.get("primary_color", "#C9A25A")
    secondary = brief.get("secondary_color", "#8B8B7A")
    accent2 = brief.get("accent_color") or secondary
    energy = str(brief.get("energy", "cinematic")).lower()

    if "playful" in energy:
        bg = brief.get("bg_color", "#FFFFFF")
        if not _is_dark(bg):
            text = "#1A1A1A"
        else:
            text = "#F5F0E8"
    else:
        bg = brief.get("bg_color", "#0F0D0C")
        text = "#F2EDE4" if _is_dark(bg) else "#1A1A1A"

    tagline = brief.get("tagline", "")
    concept = brief.get("concept_statement", "")
    logo_concept = brief.get("logo_concept", "")
    logo_icon_brief = brief.get("logo_icon_svg_brief", "")  # Direkt SVG çizim talimatı
    visual_language = brief.get("visual_language", "")

    # Font-size hesabı: viewBox genişliği / (karakter sayısı × 0.65) = max font-size
    # Türkçe karakterler (İ Ş Ğ vb.) birer karakter sayılır — len() doğru çalışır
    name_len = max(len(name), 1)
    max_font_logo = min(90, int(480 / (name_len * 0.65)))  # logo_primary: ~480px kullanılabilir genişlik
    max_font_app2 = min(200, int(860 / (name_len * 0.65)))  # app2 stroke-only: 1080px - margin

    tagline_words = [w for w in tagline.split() if w][:4]
    max_tagline_word_len = max((len(w) for w in tagline_words), default=8)
    max_font_app1 = min(160, int(900 / (max_tagline_word_len * 0.65)))  # app1: 1080px - margin, 160px hard cap (kısa kelimeler taşmasın)

    # Studio DNA inject — hangi stüdyo atandıysa o stüdyonun tasarım dilini ver
    studio_dna = brief.get("studio_dna", {})
    studio_label = studio_dna.get("label", "Pentagram")
    studio_style = studio_dna.get("style", "")
    studio_sector = studio_dna.get("sector", "")

    # Stüdyo bazlı logo yönergesi
    studio_logo_guide = {
        "Collins":          "Kesin geometri + güçlü renk sistemi. Wordmark: tam dolgu renk bloğu içinde büyük metin. İkon: grid-based, modüler.",
        "Bureau Borsche":   "Kültürel referans + bold tipografi baskınlığı. Büyük/cesur yazı, grafik punch. İkon: harfi taşıyan güçlü şekil.",
        "Sagmeister&Walsh": "Kural kıran form + ekspresif ölçek. Metin ve şekil çakışabilir. İkon: sürpriz geometri, beklenmedik negatif alan.",
        "Pentagram":        "Anlam yüklü soyutlama + zariflik. Minimal ama derin. İkon: harften türeyen özgün form, net sembol.",
        "Landor":           "Güven veren form + net hiyerarşi. Dengeli oran, temiz duruş. İkon: bold monogram, kurumsal güç.",
        "Wolff Olins":      "Sistemik wordmark + modüler yapı. Güçlü renk kimliği, sade ama güçlü. İkon: renk odaklı form.",
        "Base Design":      "Minimal + yapısal kesinlik. Tipografi odaklı, fazlalık yok. İkon: negatif alan kullanan form.",
    }.get(studio_label, "Özgün ve marka DNA'sına sadık. Cüretkâr ama işlevsel.")

    return f"""MARKA: {name_safe}
STÜDYO DNA: {studio_label} ({studio_sector})
STÜDYO STİLİ: {studio_style}
LOGO YÖNERGESİ: {studio_logo_guide}
ENERJİ: {energy}
TAGLINE: {tagline}
KONSEPT: {concept}
LOGO KONSEPT: {logo_concept}
GÖRSEL DİL: {visual_language}

RENKLER:
  Zemin: {bg}
  Metin: {text}
  Ana vurgu: {primary}
  İkincil: {secondary}
  Vurgu 2: {accent2}

5 SVG tasarla — stüdyo DNA'sını her tasarımda hissettir:

===SVG:logo_primary===
viewBox="0 0 800 280". Arka plan: {bg} (ZORUNLU — değiştirme).
Marka adı: "{name_safe}" — Türkçe karakterleri OLDUĞU GİBİ yaz (İ, Ş, Ğ, Ü, Ö, Ç desteklenir).
Tüm ismi TEK <text> elementinde yaz. ASLA harf-harf bölme.
FONT-SIZE SINIRI: {name_len} karakter → maksimum {max_font_logo}px. Bunu AŞ MA.
Metin rengi {text}. Accent {primary}.
KAVRAMSAL ANCHOR: Logo konseptini ({logo_concept}) görsel forma çevir — şekil değil anlam.
{studio_logo_guide}
Wordmark: "metin + yatay çizgi" kombinasyonu YASAK. Konseptten türeyen form şart.
===END===

===SVG:logo_icon===
viewBox="0 0 320 320". Arka plan: {bg}. Ana renk: {primary}.

DOĞRUDAN UYGULA — bu ikonun çizim talimatı:
{logo_icon_brief}

MUTLAK YASAKLAR (bunları yapan SVG'yi sil, yeniden çiz):
✗ Harfin YANINA / ÜSTÜNE / ETRAFINA şekil eklemek — çizgi, ok, daire, nokta eklenti = yasak
✗ Harf + çerçeve (kare veya daire içinde harf)
✗ Harfe diagonal çizgi yapıştırmak (diagonal/slash harfin parçası değilse yasak)
✗ "E" veya "F" benzeri ASCII harfi + ek renk bloğu — FedEx taklidi değil özgün form isteniyor

DOĞRU YAKLAŞIMLAR (birini seç):
✓ Harfin bir bölümünü KES → kesik boşluk anlam taşısın (Apple ısırığı modeli)
✓ İki harfi BİRLEŞTİR → harflerin birleşiminden yeni form doğsun
✓ Harfin iç boşluğunu (counter) şekle dönüştür
✓ Harfin kendisini tanınmaz hale getirip başka bir nesneye çevir

FedEx neden çalışır: ok harflere EKLENMEDİ — E ve x arasındaki DOĞAL negatif boşluktan doğdu.
Senin de eklemen değil, var olanı keşfetmen lazım.

SWAP TESTİ (zorunlu, geçmeden bitirme): Bu ikon başka markaya yapıştırılabilir mi? → Evet ise sil, baştan yap.
===END===

===SVG:logo_mono===
viewBox="0 0 800 280". logo_primary tek renkli versiyon.
SADECE {text} rengi. Zemin şeffaf (background rect YOK).
===END===

===SVG:app1===
viewBox="0 0 1080 1080". Zemin {bg}.
Tagline'dan 2-3 kelime BÜYÜK, her kelime ayrı <text> satırında: "{tagline[:35]}"
FONT-SIZE SINIRI: En uzun kelime {max_tagline_word_len} karakter → maksimum {max_font_app1}px. Bunu AŞMA.
font-weight="900", {text} rengi. Her kelime için y değerini kademeli artır (250, 250+font-size, ...).
Alt kısımda "{name_safe}" {primary} rengiyle, daha küçük (font-size 60-80).
Güçlü renk bloğu veya diagonal şerit — {primary} veya {secondary} kullan.
===END===

===SVG:app2===
viewBox="0 0 1080 1080". app1'den tamamen farklı kompozisyon.
"{name_safe}" büyük stroke-only (fill="none", stroke="{primary}", stroke-width="10", font-size {max_font_app2}px MAX).
FONT-SIZE SINIRI: "{name_safe}" = {name_len} karakter → maksimum {max_font_app2}px. Bunu AŞMA.
Arka planda tekrarlayan geometrik grid veya pattern. Renk aksan bloğu.
Alt veya üst köşede konsept: "{concept[:50]}"
===END==="""


def _force_svg_background(svg_str: str, bg_color: str) -> str:
    """
    SVG'nin arka planını bg_color ile garantile.
    Sonnet ne renk seçerse seçsin, logo zemini her zaman sayfa bg'siyle eşleşir.
    1) İlk <rect> fill'ini bg_color'a set et (varsa)
    2) Yoksa: <svg> açılışından hemen sonra explicit background rect ekle
    """
    vb_match = re.search(r'viewBox=["\'](\S+)["\']', svg_str)
    if not vb_match:
        return svg_str

    parts = vb_match.group(1).split()
    if len(parts) == 4:
        _, _, w, h = parts
    else:
        return svg_str

    bg_rect = f'<rect width="{w}" height="{h}" fill="{bg_color}"/>'

    # Mevcut ilk rect varsa fill'ini değiştir
    first_rect = re.search(r'<rect([^/]*/?>)', svg_str)
    if first_rect:
        old = first_rect.group(0)
        new = re.sub(r'fill="[^"]*"', f'fill="{bg_color}"', old)
        if 'fill=' not in new:
            new = new.replace('/>', f' fill="{bg_color}"/>')
        svg_str = svg_str.replace(old, new, 1)
    else:
        # Hiç rect yok — svg tag'ından sonra ekle
        svg_str = re.sub(r'(<svg[^>]*>)', r'\1\n  ' + bg_rect, svg_str, count=1)

    return svg_str


def _extract_svgs(raw: str, bg_color: str = "#0F0D0C") -> dict:
    """
    Claude çıktısından SVG bloklarını çıkar, UTF-8 base64 encode et.
    logo_primary ve logo_icon için arka planı Python tarafında bg_color'a zorla —
    Sonnet'in renk seçimine bakılmaksızın sayfa zeminiyle her zaman eşleşir.
    """
    pattern = r'===SVG:(\w+)===([\s\S]*?)===END==='
    svgs = {}
    # logo_mono şeffaf kalmalı — diğerleri zorlanır
    force_bg_keys = {"logo_primary", "logo_icon", "app1", "app2"}

    for m in re.finditer(pattern, raw):
        key = m.group(1).strip()
        svg_raw = m.group(2).strip()
        if svg_raw.startswith('<svg'):
            if key in force_bg_keys:
                svg_raw = _force_svg_background(svg_raw, bg_color)
            b64 = base64.b64encode(svg_raw.encode('utf-8')).decode('ascii')
            svgs[key] = f"data:image/svg+xml;base64,{b64}"
        else:
            svgs[key] = ""
    return svgs


def generate_html_preview(brief: dict) -> tuple:
    """
    Brief JSON → window.BRAND config → tam HTML string.
    Döner: (html_str, token_usage_dict)
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Sözleşme: brief'i normalize et — eksik alanlar default değeriyle gelir
    brief = normalize_brief(brief)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # ── Aşama 2: Sonnet'ten raw SVG al ────────────────────────────────────────
    svg_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=_SVG_SYSTEM,
        messages=[{"role": "user", "content": _build_svg_prompt(brief)}],
    )
    svg_raw = svg_response.content[0].text
    svgs = _extract_svgs(svg_raw, bg_color=brief["bg_color"])

    html_token_usage = {
        "input_tokens": svg_response.usage.input_tokens,
        "output_tokens": svg_response.usage.output_tokens,
    }

    # ── Aşama 1: Python ile window.BRAND doldur ────────────────────────────────
    # normalize_brief() garantili — .get() + default'a gerek yok
    energy    = brief["energy"]          # "cinematic" | "playful"
    primary   = brief["primary_color"]
    secondary = brief["secondary_color"]
    accent2   = brief["accent_color"]   # normalize_brief → secondary ile aynı yapıldı

    bg = brief["bg_color"]
    dark_bg = _is_dark(bg)

    if energy == "playful":
        if dark_bg:
            surface = _lighten_hex(bg, 15)
            text, muted = "#F5F0E8", "#A89F94"
        else:
            surface = _darken_hex(bg, 12)
            text, muted = "#1A1A1A", "#666666"
    else:
        # cinematic — koyu zemin bekleniyor ama brief'ten geldi
        if dark_bg:
            surface = _lighten_hex(bg, 12)
            text, muted = "#F2EDE4", "#7A756C"
        else:
            surface = _darken_hex(bg, 12)
            text, muted = "#1A1A1A", "#555555"

    font_display = brief["font_display"]
    font_body    = brief["font_body"]

    def _slug(n): return n.strip().replace(" ", "+")
    gf_url = (
        f"https://fonts.googleapis.com/css2?"
        f"family={_slug(font_display)}:wght@400;600;700"
        f"&family={_slug(font_body)}:wght@400;500;600"
        f"&display=swap"
    )

    brand_name = brief["brand_name"]
    tagline    = brief["tagline"]

    # Strateji — brief'ten direkt al (brand_brief.py Sonnet'iyle üretildi)
    concept_statement = brief["concept_statement"]
    brand_story       = brief["brand_story"]
    brand_story_prev  = brief["brand_story_preview"]
    brand_story_line2 = brief["brand_story_line2"]
    voice_we          = brief["voice_we"]
    voice_we_not      = brief["voice_we_not"]
    mood_words        = brief["mood_words"]

    # Story body: ilk iki paragraf
    if brand_story_prev:
        story_body_0 = brand_story_prev
    elif brand_story and '\n\n' in brand_story:
        story_body_0 = brand_story.split('\n\n')[0]
    else:
        story_body_0 = brand_story[:300] if brand_story else ""

    if brand_story_line2:
        story_body_1 = brand_story_line2
    elif brand_story and '\n\n' in brand_story:
        parts = brand_story.split('\n\n')
        story_body_1 = parts[1] if len(parts) > 1 else ""
    else:
        story_body_1 = ""

    # Story heading — brief'te yoksa tagline'dan türet
    story_heading = brief.get("story_heading", tagline)

    # Concept body
    concept_body = brief.get("concept_body", story_body_0[:200] if story_body_0 else "")

    # Palette isimleri — mood_words'den al veya varsayılan
    default_names = ["Ana Vurgu", "İkincil", "Vurgu", "Zemin", "Metin"]
    def _pname(i):
        return mood_words[i] if i < len(mood_words) else default_names[i]

    palette = [
        {"name": _pname(0), "hex": primary,    "role": "Ana vurgu"},
        {"name": _pname(1), "hex": secondary,  "role": "İkincil"},
        {"name": _pname(2), "hex": accent2,    "role": "Vurgu 2"},
        {"name": _pname(3), "hex": bg,         "role": "Zemin"},
        {"name": _pname(4), "hex": text,       "role": "Metin"},
    ]

    # Voice traits: mood_words'den al
    voice_traits = (mood_words + ["", "", ""])[:3]

    # ── window.BRAND JSON string ───────────────────────────────────────────────
    brand_config = (
        "window.BRAND = "
        + json.dumps({
            "name":    brand_name,
            "tagline": tagline,
            "domain":  "",
            "energy":  energy,
            "colors": {
                "bg":      bg,
                "surface": surface,
                "text":    text,
                "muted":   muted,
                "accent":  primary,
                "accent2": accent2,
            },
            "palette": palette,
            "type": {
                "googleFonts": gf_url,
                "headingFont": f"'{font_display}', sans-serif",
                "bodyFont":    f"'{font_body}', sans-serif",
                "headingName": font_display,
                "bodyName":    font_body,
                "headingNote": "Display / Başlık",
                "bodyNote":    "Metin / Arayüz",
                "sampleWord":  "Aa",
            },
            "logo": {
                "primary":    svgs.get("logo_primary", ""),
                "icon":       svgs.get("logo_icon", ""),
                "mono":       svgs.get("logo_mono", ""),
                "inverse":    "",
                "clearSpace": "Logo etrafında minimum 40px boşluk korunmalıdır.",
                "misuse": [
                    "Germe veya oranı bozma",
                    "Onaysız renk değiştirme",
                    "Gölge veya efekt ekleme",
                    "Düşük kontrastlı zemine yerleştirme",
                ],
            },
            "story": {
                "eyebrow": "Hikaye",
                "heading": story_heading,
                "body":    [story_body_0, story_body_1],
            },
            "concept": {
                "eyebrow":   "Konsept",
                "statement": concept_statement,
                "body":      concept_body,
            },
            "voice": {
                "traits": voice_traits,
                "we":     voice_we,
                "weNot":  voice_we_not,
            },
            "applications": [
                {"img": svgs.get("app1", ""), "caption": "Sosyal Medya"},
                {"img": svgs.get("app2", ""), "caption": "İçerik Şablonu"},
            ],
            "credit": "Üretildi: BrandGen by Windy Venture Capital",
        }, ensure_ascii=False, indent=2)
        + ";"
    )

    # ── Template'e inject ──────────────────────────────────────────────────────
    script_pattern = r'(<script id="brand-config">)([\s\S]*?)(</script>)'
    new_html = re.sub(
        script_pattern,
        lambda m: m.group(1) + "\n" + brand_config + "\n" + m.group(3),
        template,
        count=1,
    )

    if new_html == template:
        old_pattern = r'window\.BRAND\s*=\s*\{[\s\S]*?\};'
        new_html = re.sub(old_pattern, brand_config, template, count=1)

    # Title
    new_html = new_html.replace(
        "<title>Brand — {{title}}</title>",
        f"<title>Brand — {brand_name}</title>",
    )
    new_html = new_html.replace("Brand — {{title}}", f"Brand — {brand_name}")

    # Watermark
    if energy == "playful":
        wm_color, wm_stripe = "rgba(0,0,0,0.09)", "rgba(0,0,0,0.03)"
    else:
        wm_color, wm_stripe = "rgba(255,255,255,0.07)", "rgba(255,255,255,0.025)"

    watermark_css = f"""
<style id="brandgen-watermark">
.brandgen-wm {{
  position: fixed; inset: 0; z-index: 9999; pointer-events: none;
}}
.brandgen-wm::before {{
  content: "BRANDGEN PREVIEW · BRANDGEN PREVIEW · BRANDGEN PREVIEW";
  position: absolute; font-size: 16px; font-weight: 700;
  letter-spacing: 0.3em; color: {wm_color};
  transform: rotate(-35deg); white-space: nowrap;
  font-family: monospace;
  background: repeating-linear-gradient(
    -35deg, transparent, transparent 60px,
    {wm_stripe} 60px, {wm_stripe} 61px
  );
  width: 200%; height: 200%; left: -50%; top: -50%;
  display: flex; align-items: center; justify-content: center;
  line-height: 4em;
}}
</style>
<div class="brandgen-wm"></div>
"""
    new_html = new_html.replace("</body>", watermark_css + "</body>")

    return new_html, html_token_usage


def upload_html_preview(job_id: str, brief: dict) -> str:
    """HTML üret → Supabase Storage'a yükle → public URL döner. (opsiyonel fallback)"""
    from utils.supabase_client import get_db

    html_content, _ = generate_html_preview(brief)
    db = get_db()
    path = f"previews/{job_id}/brand-kit.html"
    db.storage.from_("brandgen").upload(
        path,
        html_content.encode("utf-8"),
        {"content-type": "text/html; charset=utf-8", "upsert": "true"},
    )
    return db.storage.from_("brandgen").get_public_url(path)
