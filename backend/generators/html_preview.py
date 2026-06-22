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

BrandGen HTML Kit v3 — fal.ai Görsel Pipeline

Pipeline:
  1. brand_brief.py (Sonnet) → hikaye, konsept, ses/ton üretir (önceki aşamada oldu)
  2. select_logo_mono_png()  → PIL ile beyaz wordmark (logo_mono)
  3. generate_all_images()   → fal.ai paralel:
       logo_primary + logo_tipo + logo_icon → Recraft v3 (vector_illustration)
       app1 + app2                         → Flux Schnell (editorial fotoğraf, JPEG)
  4. window.BRAND JSON inject → brandkit-template.html

Maliyet: ~$0.13/üretim (Recraft ×3 + Flux ×2)
"""

import os
import re
import json
import base64
import colorsys

from generators.brand_brief_contract import normalize_brief, has_feature  # sözleşme
from generators.logo_generator import select_logo_mono_png
from generators.image_generator import generate_all_images  # fal.ai: logo + app görselleri

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


def generate_html_preview(brief: dict) -> tuple:
    """
    Brief JSON → window.BRAND config → tam HTML string.
    Döner: (html_str, token_usage_dict)
    """
    # Sözleşme: brief'i normalize et — eksik alanlar default değeriyle gelir
    brief = normalize_brief(brief)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # ── Görsel üretim ─────────────────────────────────────────────────────────
    # logo_mono: PIL wordmark (beyaz, şeffaf zemin)
    svgs = {
        "logo_mono": select_logo_mono_png(brief),
    }

    # fal.ai: logo_primary, logo_tipo, logo_icon (Recraft v3), app1, app2 (Flux JPEG)
    fal_images = generate_all_images(brief)
    svgs["logo_tipo"] = fal_images.get("logo_tipo", "")
    svgs["app1"] = fal_images.get("app1", "")
    svgs["app2"] = fal_images.get("app2", "")

    html_token_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
    }

    # ── Renk ve tipografi ─────────────────────────────────────────────────────
    energy    = brief["energy"]
    primary   = brief["primary_color"]
    secondary = brief["secondary_color"]
    accent2   = brief["accent_color"]

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

    concept_statement = brief["concept_statement"]
    brand_story       = brief["brand_story"]
    brand_story_prev  = brief["brand_story_preview"]
    brand_story_line2 = brief["brand_story_line2"]
    voice_we          = brief["voice_we"]
    voice_we_not      = brief["voice_we_not"]
    mood_words        = brief["mood_words"]

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

    story_heading = brief.get("story_heading", tagline)
    concept_body = brief.get("concept_body", story_body_0[:200] if story_body_0 else "")

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

    voice_traits = (mood_words + ["", "", ""])[:3]

    # ── window.BRAND JSON ─────────────────────────────────────────────────────
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
                "tipo":       svgs.get("logo_tipo", ""),
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

    # ── Template'e inject ─────────────────────────────────────────────────────
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
