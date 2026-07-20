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

BrandGen HTML Kit v3 — PIL Wordmark + fal.ai Görsel Pipeline

Pipeline (2 Tem 2026 audit sonrası güncellendi — bkz. brandgen-gorsel-audit-2tem2026.md):
  1. brand_brief.py (Sonnet) → hikaye, konsept, ses/ton üretir (önceki aşamada oldu)
  2. select_logo_primary_png() → PIL, brief'in template/stüdyo/energy kararına göre ANA logo
  3. select_logo_mono_png()    → PIL ile tek renk, GERÇEK şeffaf zemin (RGBA) wordmark
  3b. select_logo_tipo_png()   → PIL ile bg_color dolu zemin + tracked wordmark + accent
                                  nokta (3 Tem 2026: artık mono'nun kopyası DEĞİL, ayrı
                                  fonksiyon — bkz. logo_generator.py "TİPO LOGO" bölümü)
  4. generate_all_images()     → fal.ai paralel:
       logo_icon    → Recraft v3 (vector_illustration) — soyut geometrik mark
       app1 + app2  → Flux Schnell (editorial fotoğraf, JPEG)
  5. window.BRAND JSON inject → brandkit-template.html

  NOT: logo_primary/logo_mono/logo_tipo artık diffusion'a (Recraft) gitmiyor — PIL
  render marka adını her zaman doğru yazar, diffusion'ın Türkçe karakter
  hallüsinasyonu (audit B1) riskini tamamen ortadan kaldırır.

Maliyet: ~$0.05/üretim (Recraft ×1 + Flux ×2) — önceki ~$0.13'ten düştü.
"""
# Python 3.9 uyumu (Mac'te lokal QA koşabilsin): 3.10+ tip
# annotation'larini (dict | None) string'e cevirir, runtime degismez.
from __future__ import annotations


import os
import re
import json
import base64
import colorsys

from generators.brand_brief_contract import normalize_brief, has_feature  # sözleşme
from generators.logo_generator import select_logo_mono_png, select_logo_primary_png, select_logo_tipo_png
from generators.logo_generator import _brand_upper   # dil bilinçli büyük harf
from generators.image_generator import generate_all_images  # fal.ai: icon + app görselleri

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
    # logo_primary + logo_mono/tipo: PIL render — marka adı her zaman doğru yazılır,
    # diffusion'a hiç gitmez (2 Tem 2026 audit fix, bkz. dosya başlığı).
    studio_label = brief.get("studio_dna", {}).get("label", "")
    svgs = {
        "logo_primary": select_logo_primary_png(brief, studio_label=studio_label),
        # studio_label buraya da geçiyor (3 Tem 2026) — ANA, MONO ve TİPO aynı
        # markaya özgü fontu (tpl_X.ttf) kullansın, hiçbiri ayrı fonta düşmesin.
        "logo_mono":    select_logo_mono_png(brief, studio_label=studio_label),
        # 3 Tem 2026: logo_tipo artık logo_mono'nun kopyası DEĞİL — önceden burada
        # `svgs["logo_tipo"] = svgs["logo_mono"]` vardı, yani preview'da "TİPO" diye
        # gösterilen görsel piksel piksel MONO ile aynıydı (bkz. logo_generator.py
        # select_logo_tipo_png docstring'i — yapısal fark: RGB dolu zemin + primary_color
        # wordmark + ortalı/tracking + accent nokta, hepsi MONO'da yok).
        "logo_tipo":    select_logo_tipo_png(brief, studio_label=studio_label),
    }

    # fal.ai: logo_icon (Recraft v3 — soyut geometrik, exact-text istemiyor),
    # app1, app2 (Flux JPEG) + hero_dark/hero_light (Flux 9:16 — Görev 2B)
    fal_images = generate_all_images(brief, studio_label=studio_label)
    svgs["logo_icon"] = fal_images.get("logo_icon", "")

    # ── SLOT YENİDEN DÜZENİ (Görev 2E, 20 Tem 2026 — Serhat kararı) ──────────
    # Serhat: "Tipo = Ana'nın şu anki hali olsun (o güzel duruyordu), Ana ise
    # aile sistemli mark + altında wordmark olsun."
    #
    #   Ana   = AI mark + wordmark lockup      (YENİ — lockup_generator)
    #   Tipo  = eski Ana (select_logo_primary_png, template lockup'lı)
    #   İkon  = markın tek başına hali (AYNI SVG — ikinci AI çağrısı YOK)
    #   Mono / Ters = değişmedi
    #
    # Eski tipo (dolu zemin + accent nokta) DÜŞTÜ; yerini daha karakterli olan
    # aldı. Lockup kurulamazsa (mark boş/bozuk) ana slot eski PIL logosunda
    # kalır → üretim asla kırılmaz.
    from generators.lockup_generator import build_primary_lockup
    _old_primary = svgs["logo_primary"]
    _lockup = build_primary_lockup(brief, svgs["logo_icon"], studio_label=studio_label)
    if _lockup:
        svgs["logo_primary"] = _lockup
        svgs["logo_tipo"] = _old_primary
    else:
        print("[html_preview] lockup kurulamadı → ana logo eski PIL çıktısında kaldı")
    svgs["app1"] = fal_images.get("app1", "")
    svgs["app2"] = fal_images.get("app2", "")

    # Görev 2B (20 Tem 2026): genişletilmiş PIL asset'leri — TEK KAYNAK
    # (asset_generator.py; finalize_job da AYNI fonksiyonu çağırır — "Preview ≠
    # İndirilen" bug ailesi kapalı kalsın).
    from generators.asset_generator import generate_extended_pil_assets
    ext = generate_extended_pil_assets(
        brief, studio_label=studio_label, mono_uri=svgs["logo_mono"]
    )

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

    # ── FONT TUTARLILIĞI (20 Tem 2026, Serhat bulgusu — canlı Biricik testi) ──
    # Sorun: kit sayfası Sonnet'in seçtiği Google fontla (örn. Playfair), logo ise
    # template'in curated fontuyla (örn. Bodoni Moda) yazılıyordu — kitin "Yazı
    # Sistemi" bölümü logoyla çelişiyordu. Karar: display font LOGO FONTUNA kilitli
    # (5 curated fontun 5'i de Google Fonts'ta var, $0). Body font Sonnet'ten kalır.
    # Font sistemi v3 (20 Tem 2026) ile senkron — her template kendi fontu:
    _TPL_GOOGLE_DISPLAY = {
        "A": "Anton", "B": "Bodoni Moda", "C": "Unbounded",
        "D": "Archivo Black", "E": "Space Grotesk",
        "F": "Bungee", "G": "DM Serif Display", "H": "Alfa Slab One",
        "I": "Libre Franklin", "J": "Fredoka",
    }
    # 20 Tem 2026 (Pepito bulgusu): font dosyası alias'a düşerse (tpl_X.ttf
    # diskte yoksa) logo BAŞKA fontla basılır. Sayfa fontunu template koduna
    # değil, GERÇEKTEN KULLANILAN font dosyasına bağla — yoksa "sayfa fontu
    # logo fontuyla çelişiyor" bug'ı alias yoluyla geri gelir.
    try:
        from generators.logo_generator import _resolve_template as _rt
        from generators.logo_generator import _tpl_font_name as _tfn
        _tpl = _rt(brief, studio_label)
        _font_tpl = _tfn(_tpl).replace("tpl_", "") if _tpl else ""
    except Exception:
        _tpl, _font_tpl = "", ""
    font_display = _TPL_GOOGLE_DISPLAY.get(_font_tpl) or brief["font_display"]
    font_body    = brief["font_body"]

    def _slug(n): return n.strip().replace(" ", "+")
    # Display font AĞIRLIKSIZ istenir (v3 fix): Bungee/Alfa Slab One gibi tek
    # ağırlıklı ailelerde ":wght@400;600;700" css2'de hata verir → font hiç
    # yüklenmezdi. Ağırlıksız istek her ailede güvenli; başlık 600'ü tarayıcı
    # gerekirse sentetik kalınlaştırır.
    gf_url = (
        f"https://fonts.googleapis.com/css2?"
        f"family={_slug(font_display)}"
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
            # Belge şeridi (docbar) için DİL BİLİNÇLİ büyük harf. CSS'in
            # text-transform:uppercase'i yabancı kelimeyi ayırt edemiyor
            # ("VIRA DIGITAL" → "VİRA DİGİTAL" basıyordu). 20 Tem canlı bulgu.
            "nameUpper": _brand_upper(brief),
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
                # Görev 2B: reversed — asset_generator'ın polarite-ters MONO'su
                # (finalize_job ZIP'ine giren logo_reversed ile AYNI kaynak)
                "reversed":   ext.get("logo_reversed", ""),
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
                {"img": svgs.get("app1", ""), "caption": "Instagram Post A"},
                {"img": svgs.get("app2", ""), "caption": "Instagram Post B"},
            ],
            # Görev 2B (20 Tem 2026): genişletilmiş asset seti — WVC brand-kit
            # paritesi (kartvizit, profil, highlight, banner, mobil hero).
            "assets": {
                "cardFront":     ext.get("card_front", ""),
                "cardBack":      ext.get("card_back", ""),
                "profileDark":   ext.get("profile_dark", ""),
                "profileLight":  ext.get("profile_light", ""),
                "highlights": [
                    {"label": lbl, "img": ext.get(f"highlight_{i}", "")}
                    for i, lbl in enumerate(ext.get("_highlight_labels", []), start=1)
                ],
                "bannerLinkedin": ext.get("banner_linkedin", ""),
                "bannerTwitter":  ext.get("banner_twitter", ""),
                "heroMobileDark":  fal_images.get("hero_dark", ""),
                "heroMobileLight": fal_images.get("hero_light", ""),
            },
            # Görev 2C (20 Tem 2026): kapanış "Bu kitte olmayan" listesi.
            # Sonnet sektöre özgü 3 madde üretir; boşsa template kendi
            # varsayılan listesine düşer (geriye dönük güvenli).
            "notIncluded": [x for x in brief.get("not_included", []) if str(x).strip()],
            # 20 Tem 2026 — Serhat kararı: müşteri kitinde WVC adı geçmez (proje
            # bağımsızlığı; BrandGen kendi markası). Kredi sadece ürünü söyler.
            "credit": "Üretildi: BrandGen · brandgen.no1a.com",
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
