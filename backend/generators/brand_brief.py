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

# ─────────────────────────────────────────────────────────────────────────────
#  STÜDYO DNA — Sektöre göre atanan estetik kişilik
#  Her sektör bir dünya stüdyosunun bakış açısını temsil eder.
# ─────────────────────────────────────────────────────────────────────────────

SECTOR_STUDIO_MAP: dict[str, dict] = {
    "industry_b2b": {
        "label": "Wolff Olins",
        "sector": "Endüstri / B2B",
        "voice": (
            "Bold, systematic, unapologetic. Sektörün dilini konuş ama beklentiyi alt üst et. "
            "Kurumsal ağırlık değil — kategorik dönüşüm. Renk ve form güç hissettirir; "
            "söz fazlası yok, her şey kaçınılmaz görünür."
        ),
        "keywords": [
            "iş güvenliği", "endüstri", "fabrika", "üretim", "inşaat", "imalat",
            "makine", "b2b", "tedarik", "lojistik", "depo", "sanayi", "isg", "ehs",
            "mühendislik", "proje yönetimi", "çevre", "enerji", "madencilik",
        ],
    },
    "luxury_premium": {
        "label": "Bureau Borsche",
        "sector": "Lüks / Premium",
        "voice": (
            "Editorial, cinematic, tipografik üstünlük. Her söz ölçülü — sessizlik de bir "
            "tasarım öğesi. Marka, kalabalığı görmezden gelir; sadece doğru insanla konuşur. "
            "Görsel hiyerarşi mutlak; detay kusursuz."
        ),
        "keywords": [
            "lüks", "premium", "moda", "fashion", "haute", "atölye", "tasarım stüdyo",
            "otel", "butik", "gastronomi", "şarap", "saat", "mücevher", "parfüm",
            "koleksiyon", "resort", "villa", "yat",
        ],
    },
    "tech_saas": {
        "label": "Collins",
        "sector": "Tech / SaaS",
        "voice": (
            "Strategic, warm, culturally resonant. Teknik değil — insan odaklı. "
            "Akıllı ama erişilebilir; soğuk değil, cesur. Marka bir araç değil, "
            "bir bakış açısı. İnsanı görmek ürünü gölgelemez."
        ),
        "keywords": [
            "tech", "saas", "yazılım", "uygulama", "app", "platform", "ai",
            "yapay zeka", "data", "bulut", "cloud", "startup", "fintech", "kripto",
            "blockchain", "digital", "dijital", "otomasyon", "api", "erp", "crm",
        ],
    },
    "culture_creative": {
        "label": "Sagmeister & Walsh",
        "sector": "Kültür / Yaratıcı",
        "voice": (
            "Provocative, personal, experiential. Kural ihlali kaçınılmaz — ama kasıtlı. "
            "Sanat ile ticaret arasında bilinçli gerilim. Her karar bir manifestodur. "
            "Sıradan güzel olmak bu markanın en büyük başarısızlığı olur."
        ),
        "keywords": [
            "kültür", "sanat", "medya", "müzik", "film", "festival", "galeri",
            "yaratıcı", "creative", "ajans", "agency", "influencer", "creator",
            "içerik", "content", "podcast", "yayın", "grafik", "illüstrasyon",
        ],
    },
    "food_lifestyle": {
        "label": "Pentagram",
        "sector": "Gıda / Yaşam",
        "voice": (
            "Considered, multi-disciplinary, timeless. Trend değil — karakter. "
            "Her detay yerli yerinde; hiçbir şey fazla, hiçbir şey eksik. "
            "Marka rafta değil, sofrada veya evde yaşar."
        ),
        "keywords": [
            "gıda", "yiyecek", "içecek", "restoran", "kafe", "kahve", "organik",
            "doğal", "sağlıklı", "beslenme", "mutfak", "food", "lifestyle",
            "wellness", "yaşam", "tarım", "üzüm", "peynir", "çikolata", "fırın",
        ],
    },
    "health_medical": {
        "label": "Landor",
        "sector": "Sağlık / Medikal",
        "voice": (
            "Trust-first, human clarity. Karmaşıklığı eritir, insanı merkeze alır. "
            "Klinik soğukluğu yok — güven görünmez ama hissedilir. "
            "Renk ve form kaygıyı azaltır, umut verir."
        ),
        "keywords": [
            "sağlık", "medikal", "hastane", "klinik", "ilaç", "pharma",
            "terapi", "psikoloji", "rehabilitasyon", "eczane", "diş",
            "optik", "wellness", "spa", "psikiyatri", "check-up",
        ],
    },
    "corporate_legal": {
        "label": "Base Design",
        "sector": "Kurumsal / Hukuk / Finans",
        "voice": (
            "Rigorous, elegant, systematic. Fazlalık yok — her element işlevli. "
            "Güç sadelikte. Marka güvenilirliği fısıldar, bağırmaz. "
            "Tipografi ve boşluk hiyerarşi kurar; renk minimal ama kesin."
        ),
        "keywords": [
            "hukuk", "avukat", "finans", "muhasebe", "danışmanlık", "consulting",
            "yönetim", "corporate", "sigorta", "holding", "yatırım", "banka",
            "denetim", "audit", "fon", "varlık", "portföy",
        ],
    },
}

_DEFAULT_STUDIO = "tech_saas"  # keyword eşleşmesi yoksa Collins


def detect_sector(prompt: str) -> dict:
    """
    Prompt'tan sektörü tespit et → stüdyo DNA dict döner.
    Yaklaşım: keyword frekansı. En çok eşleşen sektör kazanır.
    Tie veya eşleşme yok → _DEFAULT_STUDIO.
    """
    prompt_lower = prompt.lower()
    scores: dict[str, int] = {}
    for sector_key, studio in SECTOR_STUDIO_MAP.items():
        score = sum(1 for kw in studio["keywords"] if kw in prompt_lower)
        if score > 0:
            scores[sector_key] = score

    if not scores:
        return SECTOR_STUDIO_MAP[_DEFAULT_STUDIO]

    best = max(scores, key=lambda k: scores[k])
    return SECTOR_STUDIO_MAP[best]

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

Aşağıdaki JSON formatında yanıt ver. Sadece JSON döndür, başka hiçbir şey yazma.

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
  "logo_concept": "4 zorunlu element, her biri 1 cümle: (1) GÖRSEL METAFOR — marka özünü temsil eden beklenmedik ama doğru sembol (Apple elması gibi — hem bilgi hem yasak hem Newton, tek formda); (2) PRİMİTİF FORM — bu metaforu max 3 geometrik eleman ile nasıl ifade edersin, tek cümle; (3) NEGATİF ALAN — hangi boşluk/kesik anlam taşır (FedEx okunu veya Apple ısırığını rehber al — olmayan şey anlam verir); (4) SWAP ENGELI — sadece bu markaya ait, başka hiçbir markaya konamayacak özgün detay. YASAK: 'harf + şekil', 'monogram', 'sade ve modern' gibi jenerik cümleler.",
  "logo_icon_svg_brief": "320x320 ikon için tek eylemli geometri talimatı — doğrudan SVG'ye çevrilebilir, geometrik ve somut: Örn: 'Ş harfinin üst yatayını 45° açıyla kes; kesik boşluk beyaz kalır, negatif ok okur.' VEYA 'F harfinin alt kolu yoktur; ortada gizli boşluk ok yönünü ima eder.' YASAK: 'modern', 'minimal', 'zarif harf', 'harf yanına şekil ekle' — bunlar talimat değil. Sadece 1 cümle: ne çizilecek ve nasıl.",
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
  "social_post_2_caption": "Farklı içerik türü veya bakış açısı — ikinci post",
  "fal_logo_prompt": "Recraft v3 için İngilizce prompt — logo_primary slot (wordmark/primary logo). Kurallar: (1) İngilizce yaz, (2) 'vector logo for [BRAND NAME]' ile başla, (3) logo_concept'teki görsel metaforu ve primitif formu İngilizce olarak somutlaştır, (4) exact renk kodlarını yaz (primary_color dominant), (5) bg_color'u belirt, (6) 'No gradients. No shadows. No text other than brand name. Vector illustration.' ile bitir. Max 3 cümle. Örnek: 'Vector logo for VOLT electric scooter brand. Letter V with integrated lightning bolt as negative space — bold diagonal cut creates speed arrow. Electric yellow #F0C832 on dark slate #1A1E2E. No gradients. No shadows. Vector illustration.'",
  "fal_icon_prompt": "Recraft v3 için İngilizce prompt — logo_icon slot (app icon / mark). Kurallar: (1) İngilizce yaz, (2) 'App icon for [BRAND NAME]' ile başla, (3) logo_icon_svg_brief'teki geometri talimatını İngilizce ve Recraft'a uygun şekilde ifade et, (4) 'No text. Square format. Scalable geometric shape.' ekle, (5) exact renk kodlarını yaz. Max 3 cümle. Örnek: 'App icon for VOLT brand. Letter V with diagonal lightning bolt bisecting the form — the negative space reads as a directional arrow implying speed. Electric yellow #F0C832 on dark slate #1A1E2E. No text. Square format. Vector illustration.'"
}}"""


# ─────────────────────────────────────────────────────────────────────────────
#  SELF-CRITIQUE PASS — 2. Sonnet çağrısı
#  İlk brief üretildikten sonra 4 kalite kapısını kontrol eder.
#  Başarısız alanları yeniden yazar. Geçen alanları değiştirmez.
#  Tahmini maliyet: ~$0.01/üretim. Kalite etkisi: %30-40.
# ─────────────────────────────────────────────────────────────────────────────

CRITIQUE_SYSTEM = """Sen sert ve tarafsız bir marka stratejisi kalite denetçisisin.
Görevin: verilen brief alanlarını 6 kalite kapısından geçirmek.
Başarısız olan alanları yeniden yaz. Geçen alanları AYNEN koru — değiştirme.

Yanıtın: sadece başarısız alanları içeren JSON. Başka hiçbir şey yazma.
Tüm alanlar geçiyorsa boş JSON ({}) döndür."""

CRITIQUE_USER_TEMPLATE = """Marka: {brand_name} | Sektör: {sector} | Kullanıcı isteği: {prompt}

Aşağıdaki brief alanlarını 4 kalite kapısından geçir:

─── KONTROL EDİLECEK ALANLAR ───
concept_statement: "{concept_statement}"
story_heading: "{story_heading}"
tagline: "{tagline}"
voice_we_not_1: "{voice_we_not_1}"
voice_we_not_2: "{voice_we_not_2}"
brand_story_preview: "{brand_story_preview}"
logo_concept: "{logo_concept}"
logo_icon_svg_brief: "{logo_icon_svg_brief}"

─── 6 KALİTE KAPISI ───

KAPI 1 — SWAP TEST (concept_statement):
Soru: Bu cümle, aynı sektördeki başka bir markaya da uyar mı?
Uyarsa → BAŞARISIZ. Yeniden yaz: marka adı olmadan sadece bu markaya ait paradoks/gerilim.
✗ "Güvenliği bir sonraki seviyeye taşıyoruz" → her güvenlik firması söyler
✓ "Kaza olmayan yerde insan var — biz onu görüyoruz" → sadece bu perspektife ait

KAPI 2 — STORY HEADING (story_heading):
Soru: Bu başlık tagline'ın kopyası mı? Okuyunca duraksatıyor mu? Paradoks/gerilim var mı?
Tagline kopyasıysa veya duraksatmıyorsa → BAŞARISIZ. Yeniden yaz: max 6 kelime, tersine çevrilmiş beklenti.
✗ "Güvenli Çalışma, Güçlü Gelecek" → tagline formatı
✓ "Tehlike Yoksa Başarısız Oluyoruz" → gerilim, beklentiyi kırıyor

KAPI 3 — SEKTÖR KLİŞESİ (voice_we_not):
Soru: Bu replikler gerçekten bu sektörün kullandığı klişeler mi? Jenerik korporat söylem mi yoksa sektöre özgü mü?
Jenerik ise (herhangi bir sektöre de uyar) → BAŞARISIZ. Yeniden yaz: bu sektörün tam klişesi.
✗ "Müşteri memnuniyeti bizim önceliğimiz" → jenerik, sektörsüz
✓ "Sıfır kaza hedefiyle ilerliyoruz" → iş güvenliği sektörünün tam klişesi

KAPI 4 — İNSAN GERÇEĞİ (brand_story_preview):
Soru: İlk paragraf insan içgörüsü veya kategorinin sorunu mu? Marka adı geçiyor mu? Ürün tanımı gibi mi başlıyor?
Ürün tanımıysa veya marka adı geçiyorsa → BAŞARISIZ. Yeniden yaz: insan davranışı/duygusu/sorunu — marka adı yok.
✗ "XYZ Şirketi iş güvenliği alanında..." → ürün tanımı
✓ "Her sabah işe gidenlerin büyük çoğunluğu eve dönüp dönmeyeceğini düşünmez." → insan gerçeği

KAPI 5 — LOGO KONSEPTİ (logo_concept):
Soru: Bu logo_concept 4 elementi içeriyor mu? (1) görsel metafor, (2) primitif form, (3) negatif alan, (4) swap engeli.
Eksik veya jenerikse → BAŞARISIZ. Yeniden yaz: Apple ısırığı ve FedEx oku standardında, 4 elementin tamamını içeren özgün brief.
✗ "Modern bir font ile marka adı, arka planda geometrik şekil" → jenerik, herhangi bir markaya uyar
✓ "Metafor: Anlık karar anı — bir düğmeye basma hareketi; Form: diagonal kesik çizgi Ş harfini ikiye böler (2 eleman); Negatif alan: kesik içinde gizli ok, ileriyi işaret eder; Swap engeli: sadece Ş'nin dekonstrüksiyonu bu markaya ait" → özgün, uygulanabilir

KAPI 6 — İKON SVG TALİMATI (logo_icon_svg_brief):
Soru: Bu talimat doğrudan SVG'ye çevrilebilir mi? "Harf + ekleme" yapıyor mu? Başka markaya uyabilir mi?
BAŞARISIZ koşullar (herhangi biri):
  ✗ Eklenti mantığı: mevcut harfin dışına/üstüne/yanına bir eleman yapıştırılıyor ("ok ekle", "çizgi ekle", "nokta koy")
  ✗ Soyut/jenerik: "modern minimal sembol", "hız ikonu", "zarif harf", "dinamik form"
  ✗ Swap geçemez: aynı ikon başka kurye/hız markasına koyulabilir
  ✗ SVG'ye çevrilemiyor: geometrik tarif yok, sadece estetik kelimeler var
BAŞARISIZ → Yeniden yaz. Şu üç yaklaşımdan birini kullan:
  1. Harfin bir bölümünü KES → kesik/boşluk anlam taşısın (Apple ısırığı modeli — ekleme değil çıkarma)
  2. Harfin iç boşluğunu (counter/negative space) somut bir forma dönüştür (FedEx modeli — varolan boşluğu oku)
  3. İki harfi birleştir → birleşim noktasından yeni form doğsun
✗ "Ş harfinin cedilla'sına turuncu ok ekle" → eklenti, yasak
✓ "Ş harfinin üst yatay çubuğu 40° açıyla kesilir; kesik boşluk sağ-yukarı yönünde ok oluşturur — negatif alan, ekleme değil çıkarma; cedilla bu sefer sol-aşağı okur, çift yön sadece Ş anatomisinde var" → harften doğan, geometrik, swap-proof

─── ÇIKTI FORMATI ───
Sadece başarısız alanlar için JSON döndür. Örnek:
{{
  "concept_statement": "Yeniden yazılmış versiyon",
  "logo_concept": "Yeniden yazılmış logo konsepti",
  "logo_icon_svg_brief": "Yeniden yazılmış ikon talimatı"
}}
Tüm kapılar geçtiyse: {{}}"""


def _clean_json(raw: str) -> dict:
    """JSON string temizle ve parse et. Hata durumunda boş dict döner."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("`").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def critique_brief(brief: dict, prompt: str, studio: dict) -> tuple[dict, dict]:
    """
    Brief alanlarını 4 kalite kapısından geçir.
    Başarısız alanları yeniden yazar, geçenlere dokunmaz.
    Döner: (güncellenmiş brief dict, critique token usage dict)
    """
    voice_we_not = brief.get("voice_we_not", ["", ""])
    vwn1 = voice_we_not[0] if len(voice_we_not) > 0 else ""
    vwn2 = voice_we_not[1] if len(voice_we_not) > 1 else ""

    user_content = CRITIQUE_USER_TEMPLATE.format(
        brand_name=brief.get("brand_name", ""),
        sector=studio.get("sector", ""),
        prompt=prompt[:200],  # token tasarrufu — ilk 200 karakter yeterli
        concept_statement=brief.get("concept_statement", ""),
        story_heading=brief.get("story_heading", ""),
        tagline=brief.get("tagline", ""),
        voice_we_not_1=vwn1,
        voice_we_not_2=vwn2,
        brand_story_preview=brief.get("brand_story_preview", "")[:300],  # token limiti
        logo_concept=brief.get("logo_concept", "")[:400],  # token limiti
        logo_icon_svg_brief=brief.get("logo_icon_svg_brief", "")[:300],  # token limiti
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,  # 6. kapı eklendi — biraz daha alan gerekli
        system=CRITIQUE_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )

    token_usage = {
        "input_tokens":  message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }

    fixes = _clean_json(message.content[0].text)

    if not fixes:
        # Tüm kapılar geçti — brief değişmeden döner
        return brief, token_usage

    # Başarısız alanları güncelle
    updated = dict(brief)
    for field, value in fixes.items():
        if field == "voice_we_not_1":
            wn = list(updated.get("voice_we_not", ["", ""]))
            wn[0] = value
            updated["voice_we_not"] = wn
        elif field == "voice_we_not_2":
            wn = list(updated.get("voice_we_not", ["", ""]))
            if len(wn) < 2:
                wn.append(value)
            else:
                wn[1] = value
            updated["voice_we_not"] = wn
        else:
            updated[field] = value

    # Critique geçmişini kaydet (admin/debug için)
    updated["_critique_fixes"] = list(fixes.keys())

    return updated, token_usage


def generate_brand_brief(prompt: str, tier: str = "free") -> tuple[dict, dict]:
    """
    Claude'a prompt gönder → (brand brief dict, token usage dict) döner.
    tier: free | single | starter | pro | agency

    Sektör otomatik tespit edilir → stüdyo DNA sistem prompt'a enjekte edilir.
    """
    model = MODEL_MAP.get(tier, DEFAULT_MODEL)
    max_tokens = 4096  # Sonnet her tier için — story_heading + concept_body eklendi

    # Stüdyo DNA tespiti — sistem prompt'a enjekte edilir
    studio = detect_sector(prompt)
    studio_injection = (
        f"\n\n─── STÜDYO KİŞİLİĞİ: {studio['label']} ({studio['sector']}) ───\n"
        f"Bu markayı {studio['label']} perspektifiyle yaklaş.\n"
        f"{studio['voice']}\n"
        f"Bunu stil notu olarak değil, bakış açısı olarak içselleştir. "
        f"Çıktıda 'stüdyo adı' geçmez — sadece o zihin yapısıyla üret."
    )
    dynamic_system = SYSTEM_PROMPT + studio_injection

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=dynamic_system,
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

    # DEBUG — her üretimde stop_reason ve ham yanıtın ilk 300 karakteri loglanır
    print(f"[brief] stop_reason={message.stop_reason} output_tokens={message.usage.output_tokens}")
    print(f"[brief] raw ilk 300: {raw[:300]!r}")

    # JSON temizle — backtick wrapper veya preamble metin varsa temizle
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("`").strip()

    # Model JSON öncesi metin yazdıysa (preamble), { başlayan noktayı bul
    if raw and not raw.startswith("{"):
        start = raw.find("{")
        if start != -1:
            raw = raw[start:]

    if not raw:
        raise ValueError(
            f"Anthropic boş yanıt döndürdü. "
            f"stop_reason={message.stop_reason}, "
            f"output_tokens={message.usage.output_tokens}, "
            f"content_len={len(message.content)}"
        )

    parsed = json.loads(raw)
    # Stüdyo DNA'yı brief'e ekle — template ve admin stats için
    parsed["studio_dna"] = {
        "label":  studio["label"],
        "sector": studio["sector"],
    }
    # Sözleşme: eksik alanları default ile doldur, tip uyumsuzluklarını düzelt
    normalized = normalize_brief(parsed)

    # ── Self-critique pass — 4 kalite kapısı ─────────────────────────────────
    critiqued, critique_tokens = critique_brief(normalized, prompt, studio)
    token_usage["input_tokens"]  += critique_tokens["input_tokens"]
    token_usage["output_tokens"] += critique_tokens["output_tokens"]

    return critiqued, token_usage
