"""
image_generator.py — fal.ai Görsel Üretici

Ne yapar    : fal.ai API ile 4 görseli paralel üretir.
              logo_primary + logo_tipo + logo_icon → Recraft v3 (vector_illustration)
              app1 + app2                          → Flux Schnell (editorial, JPEG)

Kime bağlı  : html_preview.py → generate_all_images(brief) çağrısı
Döner       : {"logo_primary": ..., "logo_tipo": ..., "logo_icon": ..., "app1": ..., "app2": ...}
Bozulursa   : Hatalı slot "" döner — html_preview pipeline kırılmaz, o slot gizlenir.
Maliyet     : Recraft ×3 (~$0.12) + Flux ×2 (~$0.006) = ~$0.13/üretim
Türkçe      : Marka adı _ascii_safe() ile temizlenir — AI görsel promptunda Türkçe karakter gitMEZ.
"""

import os
import base64
import asyncio
import httpx
import fal_client


# ── Türkçe karakter koruma ────────────────────────────────────────────────────
def _ascii_safe(name: str) -> str:
    """İ→I, Ş→S vb. — AI prompt'a gönderilirken Türkçe karakter gitmesin."""
    tr_map = str.maketrans("İĞÜŞÖÇığüşöç", "IGUSSOigusso")
    return name.translate(tr_map)


# ── Prompt üreticiler ─────────────────────────────────────────────────────────

def _logo_primary_prompt(brief: dict) -> str:
    # Önce Sonnet'in ürettiği Recraft-optimized prompt'u kullan
    fal_prompt = brief.get("fal_logo_prompt", "").strip()
    if fal_prompt and len(fal_prompt) > 30:
        return fal_prompt

    # Fallback: brief alanlarından generic prompt
    name      = _ascii_safe(brief.get("brand_name", "BRAND"))
    primary   = brief.get("primary_color", "#333333")
    secondary = brief.get("secondary_color", "#888888")
    bg        = brief.get("bg_color", "#FFFFFF")
    energy    = brief.get("energy", "cinematic")
    tagline   = brief.get("tagline", "")
    concept   = brief.get("concept_statement", "")
    sector    = brief.get("studio_dna", {}).get("sector", "")
    mood      = ", ".join(brief.get("mood_words", [])[:3])

    style = "bold energetic playful" if energy == "playful" else "premium cinematic minimal"
    return (
        f'Vector logo for brand "{name}"{(" — " + sector) if sector else ""}. '
        f'Wordmark: the text "{name}" is the dominant element. '
        f'{concept[:100] + ". " if concept else ""}'
        f'{mood + ". " if mood else ""}'
        f'{style} visual style. '
        f'Colors: {primary} dominant on {bg} background, {secondary} accent. '
        f'Horizontal format. No gradients. No shadows. Vector illustration.'
    ).strip()


def _logo_tipo_prompt(brief: dict) -> str:
    """Tipo (yaratıcı tipografik wordmark) için Recraft prompt.
    Amaç: marka adı merkezde, yaratıcı harf tasarımı — sahneden bağımsız grafik wordmark."""
    name      = _ascii_safe(brief.get("brand_name", "BRAND"))
    primary   = brief.get("primary_color", "#333333")
    secondary = brief.get("secondary_color", "#888888")
    bg        = brief.get("bg_color", "#FFFFFF")
    energy    = brief.get("energy", "cinematic")
    font_display = brief.get("font_display", "")
    mood      = ", ".join(brief.get("mood_words", [])[:3])
    concept   = brief.get("concept_statement", "")[:80]

    if energy == "playful":
        style_hint = "playful bold hand-lettered typography, bouncy rounded letterforms, fun graphic wordmark"
        color_note = f"vibrant {primary} lettering on {bg}, {secondary} decorative accents on letters"
    else:
        style_hint = "elegant custom lettering, refined typographic wordmark, editorial brand typography"
        color_note = f"{primary} letterforms on {bg} background, {secondary} as subtle accent"

    font_hint = f"lettering style inspired by {font_display}. " if font_display else ""

    return (
        f'Creative typographic wordmark for brand "{name}". '
        f'The word "{name}" rendered as custom lettering — {style_hint}. '
        f'{font_hint}'
        f'{concept + ". " if concept else ""}'
        f'{mood + ". " if mood else ""}'
        f'{color_note}. '
        f'Horizontal wordmark layout. Flat vector graphic. '
        f'The brand name text is the dominant visual element.'
    ).strip()


def _logo_icon_prompt(brief: dict) -> str:
    # Önce Sonnet'in ürettiği Recraft-optimized prompt'u kullan
    fal_prompt = brief.get("fal_icon_prompt", "").strip()
    if fal_prompt and len(fal_prompt) > 30:
        return fal_prompt

    # Fallback: brief alanlarından generic prompt
    name      = _ascii_safe(brief.get("brand_name", "BRAND"))
    letter    = name[0].upper() if name else "B"
    primary   = brief.get("primary_color", "#333333")
    bg        = brief.get("bg_color", "#FFFFFF")
    secondary = brief.get("secondary_color", "#888888")
    energy    = brief.get("energy", "cinematic")
    concept   = brief.get("concept_statement", "")
    mood      = ", ".join(brief.get("mood_words", [])[:2])

    style = "bold geometric playful" if energy == "playful" else "minimal premium geometric"
    return (
        f'App icon mark for "{name}" brand. '
        f'Abstract geometric symbol built from the letter "{letter}". '
        f'{concept[:100] + ". " if concept else ""}'
        f'{mood + ". " if mood else ""}'
        f'{style} design. '
        f'Colors: {primary} on {bg} background, {secondary} accent. '
        f'Square format. No text. Scalable geometric shape. Clean edges. '
        f'Vector illustration.'
    ).strip()


def _app1_prompt(brief: dict) -> str:
    name      = _ascii_safe(brief.get("brand_name", "BRAND"))
    primary   = brief.get("primary_color", "#333333")
    bg        = brief.get("bg_color", "#111111")
    energy    = brief.get("energy", "cinematic")
    concept   = brief.get("concept_statement", "")
    sector    = brief.get("studio_dna", {}).get("sector", brief.get("sector", ""))
    mood_raw  = brief.get("mood_words", [])
    mood      = ", ".join(mood_raw[:3]) if mood_raw else ""
    visual    = brief.get("visual_language", "")[:120]

    if energy == "playful":
        atm = "vivid, colorful, joyful, bold graphic illustration, flat design, playful"
        style = "Bold flat illustration or graphic art. Bright saturated colors. Child-friendly, fun, energetic."
    else:
        atm = "cinematic, dramatic, premium, atmospheric"
        style = "Professional editorial photography or bold graphic composition."
    return (
        f'Editorial social media visual for "{name}"{(" — " + sector) if sector else ""}. '
        f'{atm} atmosphere. '
        f'{concept[:120] + ". " if concept else ""}'
        f'{visual + ". " if visual else ""}'
        f'{mood + ". " if mood else ""}'
        f'Dominant color: {primary} on {bg} background. '
        f'NO text. NO logo. NO watermark. '
        f'{style} '
        f'Square 1:1 format, high quality.'
    ).strip()


def _app2_prompt(brief: dict) -> str:
    name      = _ascii_safe(brief.get("brand_name", "BRAND"))
    secondary = brief.get("secondary_color", "#888888")
    bg        = brief.get("bg_color", "#111111")
    energy    = brief.get("energy", "cinematic")
    concept   = brief.get("concept_statement", "")
    sector    = brief.get("studio_dna", {}).get("sector", brief.get("sector", ""))
    mood_raw  = brief.get("mood_words", [])
    mood      = ", ".join(mood_raw[1:4]) if len(mood_raw) > 1 else ""
    visual    = brief.get("visual_language", "")[:100]

    atm = "playful abstract geometric, bold colors, graphic" if energy == "playful" else "minimal bold editorial, abstract architectural"
    return (
        f'Abstract brand identity visual for "{name}"{(" — " + sector) if sector else ""}. '
        f'{atm} composition. '
        f'{concept[:120] + ". " if concept else ""}'
        f'{visual + ". " if visual else ""}'
        f'{mood + ". " if mood else ""}'
        f'Dominant color: {secondary} on {bg} background. '
        f'NO text. NO logo. NO product shots. Pure abstract or conceptual art. '
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


async def _recraft_logo(prompt: str) -> str:
    """Recraft v3 — vector_illustration stili. ANA logo ve İKON için (editorial illüstrasyon)."""
    try:
        result = await asyncio.to_thread(
            fal_client.run,
            "fal-ai/recraft-v3",
            arguments={
                "prompt": prompt,
                "image_size": "square_hd",       # 1024×1024
                "style": "vector_illustration",
                "num_images": 1,
            },
        )
        url = result["images"][0]["url"]
        return await _download_b64(url, "image/png")
    except Exception as e:
        print(f"[image_generator] Recraft hata (logo): {e}")
        return ""


async def _recraft_tipo(prompt: str) -> str:
    """Recraft v3 — vector_illustration/flat_art stili. TİPO için (yaratıcı tipografik wordmark).
    flat_art: grafik, geometrik, karakter sahnesine girme eğilimi daha düşük."""
    try:
        result = await asyncio.to_thread(
            fal_client.run,
            "fal-ai/recraft-v3",
            arguments={
                "prompt": prompt,
                "image_size": "landscape_16_9",  # wordmark için yatay format
                "style": "vector_illustration/flat_art",
                "num_images": 1,
            },
        )
        url = result["images"][0]["url"]
        return await _download_b64(url, "image/png")
    except Exception as e:
        print(f"[image_generator] Recraft hata (tipo): {e}")
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
    4 görseli paralel üret.

    Parametreler:
        brief : normalize edilmiş brand brief dict

    Döner:
        {
            "logo_primary": "data:image/svg+xml;base64,...",  # veya ""
            "logo_icon":    "data:image/svg+xml;base64,...",
            "app1":         "data:image/jpeg;base64,...",
            "app2":         "data:image/jpeg;base64,...",
        }
    Hatalı slotlar "" döner — template boş slotu gizler, pipeline kırılmaz.
    """
    async def _run():
        return await asyncio.gather(
            _recraft_logo(_logo_primary_prompt(brief)),
            _recraft_tipo(_logo_tipo_prompt(brief)),   # flat_art stili — yaratıcı wordmark
            _recraft_logo(_logo_icon_prompt(brief)),
            _flux_app(_app1_prompt(brief)),
            _flux_app(_app2_prompt(brief)),
            return_exceptions=True,
        )

    results = asyncio.run(_run())
    keys = ["logo_primary", "logo_tipo", "logo_icon", "app1", "app2"]
    return {
        k: (r if isinstance(r, str) else "")
        for k, r in zip(keys, results)
    }
