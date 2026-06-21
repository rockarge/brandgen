"""
no1-brandkit kalitesinde HTML brand kit üretir.
Brief JSON → Claude API (Haiku) → window.BRAND config → brandkit-template.html → tam HTML

Eski statik template doldurma kaldırıldı.
Claude, no1-brandkit SKILL kurallarını uygulayarak markaya özgü strateji üretir:
- Anti-generic: yasaklı kalıp yok
- Swap testi: marka adı değişince de doğruysa yeniden yaz
- concept/story/voice: sektörün gerçek geriliminden türetilir
"""

import os
import re
import json
import base64

import anthropic


def _fix_svg_base64(data_uri: str) -> str:
    """
    AI üretiminde sık görülen SVG XML hatalarını düzelt.
    Özellikle: <text>content<text> → <text>content</text>
    """
    prefix = "data:image/svg+xml;base64,"
    if not data_uri.startswith(prefix):
        return data_uri
    b64 = data_uri[len(prefix):]
    try:
        svg = base64.b64decode(b64 + "==").decode("utf-8")
    except Exception:
        return data_uri

    # Fix 1: Kapama etiketinde / eksik — <text>content<text> → <text>content</text>
    # Regex: text içeriğinden sonra gelen bare <text> (attribute'suz), bir sonraki tag'den önce
    svg = re.sub(r'([^<\s][^<]*?)<text>(\s*<)', lambda m: m.group(1) + "</text>" + m.group(2), svg)
    # Fix 2: Satır sonunda kalan <text> kapama hataları
    svg = re.sub(r'(<text[^>]*>[^<]+)<text>', r'\1</text>', svg)
    # Fix 3: <tspan>content<tspan> aynı hata tspan için
    svg = re.sub(r'(<tspan[^>]*>[^<]+)<tspan>', r'\1</tspan>', svg)

    try:
        fixed_b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return prefix + fixed_b64
    except Exception:
        return data_uri


def _fix_svg_in_config(brand_config: str) -> str:
    """
    window.BRAND config string içindeki tüm base64 SVG URI'larını bulup onar.
    """
    pattern = r'data:image/svg\+xml;base64,[A-Za-z0-9+/=]+'
    def replacer(m):
        return _fix_svg_base64(m.group(0))
    return re.sub(pattern, replacer, brand_config)

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "brandkit-template.html")

_SYSTEM_PROMPT = """Sen bir marka kimlik stratejisti, kreatif direktör ve SVG tasarımcısısın.
Sana bir marka brief JSON'u verilecek. Bu verilerden brandkit-template.html için
window.BRAND JavaScript konfig bloğunu üreteceksin.

## KALİTE KURALLARI — ASLA İHLAL ETME

### concept.statement
Markanın çekirdek vaadi. Sadece BU markaya ait, tek cümle, somut.
İYİ: "Daha az şey, daha çok anlam." / "Sokaktan binince de güven." / "Gürültüyü sinyale çeviririz."
YASAK: "Kaliteli hizmet sunuyoruz", "Müşteri odaklı", "Yenilikçi çözüm", "Sektörün öncüsü"

### story.heading
Tagline değil, bir manifesto başlığı. Kısa, güçlü, markaya özel.

### story.body [tam olarak 2 paragraf string dizisi]
Kurucunun "neden"inden türet. Gerilim ve somut sahne kur.
Soyut sıfat dökme. En az bir gerçek detay/sahne/sayı olmalı.
Her paragraf 2-3 cümle.

### voice.traits [tam olarak 3 sıfat]
YASAK üçlü: "profesyonel, güvenilir, yenilikçi" — bu kombinasyonu ASLA kullanma.
Markaya özgü, beklenmedik ama doğru kombinasyon.

### voice.we [tam olarak 2 replik, tırnak içinde]
Birebir kullanılabilecek gerçek cümle. "İlke açıklaması" değil, konuşma dili.

### voice.weNot [tam olarak 2 replik, tırnak içinde]
Bu sektörün GERÇEK tuzakları — rakiplerin düştüğü ton.
Rastgele kötü cümle değil — bu markanın reddettiği spesifik dil.

## SWAP TESTİ
Marka adını başka bir markayla değiştir. Hâlâ doğruysa metin jeneriktir — yeniden yaz.

## LOGO VE GÖRSELLER — SVG ÜRET (ZORUNLU)

### logo.primary
Marka için modern, minimal bir SVG logo üret. Kural:
- viewBox="0 0 800 300" veya "0 0 600 200" — yatay format
- Marka adı büyük harf, bold, letter-spacing negatif (sıkışık, güçlü)
- Accent renk ile 1-2 geometrik detay (ince çizgi, nokta, dikdörtgen, daire segmenti)
- Font: font-family içinde Helvetica Neue, Arial Black, Arial, sans-serif sırasıyla
- Zemin: primary_color (bg rengi)
- Metin: text rengi
- SVG'yi `data:image/svg+xml;base64,` formatında base64 encode edip yaz

### logo.icon
Marka için kare (320x320) monogram/ikon SVG:
- Marka baş harfleri veya kısaltması (1-2 harf)
- Geometrik çerçeve (ince kare veya daire kontur)
- Base64 encoded data URI

### applications (en az 2 kart)
Her uygulama için 1:1 Instagram post formatında (1080x1080) SVG mockup:
- Post 1: büyük statement metin + marka adı + accent shape
- Post 2: grid/pattern overlay + içerik farklı kompozisyon
- Her img alanı base64 encoded SVG data URI

## BASE64 ENCODİNG KURALI
SVG string → base64 encode → "data:image/svg+xml;base64,{base64_string}" formatı
JavaScript'te: btoa(unescape(encodeURIComponent(svgString))) — ama sen doğrudan base64'ü hesapla.

## KRİTİK XML KURALI — ASLA İHLAL ETME
SVG geçerli XML olmalı. Kapama etiketleri MUTLAKA `/` içermeli:
- DOĞRU: `<text x="40" y="180" ...>KAVA</text>`
- YANLIŞ: `<text x="40" y="180" ...>KAVA<text>` ← kapama etiketi bozuk
Her açılan tag kapanmalı: `<text>` → `</text>`, `<tspan>` → `</tspan>`, `<g>` → `</g>`.

## ÇIKTI FORMAT
Sadece geçerli JavaScript window.BRAND = { ... }; bloğu.
Başka hiçbir şey yazma (markdown kod bloğu, açıklama, vs. yok).
String değerlerde çift tırnak kullan.
Türkçe ve özel karakterler sorunsuz kullanılabilir."""


def _build_user_prompt(brief: dict) -> str:
    energy = str(brief.get("energy", "cinematic")).lower()
    energy = "playful" if "playful" in energy else "cinematic"

    primary  = brief.get("primary_color", "#C9A25A")
    secondary = brief.get("secondary_color", "#8B8B7A")
    accent2  = brief.get("accent_color") or secondary

    if energy == "playful":
        bg, surface, text, muted = "#FFFFFF", "#F5F5F5", "#1A1A1A", "#666666"
    else:
        bg, surface, text, muted = "#0A0909", "#141210", "#F2EDE4", "#7A756C"

    font_display = brief.get("font_display", "Inter")
    font_body    = brief.get("font_body", "Inter")

    def _slug(n): return n.strip().replace(" ", "+")
    gf_url = (
        f"https://fonts.googleapis.com/css2?"
        f"family={_slug(font_display)}:wght@400;600;700"
        f"&family={_slug(font_body)}:wght@400;500;600"
        f"&display=swap"
    )

    brand_name = brief.get("brand_name", "BRAND")
    tagline    = brief.get("tagline", "")

    # Brief'i prompte eklerken _*_b64 alanlarını çıkar (dev büyük, token israfı)
    brief_clean = {k: v for k, v in brief.items() if not k.startswith("_")}

    # Beş renk paleti — brief'ten al
    palette_colors = [
        {"name": "Ana Vurgu",    "hex": primary,   "role": "Accent / Marka rengi"},
        {"name": "İkincil",      "hex": secondary,  "role": "İkincil vurgu"},
        {"name": "Vurgu 2",      "hex": accent2,    "role": "Üçüncül vurgu"},
        {"name": "Zemin",        "hex": bg,         "role": "Arka plan"},
        {"name": "Metin",        "hex": text,       "role": "Ana metin"}
    ]

    # Palette adlarını brief'ten al varsa
    mood = brief.get("mood_words", [])

    return f"""Aşağıdaki marka brief JSON'undan window.BRAND config bloğunu üret.

MARKA BRİEF:
{json.dumps(brief_clean, ensure_ascii=False, indent=2)}

GÖREV: Aşağıdaki iskelet JSON'u doldur. İskelet yapısını DEĞİŞTİRME — sadece {{DOLDUR}} etiketli yerleri yaz.
Başka key ekleme, iç içe obje ekleme, yapıyı değiştirme. TAM olarak bu şemayı kullan.

window.BRAND = {{
  "name": "{brand_name}",
  "tagline": "{tagline if tagline else '{{DOLDUR: kısa vurucu slogan — max 7 kelime}}'}",
  "domain": "",
  "energy": "{energy}",

  "colors": {{
    "bg":      "{bg}",
    "surface": "{surface}",
    "text":    "{text}",
    "muted":   "{muted}",
    "accent":  "{primary}",
    "accent2": "{accent2}"
  }},

  "palette": [
    {{"name": "{{DOLDUR: marka renginin Türkçe şiirsel ismi}}",  "hex": "{primary}",   "role": "Ana vurgu"}},
    {{"name": "{{DOLDUR: ikincil renk ismi}}",                   "hex": "{secondary}",  "role": "İkincil"}},
    {{"name": "{{DOLDUR: üçüncül renk ismi}}",                   "hex": "{accent2}",    "role": "Vurgu 2"}},
    {{"name": "{{DOLDUR: zemin rengi ismi}}",                    "hex": "{bg}",         "role": "Zemin"}},
    {{"name": "{{DOLDUR: metin rengi ismi}}",                    "hex": "{text}",       "role": "Metin"}}
  ],

  "type": {{
    "googleFonts":  "{gf_url}",
    "headingFont":  "'{font_display}', sans-serif",
    "bodyFont":     "'{font_body}', sans-serif",
    "headingName":  "{font_display}",
    "bodyName":     "{font_body}",
    "headingNote":  "Display / Başlık",
    "bodyNote":     "Metin / Arayüz",
    "sampleWord":   "Aa"
  }},

  "logo": {{
    "primary": "{{DOLDUR: data:image/svg+xml;base64,BASE64 — viewBox=0 0 800 280, marka adı '{brand_name}' büyük/bold/negatif letter-spacing, zemin={bg}, metin={text}, accent={primary}, 1-2 geometrik detay, font-family Arial Black/Helvetica Neue}}",
    "icon":    "{{DOLDUR: data:image/svg+xml;base64,BASE64 — 320x320 kare, baş harfler monogram, geometrik çerçeve, aynı renk paleti}}",
    "mono":    "{{DOLDUR: data:image/svg+xml;base64,BASE64 — logo.primary'nin tek renkli versiyonu, sadece {text} rengi}}",
    "inverse": "",
    "clearSpace": "Logo etrafında minimum boşluk korunmalıdır.",
    "misuse": ["Germe veya oranı bozma", "Onaysız renk değiştirme", "Gölge veya efekt ekleme", "Düşük kontrastlı zemine yerleştirme"]
  }},

  "story": {{
    "eyebrow": "Hikaye",
    "heading": "{{DOLDUR: manifesto başlığı — tagline değil, gerilim veya dönüşüm cümlesi, max 6 kelime}}",
    "body": [
      "{{DOLDUR: 2-3 cümle — kurucunun 'neden'i, somut sahne veya gerçek detay}}",
      "{{DOLDUR: 2-3 cümle — markanın nasıl çalıştığı, fark yaratma biçimi}}"
    ]
  }},

  "concept": {{
    "eyebrow": "Konsept",
    "statement": "{{DOLDUR: tek cümle öz fikir — SWAP TESTİ: marka adını değiştirince hâlâ doğruysa yeniden yaz}}",
    "body": "{{DOLDUR: 1-2 cümle bu fikri açıkla}}"
  }},

  "voice": {{
    "traits": ["{{DOLDUR: sıfat 1}}", "{{DOLDUR: sıfat 2}}", "{{DOLDUR: sıfat 3}}"],
    "we":    ["{{DOLDUR: bu markanın ağzından gerçek replik 1 — tırnak içinde}}", "{{DOLDUR: gerçek replik 2 — tırnak içinde}}"],
    "weNot": ["{{DOLDUR: bu markanın reddettiği sektör tuzağı 1 — tırnak içinde}}", "{{DOLDUR: reddedilen ton 2 — tırnak içinde}}"]
  }},

  "applications": [
    {{
      "img": "{{DOLDUR: data:image/svg+xml;base64,BASE64 — 1080x1080 Instagram post SVG, büyük statement metin, zemin={bg}, accent geometri, marka adı '{brand_name}'}}",
      "caption": "Sosyal Medya"
    }},
    {{
      "img": "{{DOLDUR: data:image/svg+xml;base64,BASE64 — 1080x1080 Instagram post 2, farklı kompozisyon, grid/pattern, farklı tipografi hiyerarşisi}}",
      "caption": "İçerik Şablonu"
    }}
  ],

  "credit": "Üretildi: BrandGen by Windy Venture Capital"
}};

KALİTE KURALLARI (ihlal etme):
- story.heading: Tagline kopyası değil — bir gerilim veya dönüşüm anı
- concept.statement: Swap testini geç — sadece bu markaya özgü olmalı
- voice.we / weNot: Gerçek konuşma dili, ilke açıklaması değil
- Tüm SVG'ler geçerli XML — her açılan tag kapanmalı (</text>, </g>, </tspan>)
- SVG base64 encoding: Python'daki base64.b64encode(svg.encode()).decode() ile aynı

Sadece window.BRAND = {{ ... }}; bloğunu yaz. {{DOLDUR}} ifadelerini gerçek içerikle değiştir. Başka hiçbir şey ekleme."""


def generate_html_preview(brief: dict) -> tuple:
    """
    Brief JSON → Claude API (Haiku) → window.BRAND config → tam HTML string.
    no1-brandkit kalitesinde, markaya özgü dinamik içerik üretir.
    Döner: (html_str, token_usage_dict)
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # Claude API — Haiku (hız + maliyet dengesi, kalite yeterli)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8192,  # SVG logo+uygulamalar için artırıldı
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(brief)}],
    )

    html_token_usage = {
        "input_tokens":  response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }

    brand_config = response.content[0].text.strip()

    # Markdown code block temizle (bazen ``` içinde döner)
    if brand_config.startswith("```"):
        lines = brand_config.split("\n")
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        brand_config = "\n".join(lines[1:end])

    # SVG XML hata düzeltici — AI üretimindeki kapama etiketi hatalarını onar
    brand_config = _fix_svg_in_config(brand_config)

    # Template'deki <script id="brand-config"> içeriğini değiştir
    # NOT: Template'deki HTML comment'den "<script id="brand-config">" kaldırıldı,
    # bu yüzden basit regex güvenli (tek match = gerçek script tag).
    script_pattern = r'(<script id="brand-config">)([\s\S]*?)(</script>)'
    new_html = re.sub(
        script_pattern,
        lambda m: m.group(1) + "\n" + brand_config + "\n" + m.group(3),
        template,
        count=1,
    )

    # Eğer regex tutmadıysa (güvenlik) window.BRAND bloğunu değiştir
    if new_html == template:
        old_pattern = r'window\.BRAND\s*=\s*\{[\s\S]*?\};'
        new_html = re.sub(old_pattern, brand_config, template, count=1)

    # Title güncelle
    brand_name = brief.get("brand_name", "BRAND")
    new_html = new_html.replace(
        "<title>Brand — {{title}}</title>",
        f"<title>Brand — {brand_name}</title>",
    )
    new_html = new_html.replace("Brand — {{title}}", f"Brand — {brand_name}")

    # Watermark overlay (preview için)
    energy = str(brief.get("energy", "cinematic")).lower()
    if "playful" in energy:
        wm_color        = "rgba(0,0,0,0.09)"
        wm_stripe_color = "rgba(0,0,0,0.03)"
    else:
        wm_color        = "rgba(255,255,255,0.07)"
        wm_stripe_color = "rgba(255,255,255,0.025)"

    watermark_css = f"""
<style id="brandgen-watermark">
.brandgen-wm {{
  position: fixed; inset: 0; z-index: 9999; pointer-events: none;
  background: transparent;
}}
.brandgen-wm::before {{
  content: "BRANDGEN PREVIEW · BRANDGEN PREVIEW · BRANDGEN PREVIEW";
  position: absolute; font-size: 16px; font-weight: 700;
  letter-spacing: 0.3em; color: {wm_color};
  transform: rotate(-35deg); white-space: nowrap;
  text-shadow: none; font-family: monospace;
  background: repeating-linear-gradient(
    -35deg,
    transparent, transparent 60px,
    {wm_stripe_color} 60px, {wm_stripe_color} 61px
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
    """
    HTML üret → Supabase Storage'a yükle → public URL döner.
    (Pipeline preview_html'i direkt DB'ye yazıyor; bu fonksiyon opsiyonel fallback.)
    """
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
