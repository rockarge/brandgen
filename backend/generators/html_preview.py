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

_SVG_SYSTEM = """Sen bir marka kimlik SVG tasarımcısısın.
Sana marka paleti, isim ve konsept verilecek. Tam olarak 5 SVG tasarımı üreteceksin.

ÇIKTI FORMAT — her SVG için bu bloğu kullan:
===SVG:logo_primary===
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 280">
  ... tasarım ...
</svg>
===END===

5 blok şunlar olmalı: logo_primary, logo_icon, logo_mono, app1, app2
Bloklar arasında başka HİÇBİR ŞEY yazma — sadece bloklar.

SVG KALİTE KURALLARI:
- Her açılan tag kapanmalı: <text>KAYA</text> ✓ / <text>KAYA<text> ✗
- Türkçe karakterler (Ü, Ğ, Ş, İ, Ö, Ç) direkt kullanılabilir — base64 YOK
- viewBox dışına taşan element yazma
- font-family: 'Arial Black', 'Helvetica Neue', Arial, sans-serif

LOGO KALİTESİ:
- Geometrik detaylarla ayırt edici, marka karakterine özgü
- Standart/sıradan "metin + çizgi" kombinasyonu yerine özgün kompozisyon
- İkon logosu (logo_icon): baş harf(ler) + çerçeve/form — monogram sistemi"""


def _build_svg_prompt(brief: dict) -> str:
    name = brief.get("brand_name", "BRAND")
    primary = brief.get("primary_color", "#C9A25A")
    secondary = brief.get("secondary_color", "#8B8B7A")
    accent2 = brief.get("accent_color") or secondary
    energy = str(brief.get("energy", "cinematic")).lower()

    if "playful" in energy:
        bg = brief.get("bg_color", "#FFFFFF")
        # playful için bg açık tonsa beyaz/açık metin mantıksız — kontrol et
        if not _is_dark(bg):
            text = "#1A1A1A"
        else:
            text = "#F5F0E8"
    else:
        bg = brief.get("bg_color", "#0F0D0C")
        text = "#F2EDE4" if _is_dark(bg) else "#1A1A1A"

    tagline = brief.get("tagline", "")
    concept = brief.get("concept_statement", "")
    font_display = brief.get("font_display", "Space Grotesk")
    logo_concept = brief.get("logo_concept", "")
    visual_language = brief.get("visual_language", "")

    return f"""MARKA: {name}
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

Font: {font_display}

5 SVG tasarla:

===SVG:logo_primary===
viewBox="0 0 800 280". Zemin {bg}. Marka adı "{name}" büyük/bold,
negatif letter-spacing (-0.03 ile -0.06 arası). Metin rengi {text}.
Accent {primary} ile 1-2 özgün geometrik detay (ince çizgi, köşe aksanı, küçük form).
Logo konseptine uygun: {logo_concept or "minimal ve güçlü"}
===END===

===SVG:logo_icon===
viewBox="0 0 320 320". "{name[0]}" baş harfi veya kısaltma.
Zemin {bg}. Geometrik çerçeve veya form, accent={primary}.
Metin {text}. Monogram sistemi — özgün, ayırt edici.
===END===

===SVG:logo_mono===
viewBox="0 0 800 280". logo_primary'nin tek renkli versiyonu.
SADECE {text} rengi. Zemin şeffaf (background rect YAZMA).
===END===

===SVG:app1===
viewBox="0 0 1080 1080". Instagram post. Zemin {bg}.
Büyük statement metin (tagline'dan 3-5 kelime: "{tagline[:40]}").
Alt kısımda marka adı "{name}" accent={primary} rengiyle.
Güçlü geometri — dolu blok veya diagonal şerit.
===END===

===SVG:app2===
viewBox="0 0 1080 1080". Farklı kompozisyon. Grid/pattern zemin.
"{name}" büyük outline/transparent metin. Accent renk bloğu.
Farklı hiyerarşi — konsept: "{concept[:60]}"
===END==="""


def _extract_svgs(raw: str) -> dict:
    """Claude çıktısından SVG bloklarını çıkar, UTF-8 base64 encode et (Python yapıyor)."""
    pattern = r'===SVG:(\w+)===([\s\S]*?)===END==='
    svgs = {}
    for m in re.finditer(pattern, raw):
        key = m.group(1).strip()
        svg_raw = m.group(2).strip()
        if svg_raw.startswith('<svg'):
            # Python UTF-8 base64 — hallüsinasyon yok, Türkçe karakterler sağlam
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
    svgs = _extract_svgs(svg_raw)

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
