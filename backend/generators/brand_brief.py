"""
Claude API ile brand brief üretimi.
Kullanıcı promptu → structured brand brief JSON.
"""

import json
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Tier → model mapping
# Haiku:  free / solo / starter_pack — hızlı, standart çıktı
# Sonnet: studio_pack / pro_pack / agency — gelişmiş AI çıktısı
# Kullanıcıya model adı gösterilmez.
MODEL_MAP = {
    # Tüm tierlar Sonnet — kalite öncelikli (mevcut hacimde maliyet farkı önemsiz)
    "free":          "claude-sonnet-4-6",
    "solo":          "claude-sonnet-4-6",
    "starter_pack":  "claude-sonnet-4-6",
    "studio_pack":   "claude-sonnet-4-6",
    "pro_pack":      "claude-sonnet-4-6",
    "agency":        "claude-sonnet-4-6",
    # Eski tier isimleri (geriye dönük uyumluluk)
    "single":        "claude-sonnet-4-6",
    "starter":       "claude-sonnet-4-6",
    "pro":           "claude-sonnet-4-6",
}
DEFAULT_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Sen dünya standartlarında bir marka kimliği uzmanısın.
Referans estetik repertuarın geniş: Bureau Borsche, Sagmeister & Walsh, Pentagram, Base Design,
Collins, Wolff Olins, Landor. Her markaya kendi doğru estetiğini giydirirsin.

TEMEL YAKLAŞIM:
Önce markayı anla: sektör, hedef kitle, duygusal vaat, rekabet ortamı.
Sonra o markaya uygun estetik sistemi seç. Herkese aynı şablonu giydirme.

RENK KURALI — ÇOK ÖNEMLİ:
- Avant-garde/lüks/B2B → siyah (#0A0A0A) + off-white (#F1EBE1) ağırlıklı, maksimum 1 accent
- Çocuk/eğlence/yiyecek-içecek/spor → CANLI, doygun renkler. Marka karakterine uygun
  boldpalette kullan. Siyah zorunlu değil — beyaz veya açık renk zemin daha iyi işleyebilir.
- Sağlık/organik/doğa → toprak tonları, yeşiller, soft palettes
- Tech/SaaS → temiz, nötr, 1-2 vurgu rengi
Renk seçimini MARKAYA GÖRE yap, default'a kaçma.

TİPOGRAFİ:
Avant-garde → Big Shoulders Display / DM Sans / DM Mono
Çocuk/eğlenceli → Fredoka One / Nunito / Poppins
Lüks/premium → Cormorant Garamond / Optima / Futura
Organik/el yapımı → Playfair Display / Lato
Tech → Inter / Space Grotesk / IBM Plex

KOMPOZİSYON:
- Büyük/küçük ölçek kontrastı — güçlü hiyerarşi
- Ana harf veya şekil canvas'ı keser/zorlar
- Bold ama markanın karakteriyle uyumlu

JSON formatında yanıt ver. Başka hiçbir şey yazma."""

USER_TEMPLATE = """Kullanıcı isteği: {prompt}

Bu markayı analiz et ve aşağıdaki JSON yapısını eksiksiz doldur.
Renk, tipografi ve estetik seçimlerini marka karakterine göre yap — default siyah/beyaza kaçma.

{{
  "brand_name": "İsim veya kısaltma",
  "tagline": "Max 6 kelime, vurucu slogan — markaya özel ton ve ses",
  "brand_story": "3-4 paragraf — marka felsefesi, karakter, pozisyon, hedef kitle bağlantısı",
  "brand_story_preview": "Sadece ilk paragraf",
  "primary_color": "#XXXXXX  ← marka karakterine uygun ana renk",
  "secondary_color": "#XXXXXX  ← ana renkle uyumlu ikincil renk",
  "accent_color": "#XXXXXX veya null  ← isteğe bağlı 3. vurgu rengi",
  "font_display": "Marka karakterine uygun display font adı",
  "font_body": "Okunabilir body font adı",
  "font_meta": "Meta/label font adı",
  "logo_concept": "Ana logo tasarım fikri — hangi harf/şekil, nasıl kompozisyon, neden bu marka için doğru",
  "logo_versions": [
    {{"version": "primary", "description": "Yatay/geniş format açıklaması"}},
    {{"version": "icon", "description": "Kare/monogram format açıklaması"}},
    {{"version": "reversed", "description": "Ters versiyon açıklaması"}}
  ],
  "visual_language": "Genel görsel dil — formlar, dokular, kompozisyon kuralları",
  "mood_words": ["kelime1", "kelime2", "kelime3", "kelime4"],
  "social_post_1_caption": "Markaya uygun ton ve ses ile ilk sosyal medya post metni",
  "social_post_2_caption": "İkinci sosyal medya post metni",
  "energy": "cinematic VEYA playful — lüks/premium/B2B/VC → cinematic; çocuk/viral/eğlence/tüketici → playful",
  "concept_statement": "Markanın çekirdek vaadi — tek cümle, jenerik değil, swap testini geçmeli",
  "concept_body": "Concept statement'ı açıklayan 1-2 cümle",
  "story_heading": "Manifesto başlığı — tagline değil, gerilim veya dönüşüm cümlesi, max 6 kelime",
  "brand_story_line2": "Brand story ikinci paragraf (birincisi brand_story_preview)",
  "voice_we": ["Markanın ağzından gerçek replik 1", "Gerçek replik 2"],
  "voice_we_not": ["Bu markanın reddettiği ton örneği 1", "Reddedilen ton örneği 2"]
}}"""


def generate_brand_brief(prompt: str, tier: str = "free") -> tuple[dict, dict]:
    """
    Claude'a prompt gönder → (brand brief dict, token usage dict) döner.
    tier: free | single | starter | pro | agency
    """
    model = MODEL_MAP.get(tier, DEFAULT_MODEL)
    max_tokens = 4096  # Sonnet her tier için — story_heading + concept_body eklendi

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": USER_TEMPLATE.format(prompt=prompt),
            }
        ],
    )

    # Gerçek token kullanımını yakala
    token_usage = {
        "input_tokens":  message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }

    raw = message.content[0].text.strip()

    # JSON temizle (bazen ```json ... ``` içinde gelebilir)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("`").strip()

    return json.loads(raw), token_usage
