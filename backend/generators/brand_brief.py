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

SYSTEM_PROMPT = """Sen dünya standartlarında bir marka kimliği ve strateji uzmanısın.
Estetik repertuarın: Bureau Borsche, Sagmeister & Walsh, Pentagram, Base Design, Collins, Wolff Olins, Landor.
Strateji referansın: Katapult İstanbul yaklaşımı — "What is felt, stays."

STRATEJI YAPISI — her marka için bu 4 katmanı zihinsel olarak geç:
1. SİTUATİON: Bu sektörde markalar ne yapıyor? Kalabalık nerede? Kategorinin cliché'si nedir?
2. PİVOT: Dominant beklentiyi ters çevir. "Herkes X yaparken biz Y yapıyoruz."
3. İNSİGHT: Hedef kitlenin içinde hiç söylenmemiş gerçek. Evrensel ama özgün.
4. FİKİR: Tek cümleye sığan, viral mekanikle donatılmış marka fikri.

MARKA HİKAYESİ FORMATI:
brand_story 3-4 paragraf olmalı:
- P1 (brand_story_preview): İnsan içgörüsü veya kategorinin sorunu — marka adı yok
- P2 (brand_story_line2): Markanın pivot'u — beklentiyi nasıl kırıyor
- P3: Kime hitap ediyor, nasıl yaşıyor, ne hissettiriyor
- P4: Felsefe, uzun vadeli vizyon

CONCEPT STATEMENT — tek cümle, swap testini geçmeli:
❌ "İş güvenliğini bir sonraki seviyeye taşıyoruz."
✅ "Kazanın olmadığı yerde insan var — biz onu görüyoruz."
Paradoks, gerilim veya beklenmedik açı kullan.

STORY HEADING — manifesto başlığı, tagline değil:
❌ "Güvenli Çalışma, Güçlü Gelecek" (tagline kopyası)
✅ "Tehlike Yoksa Başarısız Oluyoruz" (gerilim, tersine çevrilmiş beklenti)
Max 6 kelime. Okuyunca duraksatan bir şey.

VOICE — sesini bul:
voice_we: Markanın gerçek bağlamda söyleyebileceği özgün replikler.
  "Biz üretkenlik satmıyoruz. İnsanın eve dönüşünü satıyoruz."
  Tonun: sektörün cliché'sini değil, markanın karakterini yansıtsın.

voice_we_not: Bu markanın sektöründe rakiplerin tam olarak söylediği, kulağa profesyonel gelen ama içi boş replikler.
  Jenerik korporat değil — O sektörün özel klişesi.
  İş güvenliği: "Sıfır kaza hedefiyle ilerliyoruz" / "Güvenliğiniz bizim önceliğimiz"
  Fintech: "Finansal özgürlüğünüzü destekliyoruz" / "Geleceğinize yatırım yapın"

RENK KURALI — KESİN:
Saf siyah (#000000) ve saf beyaz (#FFFFFF) başarısızlıktır — defaulta kaçmak.
Her marka kendi renk tonunu alır:
- İş güvenliği/endüstri → koyu orman yeşili (#0D2B1A), antrasit (#1C2124), koyu petrol (#0B1F2A)
- Finans/hukuk → derin lacivert (#0D1B2A), koyu mürekkep (#14172B), derin bordo-siyah (#1A0D0D)
- Lüks/premium → sıcak siyah (#0A0808), derin kahve (#1A0F0A), koyu yeşim (#0A1A10)
- Sağlık/medikal → koyu teal (#0B1F1F), koyu zeytin (#141A0A), derin mavi-yeşil (#0A1420)
- Çocuk/eğlence → açık/beyaz zemin + canlı doygun accent'ler
- Gıda/içecek → kahve: koyu kahve+altın; organik: derin yeşil+toprak
- Tech/SaaS → koyu lacivert (#0F1924), koyu slate (#141B22), derin gri-mavi (#111820)
primary_color = accent (logo, vurgu, CTA)
secondary_color = tamamlayıcı ikincil
bg_color = sektöre özgü zemin, ASLA #000000/#FFFFFF

TİPOGRAFİ — sektöre göre, hepsine aynı font verme:
Güvenlik/endüstri/askeri → Big Shoulders Display, Bebas Neue, Barlow Condensed
Çocuk/eğlenceli → Fredoka One, Nunito, Poppins
Lüks/premium/moda → Cormorant Garamond, Playfair Display
Organik/doğa → Playfair Display, Lora, DM Serif Display
Tech/SaaS/fintech → Inter, Space Grotesk, IBM Plex Sans
Kurumsal/B2B → DM Sans, Source Sans Pro, Raleway
Kültür/sanat/medya → Syne, Clash Display, PP Neue Montreal

KOMPOZİSYON:
- Büyük/küçük ölçek kontrastı — güçlü hiyerarşi
- Ana harf veya şekil canvas'ı keser/zorlar
- Minimalist ama karakter sahibi

KALİTE KAPISI — üretmeden önce her birini geç:
1. SWAP TEST: concept_statement başka markaya da uyar mı? → Yeniden yaz.
2. SEKTÖR TUZAĞI: voice_we_not bu sektörün gerçek klişesi mi? Jenerik değil mi?
3. STORY HEADING: Okuyunca duraksatıyor mu? Tagline'ın kopyası mı? → Paradoks koy.
4. İNSİGHT: brand_story_preview bir insan gerçeği içeriyor mu, ürün tanımı mı?
5. RENK: bg_color saf siyah/beyaz mı? → Sektöre özgü koy.

JSON formatında yanıt ver. Başka hiçbir şey yazma."""

USER_TEMPLATE = """Kullanıcı isteği: {prompt}

Bu markayı analiz et. Önce 4 katmanlı zihinsel süreçten geç (Situation → Pivot → Insight → Fikir), sonra JSON'ı doldur.

{{
  "brand_name": "İsim veya kısaltma",
  "tagline": "Max 6 kelime — markaya özgü ses, swap testini geçmeli",
  "brand_story": "4 paragraf — P1: sektör gerçeği/insan içgörüsü (marka adı yok). P2: markanın pivot'u. P3: hedef kitle portresi. P4: uzun vadeli felsefe.",
  "brand_story_preview": "Tam P1 (brand_story'nin ilk paragrafı)",
  "brand_story_line2": "Tam P2 (markanın pivot cümlesi)",
  "story_heading": "Manifesto başlığı — gerilim veya ters çevrilmiş beklenti, max 6 kelime. ASLA tagline kopyası. Örn: 'Tehlike Yoksa Başarısız Oluyoruz', 'Herkes Varmak İster, Biz Yol Oluruz'",
  "concept_statement": "Tek cümle çekirdek vaat — insan içgörüsünden çıkan, paradoks veya gerilim içeren. ASLA jenerik: 'Güvenliğinizi ön planda tutuyoruz' başarısızlıktır.",
  "concept_body": "Concept_statement'ı somutlaştıran 1-2 cümle. Marka × insan = nasıl bir şey. Formül örn: 'Riski hesaplamak × İnsanı görmek = Kaza değil, ev dönüşü'",
  "primary_color": "#XXXXXX  ← marka accent (logo, CTA, ana vurgu)",
  "secondary_color": "#XXXXXX  ← tamamlayıcı ikincil ton",
  "accent_color": "#XXXXXX veya null  ← 3. vurgu (opsiyonel)",
  "bg_color": "#XXXXXX  ← sektöre özgü zemin. ASLA #000000 veya #FFFFFF. İş güvenliği → koyu yeşil/antrasit. Finans → derin lacivert. Lüks → sıcak koyu. Tech → koyu slate.",
  "font_display": "Sektör karakterine uygun display font",
  "font_body": "Okunabilir body font",
  "font_meta": "Meta/label font (DM Mono, JetBrains Mono, IBM Plex Mono gibi)",
  "logo_concept": "Logo DNA'sı — harf/form seçimi, kompozisyon mantığı, neden bu marka için doğru",
  "logo_versions": [
    {{"version": "primary", "description": "Yatay format açıklaması"}},
    {{"version": "icon", "description": "Monogram/ikon format"}},
    {{"version": "reversed", "description": "Ters versiyon"}}
  ],
  "visual_language": "Görsel sistem — formlar, kontrast, hareket, doku, kompozisyon kuralları",
  "mood_words": ["kelime1", "kelime2", "kelime3", "kelime4"],
  "energy": "cinematic VEYA playful",
  "voice_we": [
    "Markanın gerçek bağlamda söyleyebileceği özgün replik — karakter taşıyan",
    "İkinci replik — farklı bir durum veya bağlam"
  ],
  "voice_we_not": [
    "Bu sektörün rakiplerinin tam olarak kullandığı klişe — kulağa profesyonel gelir ama içi boş",
    "İkinci sektör klişesi — farklı bir cliché formatı"
  ],
  "social_post_1_caption": "Gerçek sosyal medya postu — markanın sesinde, platform tonunda",
  "social_post_2_caption": "Farklı içerik türü veya bakış açısı — ikinci post"
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
