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
from generators.logo_generator import select_logo_mono_png  # primary + icon artık Sonnet SVG

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

_SVG_SYSTEM = """Sen dünya klasmanında bir marka kimlik tasarımcısısın — Collins, Bureau Borsche ve Pentagram'dan geçmiş biri.
Strateji direktörü, kreatif direktör ve tasarım direktörü üç ayrı aşamada karar verdi. Bu kararlar sana "AJANS KARAR BRİEFİ" başlığıyla gelecek.
Görevin: her tasarım kararını SAF SVG'ye çevirmek. Template yok. Kalıp yok. Her marka özgün.

TAM OLARAK 4 SVG BLOĞU üreteceksin: logo_primary, logo_icon, app1, app2
Bloklar arasında başka HİÇBİR ŞEY yazma.

ÇIKTI FORMAT — her SVG için bu bloğu kullan:
===SVG:logo_primary===
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 280">
  ... tasarım ...
</svg>
===END===

===SVG:logo_icon===
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320">
  ... tasarım ...
</svg>
===END===

===SVG:app1===
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080">
  ... tasarım ...
</svg>
===END===

===SVG:app2===
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080">
  ... tasarım ...
</svg>
===END===

SVG TEKNİK KURALLAR (ihlal = geçersiz tasarım):
- Her açılan tag kapanmalı: <text>KAYA</text> ✓ / <text>KAYA<text> ✗
- Türkçe karakterler (İ Ş Ğ Ü Ö Ç) direkt UTF-8 — dönüştürme, base64 yok
- viewBox dışına taşan element YOK
- font-family SVG içinde belirtme — font-family="sans-serif" yeterli
- Türkçe kelimeyi ASLA letter-by-letter ayırma → <text>VOLKAN</text> (tek element)
- Her <text> elementi için dominant-baseline="auto" ve text-anchor="start/middle/end" belirt

UYGULAMA SIRASI:
1. "AJANS KARAR BRİEFİ" bölümündeki her tasarım kararını oku
2. O kararları eksiksiz uygula — yorumlama, direkt çevir
3. Brief'te yazan her şeyi ekle, yazmayanı ekleme

SWAP TESTİ — bu teslimatta zorunlu:
"Bu logo_primary başka bir markaya koyabilir miyim?" → Evet ise baştan yaz.
"Bu logo_icon başka bir sektörde çalışır mı?" → Evet ise baştan yaz.
Her tasarım bu markaya ÖZGÜ olmalı. Jenerik = geçersiz.

KESİN YASAKLAR (bunları yapan tasarım geçersiz sayılır):
- Harf/monogram etrafında dörtgen veya daire çerçeve — 2010 tarzı, yasaklı
- "marka adı + yatay çizgi + küçük altyazı" kombinasyonu — template, değil tasarım
- İnce dekoratif çizgi, nokta serpme, rastgele geometrik accent
- Zemin üzerine sadece düz metin — başka bir karar olmadan
- Placeholder metinler: "BRAND IDENTITY", "EST. 2024", "SINCE", "LLC"
- Gradient fill (linear-gradient, radial-gradient) — düz renkler kullan

LOGO_PRIMARY için (800x280) — wordmark kuralı:
Marka adı tek seyirde okunmalı. Ama nasıl gösterildiği kararı burada.
Seçenekler (brief'te hangisi belirtildiyse):
• Renk bloğu kesiyor — dikdörtgen primary renk, içinde beyaz/koyu wordmark
• Büyük harf parçalanıyor — ilk veya son harf ayrışıyor, farklı renk/ağırlık alıyor
• Wordmark + güçlü accent element — accent shape harften türemiş olmalı
• Diagonal şerit altında/üstünde metin — çapraz renk alanı
Kendi gerekçen yoksa: "Brief'te yazan kararı uygula."

LOGO_ICON için (320x320) — monogram kuralı:
YASAK: harf + kare/daire çerçeve (FedEx'in çerçevesi yok — FedEx'in içinde ok var)
DOĞRU: Harfin KENDI FORMUNDAN türeyen sembol.
• Harfi kes — kesik boşluk anlam taşısın (Apple logosundaki ısırık gibi)
• İki harf arasında zaten var olan boşluktan form çıkar (FedEx'in oku gibi)
• Harfin iç boşluğunu kullan (B'nin içindeki yuvarlaklar bir şeye dönüşsün)
• Harfleri birleştir — birleşim noktasından yeni form doğsun
Locked icon concept brief'te belirtilmişse: O talimatı direkt uygula.

STÜDYO DNA UYGULAMASI:
- Collins → Renk BLOK olarak konuşur. Grid görünür. Harf sisteme girer.
- Bureau Borsche → Tipografi grafik obje. Dev font, kültürel referans, sürpriz oran.
- Sagmeister & Walsh → Kural kır. Beklenmedik ölçek, çakışma kabul, sürpriz angle.
- Pentagram → Anlam yüklü minimal. Negatif boşluk çalışır, her şeyin sebebi var.
- Landor → Güven veren form. Net hiyerarşi, temiz oran, kurumsal güç.
- Wolff Olins → İsim sistem olur. Renk kimlik taşır, modüler yapı.

UYGULAMA GÖRSELLERİ — editorial design enerjisi:
- app1 (1080x1080): Tagline'dan 2-3 kelime. Her kelime ayrı satır, devasa font.
  Poster gibi çalışır, reklam gibi değil. Güçlü renk bloğu veya diagonal.
- app2 (1080x1080): app1'den tamamen farklı dil. stroke-only büyük wordmark (fill="none").
  Arka planda konseptten türeyen geometrik grid. Renk aksan bloğu köşede.

Her element için sor: "Bu neden burada, ne anlatıyor?" — cevap yoksa sil."""


def _ascii_safe(name: str) -> str:
    """
    SVG <text> için marka adını güvenli hale getir.
    Türkçe büyük harfleri ASCII eşdeğerine çevir (İ→I, Ş→S, vb.)
    Böylece font rendering problemi yaşanmaz.
    """
    tr_map = str.maketrans("İĞÜŞÖÇığüşöç", "IGUSSOigusso")
    return name.translate(tr_map)


# ══════════════════════════════════════════════════════════════════════════════
# AJANS PİPELİNE — 3 Rol + 1 İkon Pre-Call + 1 SVG Üretimi
#
# Call 1 — Strateji Direktörü  (~250 token): marka özü, boşluk, gerilim
# Call 2 — Kreatif Direktör    (~400 token): stüdyo seçimi, 5 grafik karar
# Call 3 — Tasarım Direktörü  (~900 token): her SVG için kesin teknik brief
# Call 4 — İkon Kilitleme      (~150 token): anatomik ikon talimatı (mevcut)
# Call 5 — Uygulayan Sonnet   (14000 token): direktörlerin brief'ini SVG'ye çevir
#
# Maliyet eki: ~$0.008–0.012 (toplam ~$0.07–0.09/üretim)
# ══════════════════════════════════════════════════════════════════════════════

_STRATEGY_SYSTEM = """Sen bir marka strateji direktörüsün. Wolff Olins, Landor, Interbrand geçmişi.
Brand brief'i okuyup 3 kesin çıktı üret — strateji kararı, tasarım değil.

ÇIKTI FORMAT (sadece bu 3 satır, başka hiçbir şey yazma):
ÖZSÖZ: <bu markanın tek cümlelik varoluş nedeni — şirket anlatımı değil, insan hayatındaki yeri>
BOŞLUK: <kategorideki görsel/duygusal boşluk — rakipler ne yapıyor, bu marka nerede duracak>
GERİLİM: <bu markanın içindeki yaratıcı gerilim — birlikte var olan iki karşıt değer>"""


def _run_strategy_director(brief: dict, client) -> str:
    """Call 1: Strateji direktörü — marka özü, boşluk, gerilim. ~250 token."""
    name    = brief.get("brand_name", "")
    sector  = brief.get("sector", "")
    tagline = brief.get("tagline", "")
    concept = brief.get("concept_statement", "")
    story   = brief.get("brand_story", "")[:300]
    voice   = brief.get("brand_voice", "")[:200]

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=250,
            system=_STRATEGY_SYSTEM,
            messages=[{"role": "user", "content": (
                f"Marka: {name}\nSektör: {sector}\nTagline: {tagline}\n"
                f"Konsept: {concept}\nHikaye: {story}\nSes/ton: {voice}\n\n"
                f"Strateji analizini üret."
            )}],
        )
        return resp.content[0].text.strip()
    except Exception:
        return f"ÖZSÖZ: {concept}\nBOŞLUK: Sektörde özgün görsel konum\nGERİLİM: Hız ve güven"


_CREATIVE_DIR_SYSTEM = """Sen kreatif direktörüsün. Bureau Borsche, Collins, Sagmeister&Walsh, Pentagram geçmişi.
Sana gelen her marka için kural kıran, kalıp reddeden, özgün grafik kararlar veriyorsun.

TEMEL KURAL: Jenerik çözüm = başarısız çözüm. Bu brief'e ve sadece bu markaya özgü 5 karar.

SWAP TESTİ ZORUNLU: Her kararından önce sor: "Bu karar başka bir markaya da verilmiş olabilir mi?" → Evet ise değiştir.

STÜDYO SEÇİMİ KURALI:
- Collins seç: Renk sistemi kimlik taşıyorsa, grid dominant olacaksa
- Bureau Borsche seç: Tipografi grafik obje gibi çalışacaksa, kültürel referans varsa
- Sagmeister&Walsh seç: Kural kırılacaksa, beklenti tersine çevrilecekse
- Pentagram seç: Negatif boşluk anlam taşıyacaksa, minimal ama derin olacaksa
- Landor seç: Güven + otorite + kurumsal güç gerekiyorsa
- Wolff Olins seç: Sistem tasarımı, modüler yapı, renk kimlik olacaksa

ÇIKTI FORMAT (sadece bu 5 satır — açıklama yazma, karar yaz):
STÜDYO: <stüdyo adı — neden bu marka için bu stüdyo, tek cümle>
WORDMARK: <bu markaya ÖZGÜ tek grafik karar — ne yapılacağını söyle, nasıl göründüğünü tarif et>
İKON: <harfin anatomisinden türeyen özgün dönüşüm — ekleme değil dönüştürme>
UYGULAMA1: <1080x1080 poster — hangi kelime/kelimeler, dizilim, grafik dil, renk, beklenmedik unsur>
UYGULAMA2: <1080x1080 tamamen farklı dil — stroke, pattern, köşe aksanı, bu markanın DNA'sı>"""


def _run_creative_director(brief: dict, strategy_output: str, client) -> str:
    """Call 2: Kreatif direktör — stüdyo seçimi + 5 grafik karar. ~400 token."""
    name     = brief.get("brand_name", "")
    primary  = brief.get("primary_color", "#C9A25A")
    secondary = brief.get("secondary_color", "#8B8B7A")
    energy   = brief.get("energy", "cinematic")
    logo_concept = brief.get("logo_concept", "")
    visual_language = brief.get("visual_language", "")
    tagline  = brief.get("tagline", "")

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=_CREATIVE_DIR_SYSTEM,
            messages=[{"role": "user", "content": (
                f"=== STRATEJİ ANALİZİ ===\n{strategy_output}\n\n"
                f"=== BRAND BRIEF ===\n"
                f"Marka: {name}\nAna renk: {primary} | İkincil: {secondary}\n"
                f"Enerji: {energy}\nLogo konsepti: {logo_concept}\n"
                f"Görsel dil: {visual_language}\nTagline: {tagline}\n\n"
                f"Grafik kararlarını ver."
            )}],
        )
        return resp.content[0].text.strip()
    except Exception:
        return (
            f"STÜDYO: Pentagram — sektöre uygun özgün form\n"
            f"WORDMARK: Renk bloğu içinde cesur metin\n"
            f"İKON: İlk harfin anatomisinden türeyen form\n"
            f"UYGULAMA1: Tagline büyük, tek kelime her satırda\n"
            f"UYGULAMA2: Stroke-only wordmark + geometrik grid"
        )


_DESIGN_DIR_SYSTEM = """Sen bir tasarım direktörüsün — ajansın son kalite kapısısın. Her tasarım buradan geçmeden teslim edilmez.
Strateji + kreatif kararları aldın. Tasarımcıya direkt teslim edilecek SVG teknik brief yaz.
Tasarımcı yorumlamıyor — direkt uygulayacak. Koordinat, renk, form, oran — hepsi net.

ÇIKTI FORMAT (4 bölüm — başka hiçbir şey yazma):

LOGO_PRIMARY:
[800x280 viewBox. Wordmark için net SVG talimatı.
Hangi grafik karar: renk bloğu mu (dikdörtgen x/y/width/height belirt, renk), diagonal mı, harf ayrışması mı?
Metin x/y koordinatları, font-size (max limit aşılmaz), font-weight, fill rengi.
Arka plan fill rengi (bg_color).
YASAK: sadece düz metin — mutlaka grafik bir karar var.]

LOGO_ICON:
[320x320 viewBox. Harfin anatomisinden türeyen dönüşüm.
Hangi harf, harfin hangi bölümü nasıl kesiliyor veya dönüştürülüyor.
Kesim koordinatları (polygon/path/clip), renk katmanları (fill renk, bg renk).
Ekleme değil — harfin kendi formu dönüşüm geçiriyor.]

APP1:
[1080x1080 viewBox. Tagline'dan 2-3 kelime. Her kelimenin y koordinatı, font-size (max sınır belirtilecek), font-weight="900", fill rengi.
Arka planda: hangi renk bloğu (x/y/width/height), diagonal şerit mi (polygon koordinatları), renk.
Alt kısımda marka adı: y koordinatı, font-size 60-80px, fill rengi.]

APP2:
[1080x1080 viewBox. Stroke-only wordmark: font-size (max sınır), fill="none", stroke rengi, stroke-width kaç px.
Arka planda pattern tipi (grid/diagonal/radial), renk, opacity değeri.
Köşe renk aksanı: hangi köşe, rect koordinatları, renk, boyut.]"""


def _run_design_director(brief: dict, strategy_output: str, creative_output: str, client) -> str:
    """Call 3: Tasarım direktörü — her SVG için koordinat düzeyinde teknik brief. ~900 token."""
    name      = brief.get("brand_name", "BRAND")
    name_len  = max(len(name), 1)
    primary   = brief.get("primary_color", "#C9A25A")
    secondary = brief.get("secondary_color", "#8B8B7A")
    accent2   = brief.get("accent_color") or secondary
    bg        = brief.get("bg_color", "#0F0D0C")
    energy    = str(brief.get("energy", "cinematic")).lower()
    text      = "#F2EDE4" if _is_dark(bg) else "#1A1A1A"
    tagline   = brief.get("tagline", "")
    first_letter = name[0] if name else "?"
    max_font_logo = min(90, int(480 / (name_len * 0.65)))
    max_font_app2 = min(200, int(860 / (name_len * 0.65)))

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=900,
            system=_DESIGN_DIR_SYSTEM,
            messages=[{"role": "user", "content": (
                f"=== STRATEJİ ===\n{strategy_output}\n\n"
                f"=== KRATİF KARARLAR ===\n{creative_output}\n\n"
                f"=== TEKNİK PARAMETRELER ===\n"
                f"Marka adı: {name} ({name_len} karakter) | İlk harf: {first_letter}\n"
                f"Zemin: {bg} | Metin: {text} | Ana: {primary} | İkincil: {secondary} | Aksan: {accent2}\n"
                f"Tagline: {tagline}\n"
                f"Logo max font-size: {max_font_logo}px (800px genişlik, {name_len} karakter)\n"
                f"App2 stroke wordmark max font-size: {max_font_app2}px\n\n"
                f"Her SVG için kesin teknik talimat yaz. Tasarımcı direkt uygulayacak."
            )}],
        )
        return resp.content[0].text.strip()
    except Exception:
        return ""  # Fallback: boş — SVG sistem prompt'u yine de çalışır


# ── Pre-call: İkon konsepti kilitleme ────────────────────────────────────────
# SVG üretiminden ÖNCE çalışır — sadece ikon için ayrı bir Sonnet çağrısı.
# Mevcut logo_icon_svg_brief'i alır, geometrik olarak kilitlemiş tek cümle döndürür.
# Amaç: 20+ alan arasında boğulan brief yerine, ikon için tam odak.
# Maliyet: ~$0.003–0.005/üretim ek (~%10–15 artış). Fallback: mevcut brief.

_PRE_CALL_SYSTEM = """Sen marka kimlik direktörüsün. Görevin: tek bir ikon için geometrik olarak kilitlemiş SVG çizim talimatı üretmek.

KURAL — anatomik dönüşüm (eklenti değil):
• Apple modeli: Harfin BİR BÖLÜMÜNÜ KES → kesik boşluk anlam taşısın
• FedEx modeli: İki harf ARASINDA zaten var olan negatif boşluktan form çıkar
• Birleşim modeli: İki harfi BİRLEŞTİR → harflerin birleşiminden yeni form doğsun

YASAK:
✗ Harfin yanına / üstüne / etrafına şekil eklemek
✗ Jenerik sektör sembolü (saat, ok, konum pimi, şimşek, daire/kare çerçeve)
✗ "... ekle", "... yapıştır", "... koy" gibi eklenti ifadeleri

SWAP TESTİ — zorunlu kontrol: Bu ikon başka bir kurye/hız/teslimat markasına koysan yine çalışır mı? → Evet ise baştan yaz.

ÇIKTI: Sadece tek cümle talimat. Geometrik, koordinatlı, SVG'ye direkt çevrilebilir. Açıklama veya gerekçe yazma."""


def _generate_locked_icon_concept(brief: dict, client) -> str:
    """
    Pre-call: İkon konseptini SVG üretiminden önce kilitle.
    Hata durumunda mevcut brief'e fallback yapar — pipeline kırılmaz.
    """
    name = brief.get("brand_name", "")
    first_letter = name[0] if name else ""
    logo_concept = brief.get("logo_concept", "")
    existing_brief = brief.get("logo_icon_svg_brief", "")
    sector = brief.get("sector", "")

    user_content = (
        f"Marka: {name}\n"
        f"Sektör: {sector}\n"
        f"İlk (veya en güçlü) harf: {first_letter}\n"
        f"Logo konsepti: {logo_concept[:300]}\n"
        f"Mevcut talimat (geliştir veya tamamen yeniden yaz): {existing_brief[:300]}\n\n"
        f"320×320 ikon için tek cümle SVG çizim talimatı üret. "
        f"'{first_letter}' harfinin anatomisinden yola çık. "
        f"Harfi KES, BİRLEŞTİR veya iç boşluğunu dönüştür — asla dışarıdan ekleme."
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=150,
            system=_PRE_CALL_SYSTEM,
            messages=[{"role": "user", "content": user_content}],
        )
        result = response.content[0].text.strip()
        sentences = [s.strip() for s in result.replace("\n", " ").split(".") if s.strip()]
        return (sentences[0] + ".") if sentences else result
    except Exception:
        return existing_brief  # fallback: mevcut brief


def _build_svg_prompt(brief: dict, design_output: str = "") -> str:
    name = brief.get("brand_name", "BRAND")
    # SVG UTF-8'i destekler — orijinal Türkçe ismi kullan, dönüştürme
    # _ascii_safe sadece font-size hesabı için (karakter sayısı aynı)
    name_safe = name  # display için orijinal isim
    first_letter = name[0] if name else "?"  # İkon için anatomi noktası
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
    max_font_app1 = min(160, int(900 / (max_tagline_word_len * 0.65)))

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

    # Ajans brief'i inject — varsa en üste, tasarımcı önce bunu okur
    agency_block = ""
    if design_output:
        sep = "=" * 62
        agency_block = (
            f"{sep}\n"
            f"AJANS KARAR BRİEFİ\n"
            f"Strateji + Kreatif + Tasarım Direktörü — Direkt Uygula\n"
            f"{sep}\n"
            f"{design_output}\n"
            f"{sep}\n\n"
        )

    # Locked icon concept — brief'ten al (generate_html_preview tarafından inject edildi)
    locked_icon_brief = brief.get("logo_icon_svg_brief", logo_concept)

    return f"""{agency_block}MARKA: {name_safe}
STÜDYO DNA: {studio_label} ({studio_sector}) → {studio_logo_guide}
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

4 SVG üreteceksin. Sırayla:

===SVG:logo_primary===
viewBox="0 0 800 280". Zemin: {bg}.
Wordmark: "{name_safe}"
FONT-SIZE SINIRI: {name_len} karakter → maksimum {max_font_logo}px. Bu sınırı AŞMA (taşar).
AJANS KARAR BRİEFİ'nde LOGO_PRIMARY ve WORDMARK bölümlerini uygula.
Stüdyo: {studio_label} → {studio_logo_guide}
YASAK: düz zemin üzerine sadece metin. Mutlaka bir grafik karar var (renk bloğu/diagonal/form/ölçek oynaması).
===END===

===SVG:logo_icon===
viewBox="0 0 320 320". Zemin: {bg}.
İlk harf: "{first_letter}" — bu harfin anatomisinden türeyen sembol.
KİLİTLİ İKON KONSEPT (tasarım direktörü kararı — direkt uygula): {locked_icon_brief}
YASAK: harf + çerçeve (kare/daire). Harfin kendi formu dönüşüm geçirmeli.
AJANS KARAR BRİEFİ'nde LOGO_ICON bölümünü uygula.
===END===

===SVG:app1===
viewBox="0 0 1080 1080". Zemin {bg}.
Tagline'dan 2-3 kelime BÜYÜK, her kelime ayrı <text> satırında: "{tagline[:35]}"
FONT-SIZE SINIRI: En uzun kelime {max_tagline_word_len} karakter → maksimum {max_font_app1}px. Bunu AŞMA.
font-weight="900", {text} rengi. Her kelime için y değerini kademeli artır (300, 300+font-size, ...).
Alt kısımda "{name_safe}" {primary} rengiyle, daha küçük (font-size 60-80).
Güçlü renk bloğu veya diagonal şerit — {primary} veya {secondary} kullan.
Sol üst veya sağ alt köşeye küçük geometrik aksan.
===END===

===SVG:app2===
viewBox="0 0 1080 1080". app1'den tamamen farklı kompozisyon.
"{name_safe}" büyük stroke-only (fill="none", stroke="{primary}", stroke-width="10", font-size {max_font_app2}px MAX).
FONT-SIZE SINIRI: "{name_safe}" = {name_len} karakter → maksimum {max_font_app2}px. Bunu AŞMA.
Arka planda tekrarlayan geometrik grid veya pattern ({secondary} rengi, çok düşük opacity ~0.08).
Renk aksan bloğu (sağ alt veya sol üst köşe, {primary}).
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

    # ── Ajans Pipeline: 4 Pre-Call ────────────────────────────────────────────
    # Call 1: Strateji direktörü — marka özü, boşluk, gerilim
    strategy_output = _run_strategy_director(brief, client)
    # Call 2: Kreatif direktör — stüdyo seçimi, 5 grafik karar
    creative_output = _run_creative_director(brief, strategy_output, client)
    # Call 3: Tasarım direktörü — her SVG için koordinat düzeyinde teknik brief
    design_output = _run_design_director(brief, strategy_output, creative_output, client)
    # Call 4: İkon konseptini kilitle (mevcut pre-call)
    locked_icon = _generate_locked_icon_concept(brief, client)
    brief["logo_icon_svg_brief"] = locked_icon

    # ── Stüdyo label'ını creative_output'tan parse et (SVG prompt için inject) ─
    _studio_match = re.search(r'STÜDYO:\s*([A-Za-zÇŞĞÜÖçşğüöı &]+?)(?:\s*[—–-]|\s*$)', creative_output, re.MULTILINE)
    _studio_label = _studio_match.group(1).strip() if _studio_match else brief.get("studio_dna", {}).get("label", "")
    # Brief'e stüdyo label'ını yaz — _build_svg_prompt içinde kullanılır
    if _studio_label:
        brief.setdefault("studio_dna", {})["label"] = _studio_label

    # ── Python PIL: SADECE logo_mono (basit beyaz wordmark) ──────────────────
    # logo_primary ve logo_icon artık Sonnet SVG üretiyor — PIL kaldırıldı
    svgs = {
        "logo_mono": select_logo_mono_png(brief),
    }

    # ── SVG Üretimi: Sonnet — logo_primary, logo_icon ────────────────────────
    svg_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=10000,  # 4 SVG: logo_primary, logo_icon, app1, app2
        system=_SVG_SYSTEM,
        messages=[{"role": "user", "content": _build_svg_prompt(brief, design_output)}],
    )
    svg_raw = svg_response.content[0].text
    # Sonnet çıktısından logo_primary, logo_icon al
    sonnet_svgs = _extract_svgs(svg_raw, bg_color=brief["bg_color"])
    sonnet_svgs.pop("logo_mono", None)  # mono PIL'den geliyor, override etme
    svgs.update(sonnet_svgs)


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
