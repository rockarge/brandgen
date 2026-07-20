"""
image_generator.py — fal.ai Görsel Üretici

╔══════════════════════════════════════════════════════════════════════════════╗
║  2 TEM 2026 — Fable 5 audit sonrası mimari değişikliği (bkz.                 ║
║  brandgen-gorsel-audit-2tem2026.md + _knowledge/bekleyen-gorevler.md)        ║
║                                                                              ║
║  ESKİ: logo_primary + logo_tipo + logo_icon → Recraft v3 (3 çağrı)          ║
║  YENİ: logo_primary + logo_tipo artık BURADA ÜRETİLMİYOR.                   ║
║        html_preview.py bunları logo_generator.py'nin PIL fonksiyonlarından  ║
║        (select_logo_primary_png / select_logo_mono_png) alıyor.            ║
║  SEBEP (audit B1/B4): diffusion modelden "marka adını doğru yaz" istemek   ║
║  en yüksek başarısızlık oranlı görev türü — Türkçe karakterli isimlerde    ║
║  (İ→I, Ş→S ASCII stripping) logo baştan yanlış yazılıyordu. PIL render     ║
║  %100 doğru yazar, hiç diffusion riski taşımaz.                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

Ne yapar    : fal.ai API ile 3 görseli paralel üretir (önceden 5'ti).
              logo_icon        → Recraft v3 (vector_illustration) — soyut geometrik mark,
                                  exact-text istemiyor, diffusion için uygun bir görev.
              app1 + app2      → Flux Schnell (editorial, JPEG)

Kime bağlı  : html_preview.py → generate_all_images(brief) çağrısı
Döner       : {"logo_icon": ..., "app1": ..., "app2": ...}
Bozulursa   : Hatalı slot "" döner — html_preview pipeline kırılmaz, o slot gizlenir.
Maliyet     : Recraft ×1 (~$0.04) + Flux ×2 (~$0.006) = ~$0.05/üretim
              (önceki ~$0.13'ten düştü — 2 gereksiz/riskli Recraft çağrısı kaldırıldı)
Türkçe      : Marka adı _ascii_safe() ile temizlenir — sadece logo_icon fallback'inde
              kullanılıyor (ikon promptunda marka adı zaten harfe indirgeniyor, risk düşük).
"""

import os
import base64
import asyncio
import httpx
import fal_client


# ── Türkçe karakter koruma (sadece fallback prompt'larda, exact-text render'da DEĞİL) ──
def _ascii_safe(name: str) -> str:
    """İ→I, Ş→S vb. — AI prompt'a gönderilirken Türkçe karakter gitmesin."""
    tr_map = str.maketrans("İĞÜŞÖÇığüşöç", "IGUSSOigusso")
    return name.translate(tr_map)


def _safe_trunc(text: str, n: int) -> str:
    """Kelime ortasından kesmeden güvenli kısaltma (audit B2 fix).
    Önceki `text[:100]` kelimeyi ortadan kesip diffusion prompt'una gürültü katıyordu."""
    text = (text or "").strip()
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return cut if cut else text[:n]


def _color_note(hex_code: str, name: str = "") -> str:
    """Flux hex kodunu büyük ölçüde yok sayıyor (audit B6) — renk adı + hex birlikte yaz."""
    hex_code = hex_code or "#333333"
    return f"{name} ({hex_code})".strip() if name else hex_code


# ── Prompt üreticiler ─────────────────────────────────────────────────────────
# NOT (2 Tem 2026): logo_primary/logo_tipo prompt fonksiyonları kaldırıldı —
# bu slotlar artık diffusion'a hiç gitmiyor (bkz. dosya başlığı). logo_icon ve
# app1/app2 kalıyor çünkü bunlar "exact metin yaz" istemiyor, diffusion için
# uygun görevler.

# ── İKON STİL PRESET'LERİ (20 Tem 2026 — Görev 2A) ───────────────────────────
# Template'e bağlı sanat yönetimi: ikon, ANA logonun template kişiliğiyle aynı
# eksende üretilir (neo-minimal/retro/editorial/linework/corporate/playful).
# Anti-jenerik kuyruk HER prompta eklenir — "AI-polished sameness" trend anti-tezi
# (stil-referans.md §5 checklist ile örtüşür).
_ICON_STYLE_PRESETS = {
    "A": "Strong negative space, single carved geometric form.",
    "B": "Sharp diagonal energy, cut geometry, dynamic tension.",
    "C": "Unexpected duality, two-tone split geometry.",
    "D": "Systematic modular geometry, precise structure.",
    "E": "Minimal structural mark, generous whitespace.",
    "F": "Retro-futurist geometry, echo lines, arcade-era spirit.",
    "G": "Crafted thin linework, engraved editorial detail.",
    "H": "Artisanal linework badge spirit, hand-crafted line detail.",
    "I": "Conservative classic emblem geometry, balanced, trustworthy.",
    "J": "Soft rounded playful geometry, bouncy friendly shapes.",
}
_ANTI_GENERIC_TAIL = (
    "Distinctive and specific to the brand concept. "
    "NOT a generic gradient blob, NOT a swoosh, NOT an overused abstract orb. "
    # 20 Tem 2026 — "Pepito" canlı bulgusu: Sonnet mükemmel bir geometrik mark
    # tarif etmişti (kare kontur + köşeden taşan soru işareti) ama Recraft
    # bunu yok sayıp bir SAHNE çizdi: çocuk figürü + açık sandık + içinde
    # yemeğe benzeyen bir nesne. Eski kuyruk sadece SOYUT klişeleri
    # yasaklıyordu (blob/swoosh/orb), figüratif kaymayı hiç kapatmıyordu.
    "Flat vector mark only, a single centered symbol on a plain flat background. "
    "NO scene, NO character, NO mascot, NO human figure, NO depicted object, "
    "NO food, NO perspective, NO shadow, NO background illustration. "
    "Follow the described geometry exactly — it is a constructed mark, not a picture."
)


def _logo_icon_prompt(brief: dict, tpl: str = "") -> str:
    preset = _ICON_STYLE_PRESETS.get(tpl, "")
    # Önce Sonnet'in ürettiği Recraft-optimized prompt'u kullan
    fal_prompt = brief.get("fal_icon_prompt", "").strip()
    if fal_prompt and len(fal_prompt) > 30:
        return f"{fal_prompt} {preset} {_ANTI_GENERIC_TAIL}".strip()

    # Fallback: brief alanlarından generic prompt (audit B2 fix: kelime ortası kesme yok)
    name      = _ascii_safe(brief.get("brand_name", "BRAND"))
    letter    = name[0].upper() if name else "B"
    primary   = brief.get("primary_color", "#333333")
    bg        = brief.get("bg_color", "#FFFFFF")
    secondary = brief.get("secondary_color", "#888888")
    energy    = brief.get("energy", "cinematic")
    concept   = _safe_trunc(brief.get("concept_statement", ""), 100)
    mood      = ", ".join(brief.get("mood_words", [])[:2])

    style = "bold geometric playful" if energy == "playful" else "minimal premium geometric"
    return (
        f'App icon mark for "{name}" brand. '
        f'Abstract geometric symbol built from the letter "{letter}". '
        f'{concept + ". " if concept else ""}'
        f'{mood + ". " if mood else ""}'
        f'{style} design. '
        f'Colors: {_color_note(primary)} on {_color_note(bg)} background, {_color_note(secondary)} accent. '
        f'Square format. No text. Scalable geometric shape. Clean edges. '
        f'Vector illustration. {preset} {_ANTI_GENERIC_TAIL}'
    ).strip()


def _app1_prompt(brief: dict) -> str:
    # Önce Sonnet'in ürettiği İngilizce, Recraft/Flux-optimize prompt'u kullan (audit aksiyon #2)
    fal_prompt = brief.get("fal_app1_prompt", "").strip()
    if fal_prompt and len(fal_prompt) > 30:
        return fal_prompt

    # Fallback: brief alanlarından generic prompt (audit B2/B6 fix: güvenli kesme + isim+hex renk)
    name      = _ascii_safe(brief.get("brand_name", "BRAND"))
    primary   = brief.get("primary_color", "#333333")
    bg        = brief.get("bg_color", "#111111")
    energy    = brief.get("energy", "cinematic")
    sector    = brief.get("studio_dna", {}).get("sector", brief.get("sector", ""))
    mood_raw  = brief.get("mood_words", [])
    mood      = ", ".join(mood_raw[:3]) if mood_raw else ""

    if energy == "playful":
        atm = "vivid, colorful, joyful, bold graphic illustration, flat design, playful"
        style = "Bold flat illustration or graphic art. Bright saturated colors. Child-friendly, fun, energetic."
    else:
        atm = "cinematic, dramatic, premium, atmospheric"
        style = "Professional editorial photography or bold graphic composition."
    return (
        f'Editorial social media visual for "{name}"{(" — " + sector) if sector else ""}. '
        f'{atm} atmosphere. '
        f'{mood + ". " if mood else ""}'
        f'Dominant color: {_color_note(primary)} on {_color_note(bg)} background. '
        f'NO text. NO logo. NO watermark. '
        f'{style} '
        f'Square 1:1 format, high quality.'
    ).strip()


def _app2_prompt(brief: dict) -> str:
    # Önce Sonnet'in ürettiği İngilizce prompt'u kullan (audit aksiyon #2)
    fal_prompt = brief.get("fal_app2_prompt", "").strip()
    if fal_prompt and len(fal_prompt) > 30:
        return fal_prompt

    # Fallback: brief alanlarından generic prompt (audit B2/B6/B7 fix)
    name      = _ascii_safe(brief.get("brand_name", "BRAND"))
    secondary = brief.get("secondary_color", "#888888")
    bg        = brief.get("bg_color", "#111111")
    energy    = brief.get("energy", "cinematic")
    sector    = brief.get("studio_dna", {}).get("sector", brief.get("sector", ""))
    mood_raw  = brief.get("mood_words", [])
    mood      = ", ".join(mood_raw[1:4]) if len(mood_raw) > 1 else ""

    if energy == "playful":
        # B7 fix: sabit "anaokulu" sahnesi (confetti/art supplies) kaldırıldı —
        # sektörden bağımsız jenerik sahne yerine mood/sector'e bağlı kalıyor.
        atm = (
            "vibrant flat illustration, bold graphic art, colorful pattern composition. "
            f"Playful abstract shapes reflecting the brand's world"
            f'{(" for a " + sector) if sector else ""}. '
            f"Joyful, energetic mood. Bright {_color_note(secondary)} accents. "
            "NO characters. NO text. NO logo. Pure graphic surface pattern."
        )
    else:
        atm = (
            f"minimal bold editorial, abstract architectural composition. "
            f"Dominant {_color_note(secondary)} on {_color_note(bg)} background. "
            f"{mood + '. ' if mood else ''}"
            "NO text. NO logo. Pure abstract or conceptual art."
        )
    return (
        f'Brand identity visual for "{name}"{(" — " + sector) if sector else ""}. '
        f'{atm} '
        f'Square 1:1 format, high quality.'
    ).strip()


def _hero_prompt(brief: dict, dark: bool) -> str:
    """Mobil hero (1080×1920, 9:16) — foto-gerçekçi, fal.ai (Görev 2B).
    dark/light iki varyant: WVC brand-kit paritesindeki 'Mobile Hero Dark/Light'.
    Sonnet fal_hero_prompt üretirse o kullanılır, varyant notu eklenir."""
    base = brief.get("fal_hero_prompt", "").strip()
    variant = (
        "Dark moody variant, deep shadows, dominant dark background."
        if dark else
        "Light airy variant, bright soft background, high-key lighting."
    )
    if base and len(base) > 30:
        return f"{base} Vertical 9:16 mobile hero format. {variant} NO text. NO logo."

    name    = _ascii_safe(brief.get("brand_name", "BRAND"))
    primary = brief.get("primary_color", "#333333")
    bg      = brief.get("bg_color", "#111111")
    energy  = brief.get("energy", "cinematic")
    sector  = brief.get("studio_dna", {}).get("sector", brief.get("sector", ""))
    mood    = ", ".join(brief.get("mood_words", [])[:3])

    if energy == "playful":
        style = "Bold flat illustration, bright saturated colors, joyful energy."
    else:
        style = "Cinematic editorial photography, premium atmospheric depth."
    return (
        f'Vertical mobile app hero background for "{name}"'
        f'{(" — " + sector) if sector else ""}. '
        f'{mood + ". " if mood else ""}'
        f'Accent color {_color_note(primary)} against {_color_note(bg)} tones. '
        f'{style} {variant} '
        f'9:16 portrait format. NO text. NO logo. NO watermark. High quality.'
    ).strip()


# ── fal.ai çağrıları ──────────────────────────────────────────────────────────

def _bytes_to_data_uri(content: bytes, mime: str = "image/png") -> str:
    """Ham içerik → data URI. Magic byte sniffing — header'a güvenme,
    Recraft SVG → image/png yanlış header veriyor."""
    head = content.lstrip()[:10]
    if head.startswith(b"<svg") or head.startswith(b"<?xml"):
        mime = "image/svg+xml"
    elif content[:4] == b"\x89PNG":
        mime = "image/png"
    elif content[:2] in (b"\xff\xd8", b"\xff\xe0", b"\xff\xe1"):
        mime = "image/jpeg"
    b64 = base64.b64encode(content).decode("ascii")
    return f"data:{mime};base64,{b64}"


async def _download_b64(url: str, mime: str) -> str:
    """URL'den içeriği indir, data URI olarak döndür."""
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return _bytes_to_data_uri(resp.content, mime)


# ── İKON ÇOKLU-ADAY + OTOMATİK SEÇİM (20 Tem 2026 — Görev 2A) ────────────────
# Serhat kararı (20 Tem): üretim başına 2-3 aday, otomatik seçim (~$0.13 kabul).
_ICON_N_CANDIDATES = 3


def _score_icon_bytes(content: bytes) -> float:
    """İkon adayını PIL ile skorlar (network yok, ~ms). Üç ölçüt:
    - kapsama: ikon dolgusu ideal bantta mı (%12-55 — ne cılız ne boğucu)
    - merkezlilik: form optik merkeze oturuyor mu
    - flatness: düz vektör mü, gradient-bulamaç mı (anti-jenerik: az renk iyi)
    SVG/bozuk içerik 0 alır — PNG adaylar öne geçer."""
    try:
        import io as _io2
        from PIL import Image as _Img
        img = _Img.open(_io2.BytesIO(content)).convert("RGB").resize((128, 128))
        px = list(img.getdata())
        bgc = px[0]

        def _close(a, b, t=40):
            return abs(a[0]-b[0]) <= t and abs(a[1]-b[1]) <= t and abs(a[2]-b[2]) <= t

        fg_idx = [i for i, p in enumerate(px) if not _close(p, bgc)]
        if not fg_idx:
            return 0.0
        cov = len(fg_idx) / len(px)
        cov_score = max(0.0, 1.0 - abs(cov - 0.33) / 0.33)
        xs = [i % 128 for i in fg_idx]
        ys = [i // 128 for i in fg_idx]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        center_score = max(0.0, 1.0 - (((cx - 64) ** 2 + (cy - 64) ** 2) ** 0.5) / 64)
        ncol = img.getcolors(maxcolors=100000)
        n = len(ncol) if ncol else 100000
        flat_score = 1.0 if n <= 400 else max(0.0, 1.0 - (n - 400) / 4000)
        return 0.45 * cov_score + 0.25 * center_score + 0.30 * flat_score
    except Exception:
        return 0.0


async def _recraft_icon(prompt: str) -> str:
    """Recraft v3 — vector_illustration stili. Sadece İKON için (soyut geometrik mark,
    exact-text istemiyor — diffusion için uygun görev).
    20 Tem 2026: tek çağrıda _ICON_N_CANDIDATES aday üretir, _score_icon_bytes ile
    en iyisi otomatik seçilir. Dönen arayüz DEĞİŞMEDİ (tek data URI veya "")."""
    try:
        result = await asyncio.to_thread(
            fal_client.run,
            "fal-ai/recraft-v3",
            arguments={
                "prompt": prompt,
                "image_size": "square_hd",       # 1024×1024 — ikon zaten kare, çelişki yok
                "style": "vector_illustration",
                "num_images": _ICON_N_CANDIDATES,
            },
        )
        images = (result.get("images") or [])[:_ICON_N_CANDIDATES]
        if not images:
            return ""
        contents: list = []
        async with httpx.AsyncClient(timeout=45) as client:
            for im in images:
                try:
                    r = await client.get(im["url"])
                    r.raise_for_status()
                    contents.append(r.content)
                except Exception as de:
                    print(f"[image_generator] ikon aday indirilemedi: {de}")
        if not contents:
            return ""
        scored = sorted(((_score_icon_bytes(c), i, c) for i, c in enumerate(contents)),
                        key=lambda t: t[0], reverse=True)
        best_score, best_i, best = scored[0]
        print(f"[image_generator] ikon aday skorları: "
              f"{[(i, round(s, 3)) for s, i, _ in scored]} → seçilen #{best_i}")
        return _bytes_to_data_uri(best, "image/png")
    except Exception as e:
        print(f"[image_generator] Recraft hata (icon): {e}")
        return ""


async def _flux_app(prompt: str, image_size: str = "square_hd") -> str:
    """Flux Schnell ile editorial uygulama görseli üret. Döner: data:image/png;base64,... veya "".
    image_size: "square_hd" (1024×1024) | "portrait_16_9" (9:16 — mobil hero, 2B)."""
    try:
        result = await asyncio.to_thread(
            fal_client.run,
            "fal-ai/flux/schnell",
            arguments={
                "prompt": prompt,
                "image_size": image_size,
                "num_inference_steps": 4,
                "num_images": 1,
                "enable_safety_checker": True,
            },
        )
        url = result["images"][0]["url"]
        return await _download_b64(url, "image/png")
    except Exception as e:
        print(f"[image_generator] Flux hata: {e}")
        return ""


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────

def generate_all_images(brief: dict, studio_label: str = "") -> dict:
    """
    3 görseli paralel üret (2 Tem 2026 öncesi 5'ti — logo_primary/tipo artık
    logo_generator.py'nin PIL fonksiyonlarından geliyor, bkz. dosya başlığı).

    20 Tem 2026 (Görev 2A): studio_label opsiyonel parametresi eklendi — ikon
    prompt'una template'e bağlı stil preset'i eklemek için ANA logoyla AYNI
    _resolve_template() kararı kullanılır (marka tutarlılığı). Parametre
    verilmezse eski davranışa düşer (preset'siz ama anti-jenerik kuyruk yine var).

    Parametreler:
        brief        : normalize edilmiş brand brief dict
        studio_label : brand_brief'in studio_dna etiketi (template kararı için)

    Döner:
        {
            "logo_icon": "data:image/png;base64,...",   # veya ""
            "app1":      "data:image/png;base64,...",
            "app2":      "data:image/png;base64,...",
        }
    Hatalı slotlar "" döner — template boş slotu gizler, pipeline kırılmaz.
    """
    tpl = ""
    try:
        try:
            from . import logo_generator as _lg
        except ImportError:
            import logo_generator as _lg
        tpl = _lg._resolve_template(brief, studio_label)
    except Exception as e:
        print(f"[image_generator] template kararı alınamadı (preset'siz devam): {e}")

    async def _run():
        return await asyncio.gather(
            _recraft_icon(_logo_icon_prompt(brief, tpl)),
            _flux_app(_app1_prompt(brief)),
            _flux_app(_app2_prompt(brief)),
            # Görev 2B (20 Tem 2026): mobil hero dark/light — WVC brand-kit
            # paritesi. Flux Schnell ×2, ~+$0.006/üretim. Hatalı slot "" döner,
            # kit o hücreyi gizler (mevcut kural).
            _flux_app(_hero_prompt(brief, dark=True), image_size="portrait_16_9"),
            _flux_app(_hero_prompt(brief, dark=False), image_size="portrait_16_9"),
            return_exceptions=True,
        )

    results = asyncio.run(_run())
    keys = ["logo_icon", "app1", "app2", "hero_dark", "hero_light"]
    return {
        k: (r if isinstance(r, str) else "")
        for k, r in zip(keys, results)
    }
