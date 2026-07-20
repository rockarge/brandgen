"""
BrandGen — BrandBriefContract

brand_brief.py (üretici) ile html_preview.py (tüketici) arasındaki sözleşme.

KULLANIM:
    from generators.brand_brief_contract import normalize_brief

    # brand_brief.py çıktısını her zaman normalize et:
    brief, tokens = generate_brand_brief(prompt, tier)
    brief = normalize_brief(brief)

    # html_preview.py içinde artık .get() gerekmez — tüm alanlar garantili:
    brand_name = brief["brand_name"]   # KeyError yok
    voice_we   = brief["voice_we"]     # boş liste dönerse de patlama yok

KURAL:
    Yeni alan eklenince:
    1. DEFAULTS sözlüğüne ekle (default değerle)
    2. _knowledge/brandgen-mimari.md §5 window.BRAND şemasını güncelle
    3. html_preview.py'de ilgili yeri .get() yerine doğrudan kullan
"""
# Python 3.9 uyumu (Mac'te lokal QA koşabilsin): 3.10+ tip
# annotation'larini (dict | None) string'e cevirir, runtime degismez.
from __future__ import annotations


from typing import Any

# ── Tüm alanlar ve default değerleri ──────────────────────────────────────────
DEFAULTS: dict[str, Any] = {
    # Kimlik
    "brand_name":           "BRAND",
    "tagline":              "",
    "domain":               "",
    "energy":               "cinematic",   # "cinematic" | "playful"

    # Renkler
    "primary_color":        "#C9A25A",
    "secondary_color":      "#8B8B7A",
    "accent_color":         None,          # None → secondary ile aynı
    "bg_color":             "#0F0D0C",     # Sektöre özgü zemin — ASLA saf siyah/beyaz

    # Tipografi
    "font_display":         "Space Grotesk",
    "font_body":            "Inter",
    "font_meta":            "DM Mono",

    # Logo
    "logo_concept":         "",
    "logo_versions":        [],

    # fal.ai image prompts — Sonnet tarafından üretilen, İngilizce
    # Boşsa image_generator.py fallback prompt kullanır
    # NOT (2 Tem 2026 audit): fal_logo_prompt artık KULLANILMIYOR — logo_primary
    # diffusion'dan çıkarıldı (PIL render'a geçti), alan geriye dönük uyumluluk
    # için sözleşmede duruyor ama image_generator.py bunu okumuyor.
    "fal_logo_prompt":      "",   # ARTIK KULLANILMIYOR — bkz. yukarıdaki not
    "fal_icon_prompt":      "",   # logo_icon slot için Recraft prompt
    "fal_app1_prompt":      "",   # app1 slot için Flux prompt (İngilizce, isim+hex renk formatı)
    "fal_app2_prompt":      "",   # app2 slot için Flux prompt (İngilizce, isim+hex renk formatı)
    "fal_hero_prompt":      "",   # mobil hero (9:16) için Flux prompt — Görev 2B (20 Tem 2026)

    # Görev 2B (20 Tem 2026): IG highlight kapak etiketleri — Sonnet markaya özgü
    # 4 etiket üretebilir; boşsa asset_generator._DEFAULT_HIGHLIGHTS kullanılır.
    "highlight_labels":     [],

    # Görev 2E (20 Tem 2026): harf-türevli mark ailesi. Sonnet 1-5 arası seçer;
    # boşsa image_generator aile kuralı EKLEMEZ (eski davranış, geriye dönük
    # güvenli). mark_link sadece aile 1'de anlamlı.
    "mark_family":          "",
    "mark_link":            "",

    # Görev 2E (20 Tem 2026): dil bilinçli marka adı büyütmesi. Sonnet Türkçe
    # kelimede i→İ, yabancı kelimede i→I yapar ("AXIS LOGISTICS" doğru, eskiden
    # "AXİS LOGİSTİCS" basılıyordu). Boşsa _brand_upper eski Türkçe varsayımına
    # düşer (geriye dönük güvenli).
    "brand_name_upper":     "",

    # Görev 2C (20 Tem 2026): kapanış "Bu kitte olmayan" listesi — Sonnet
    # sektöre özgü 3 madde üretir (Pepito canlı testi bulgusu: sabit liste
    # kutu markasına "ambalaj yok" diyordu). Boşsa template kendi
    # varsayılan 5 maddesine düşer.
    "not_included":         [],

    # Strateji — brand_brief.py Sonnet üretimi
    "brand_story":          "",
    "brand_story_preview":  "",
    "brand_story_line2":    "",
    "story_heading":        "",            # Manifesto başlığı — tagline değil
    "concept_statement":    "",
    "concept_body":         "",

    # Ses & Ton
    "voice_we":             ["", ""],
    "voice_we_not":         ["", ""],
    "mood_words":           [],

    # Görsel dil
    "visual_language":      "",

    # Sosyal medya post metinleri (PIL generator için)
    "social_post_1_caption": "",
    "social_post_2_caption": "",

    # Stüdyo DNA — detect_sector() tarafından eklenir
    "studio_dna":           {},        # {"label": "Collins", "sector": "Tech/SaaS", ...}

    # Tier — pipeline tarafından eklenir
    "tier":                 "free",

    # energy_tier — normalize_brief() tarafından hesaplanır (5-tier: cinematic/bold/luxury/playful/minimal)
    "energy_tier":          "cinematic",

    # Pipeline tarafından eklenen görsel base64'ler (opsiyonel)
    # html_preview.py bu alanları window.BRAND'e taşır
    "_card_front_b64":      "",   # PIL kartvizit ön — solo+
    "_card_back_b64":       "",   # PIL kartvizit arka — solo+
    "_web_hero_b64":        "",   # Web hero mockup — starter+
    "_ig_grid_b64":         "",   # Instagram grid — starter+
    "_letterhead_b64":      "",   # Letterhead — studio+
}

# Tier'a göre hangi alanların HTML brand kit'e dahil edileceği
TIER_FEATURES = {
    "free":         ["applications"],
    "solo":         ["applications", "businessCard"],
    "single":       ["applications", "businessCard"],
    "starter":      ["applications", "businessCard", "instagramGrid", "webHero"],
    "starter_pack": ["applications", "businessCard", "instagramGrid", "webHero"],
    "studio":       ["applications", "businessCard", "instagramGrid", "webHero", "letterhead"],
    "studio_pack":  ["applications", "businessCard", "instagramGrid", "webHero", "letterhead"],
    "pro":          ["applications", "businessCard", "instagramGrid", "webHero", "letterhead"],
    "pro_pack":     ["applications", "businessCard", "instagramGrid", "webHero", "letterhead"],
    "agency":       ["applications", "businessCard", "instagramGrid", "webHero", "letterhead"],
}


def normalize_brief(raw: dict) -> dict:
    """
    brand_brief.py çıktısını normalize et:
    - Eksik alanları DEFAULTS ile doldur
    - Tip uyumsuzluklarını düzelt (örn. string gelmesi gereken yerde None)
    - Accent color: None ise secondary ile aynı yap

    Dönüş: tüm alanları garantili brief dict
    """
    result = {**DEFAULTS, **raw}

    # accent_color: None → secondary
    if not result.get("accent_color"):
        result["accent_color"] = result["secondary_color"]

    # energy normalization — 2-tier (mevcut kod uyumu için korunur)
    energy_raw = str(result.get("energy", "cinematic")).lower()
    result["energy"] = "playful" if "playful" in energy_raw else "cinematic"

    # energy_tier — 5-tier (logo template dispatch + ikon seçim için)
    _ENERGY_TIER_MAP = {
        "cinematic": ["cinematic", "editorial", "sophisticated", "mysterious", "dark", "noir"],
        "bold":      ["bold", "energetic", "dynamic", "urgent", "intense", "strong", "powerful", "vivid"],
        "luxury":    ["luxury", "exclusive", "refined", "elegant", "premium", "opulent", "prestige"],
        "playful":   ["playful", "fun", "vibrant", "youthful", "friendly", "bright", "colorful", "lively"],
        "minimal":   ["minimal", "clean", "pure", "restrained", "simple", "quiet", "calm", "zen"],
    }
    detected_tier = "cinematic"  # default
    for tier, keywords in _ENERGY_TIER_MAP.items():
        if any(kw in energy_raw for kw in keywords):
            detected_tier = tier
            break
    result["energy_tier"] = detected_tier

    # bg_color: raw dict'te yoksa (eski format / Sonnet üretmedi) energy'e göre default koy
    if "bg_color" not in raw or not raw.get("bg_color"):
        if result["energy"] == "playful":
            result["bg_color"] = "#FAFAFA"
        else:
            result["bg_color"] = "#0F0D0C"

    # voice_we / voice_we_not: string geldiyse listeye çevir
    for key in ("voice_we", "voice_we_not"):
        val = result.get(key)
        if isinstance(val, str):
            result[key] = [val, ""]
        elif not isinstance(val, list):
            result[key] = ["", ""]
        elif len(result[key]) < 2:
            result[key] = (result[key] + ["", ""])[:2]

    # mood_words: string geldiyse listeye çevir
    if isinstance(result.get("mood_words"), str):
        result["mood_words"] = [w.strip() for w in result["mood_words"].split(",")]

    # story_heading: boşsa tagline'dan türet
    if not result.get("story_heading"):
        result["story_heading"] = result.get("tagline", "")

    # social_post captions: boşsa tagline'dan al
    if not result.get("social_post_1_caption"):
        result["social_post_1_caption"] = result.get("tagline", result["brand_name"])

    return result


def tier_features(tier: str) -> list[str]:
    """Bu tier'ın HTML brand kit'te hangi bölümlere sahip olduğunu döner."""
    return TIER_FEATURES.get(tier, TIER_FEATURES["free"])


def has_feature(brief: dict, feature: str) -> bool:
    """Brief'in tier'ı bu feature'ı destekliyor mu?"""
    return feature in tier_features(brief.get("tier", "free"))
