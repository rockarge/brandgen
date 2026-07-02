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

def _logo_icon_prompt(brief: dict) -> str:
    # Önce Sonnet'in ürettiği Recraft-optimized prompt'u kullan
    fal_prompt = brief.get("fal_icon_prompt", "").strip()
    if fal_prompt and len(fal_prompt) > 30:
        return fal_prompt

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
        f'Vector illustration.'
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


# ── fal.ai çağrıları ──────────────────────────────────────────────────────────

async def _download_b64(url: str, mime: str) -> str:
    """URL'den içeriği indir, data URI olarak döndür.
    İçerik magic byte'larına göre MIME tespit eder — fal.ai CDN SVG'yi image/png diye servis eder."""
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content = resp.content
        # Magic byte sniffing — header'a güvenme, Recraft SVG → image/png yanlış header veriyor
        head = content.lstrip()[:10]
        if head.startswith(b"<svg") or head.startswith(b"<?xml"):
            mime = "image/svg+xml"
        elif content[:4] == b"\x89PNG":
            mime = "image/png"
        elif content[:2] in (b"\xff\xd8", b"\xff\xe0", b"\xff\xe1"):
            mime = "image/jpeg"
        b64 = base64.b64encode(content).decode("ascii")
        return f"data:{mime};base64,{b64}"


async def _recraft_icon(prompt: str) -> str:
    """Recraft v3 — vector_illustration stili. Sadece İKON için (soyut geometrik mark,
    exact-text istemiyor — diffusion için uygun görev). 2 Tem 2026: logo_primary/tipo
    buradan kaldırıldı, bkz. dosya başlığı."""
    try:
        result = await asyncio.to_thread(
            fal_client.run,
            "fal-ai/recraft-v3",
            arguments={
                "prompt": prompt,
                "image_size": "square_hd",       # 1024×1024 — ikon zaten kare, çelişki yok
                "style": "vector_illustration",
                "num_images": 1,
            },
        )
        url = result["images"][0]["url"]
        return await _download_b64(url, "image/png")
    except Exception as e:
        print(f"[image_generator] Recraft hata (icon): {e}")
        return ""


async def _flux_app(prompt: str) -> str:
    """Flux Schnell ile editorial uygulama görseli üret. Döner: data:image/png;base64,... veya ""."""
    try:
        result = await asyncio.to_thread(
            fal_client.run,
            "fal-ai/flux/schnell",
            arguments={
                "prompt": prompt,
                "image_size": "square_hd",        # 1024×1024
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

def generate_all_images(brief: dict) -> dict:
    """
    3 görseli paralel üret (2 Tem 2026 öncesi 5'ti — logo_primary/tipo artık
    logo_generator.py'nin PIL fonksiyonlarından geliyor, bkz. dosya başlığı).

    Parametreler:
        brief : normalize edilmiş brand brief dict

    Döner:
        {
            "logo_icon": "data:image/png;base64,...",   # veya ""
            "app1":      "data:image/png;base64,...",
            "app2":      "data:image/png;base64,...",
        }
    Hatalı slotlar "" döner — template boş slotu gizler, pipeline kırılmaz.
    """
    async def _run():
        return await asyncio.gather(
            _recraft_icon(_logo_icon_prompt(brief)),
            _flux_app(_app1_prompt(brief)),
            _flux_app(_app2_prompt(brief)),
            return_exceptions=True,
        )

    results = asyncio.run(_run())
    keys = ["logo_icon", "app1", "app2"]
    return {
        k: (r if isinstance(r, str) else "")
        for k, r in zip(keys, results)
    }
