"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  DOKUNMA BÖLGESİ: BACKEND / GENERATOR                                      ║
║  Deploy: deploy_backend.command (çift tıkla)                                ║
║  Etkilediği katman: Fly.io backend — sadece bu katmanı değiştirir           ║
║                                                                              ║
║  BU DOSYAYA Frontend (Next.js/Vercel) değişikliği sırasında DOKUNMA.       ║
║  Frontend deploy: clear_cache_and_deploy.command                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

Claude API ile brand brief üretimi.
Kullanıcı promptu → structured brand brief JSON.
Çıktı: normalize_brief() ile garantili BrandBriefContract alanları.
"""

import json
import os
import anthropic

from generators.brand_brief_contract import normalize_brief  # sözleşme normalizer

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

RENK KURALI — KESİN:
Saf siyah (#000000) ve saf beyaz (#FFFFFF) DEFAULT'TUR — yani başarısızlıktır.
Her marka kendi tonunu almalı. Örnekler:
- İş güvenliği/endüstri → koyu orman yeşili, antrasit, koyu petrol
- Finans/hukuk → derin lacivert, koyu mürekkep, derin kırmızı-siyah
- Lüks/premium → sıcak siyah (#0A0808), derin kahve (#1A0F0A), koyu yeşim
- Sağlık/medikal → koyu teal, koyu zeytin, derin mavi-yeşil
- Çocuk/eğlence → beyaz zemin + canlı, doygun accent'ler
- Gıda/içecek → sektörün renk dilinden al (kahve → koyu kahve+altın, organik → yeşil+toprak)
- Tech/SaaS → koyu lacivert, derin gri-mavi, koyu slate
Kural: bg_color, primary, secondary renkleri birbirini tamamlamalı.
primary_color = marka accent'i (logo, vurgu, CTA).
secondary_color = tamamlayıcı/ikincil ton.
bg_color = sayfa/uygulama zemini — sektöre özgü koyu veya açık ton, ASLA #000000 veya #FFFFFF.

TİPOGRAFİ — sektöre göre seç, hepsine aynı fontu verme:
Güvenlik/endüstri/askeri → Big Shoulders Display, Bebas Neue, Barlow Condensed
Çocuk/eğlenceli → Fredoka One, Nunito, Poppins
Lüks/premium/moda → Cormorant Garamond, Playfair Display, Optima
Organik/el yapımı/doğa → Playfair Display, Lora, DM Serif Display
Tech/SaaS/fintech → Inter, Space Grotesk, IBM Plex Sans
Kurumsal/B2B → DM Sans, Source Sans Pro, Raleway

KOMPOZİSYON:
- Büyük/küçük ölçek kontrastı — güçlü hiyerarşi
- Ana harf veya şekil canvas'ı keser/zorlar
- Bold ama markanın karakteriyle uyumlu

KALİTE KAPISI — çıktı üretmeden önce kontrol et:
1. SWAP TEST: concept_statement başka bir markaya da uyar mı? Uyguluyorsa yeniden yaz.
2. SEKTÖR TUZAĞI: voice_we_not örnekleri bu sektörün tam klişesi mi? Jenerik korporat dil değil.
3. STORY HEADING: tagline'ın kopyası değil, gerilim veya dönüşüm cümlesi mi?
4. RENK: bg_color saf siyah/beyaz mı? → Sektöre özgü koy.

JSON formatında yanıt ver. Başka hiçbir şey yazma."""

USER_TEMPLATE = """Kullanıcı isteği: {prompt}

Bu markayı analiz et ve aşağıdaki JSON yapısını eksiksiz doldur.
Renk, tipografi ve estetik seçimlerini marka karakterine göre yap — default siyah/beyaza kaçma.

{{
  "brand_name": "İsim veya kısaltma",
  "tagline": "Max 6 kelime, vurucu slogan — markaya özel ton ve ses",
  "brand_story": "3-4 paragraf — marka felsefesi, karakter, pozisyon, hedef kitle bağlantısı",
  "brand_story_preview": "Sadece ilk paragraf",
  "primary_color": "#XXXXXX  ← marka accent'i (logo, CTA, vurgu)",
  "secondary_color": "#XXXXXX  ← ana renkle uyumlu ikincil ton",
  "accent_color": "#XXXXXX veya null  ← isteğe bağlı 3. vurgu rengi",
  "bg_color": "#XXXXXX  ← sektöre özgü zemin rengi, ASLA #000000 veya #FFFFFF",
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

    parsed = json.loads(raw)
    # Sözleşme: eksik alanları default ile doldur, tip uyumsuzluklarını düzelt
    return normalize_brief(parsed), token_usage
