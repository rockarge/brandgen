"""
Ana üretim pipeline'ı.
run_pipeline: watermarklı preview üretir (ücretsiz gösterim için)
finalize_job: ödeme sonrası watermarksız dosyaları üretir + zip'ler

╔══════════════════════════════════════════════════════════════════════════════╗
║  2 TEM 2026 — finalize_job KRİTİK FİX (bkz. bekleyen-gorevler.md)            ║
║  Önceden finalize_job, html_preview.py'nin kullandığı pipeline'dan (PIL      ║
║  wordmark + fal.ai) TAMAMEN AYRI, eski bir sistemi (generate_logo_primary/   ║
║  icon/reversed/social_post) kullanıyordu. Sonuç: müşteri ödeme öncesi        ║
║  preview'da bir görsel seti görüyor, ödeyip indirdiği ZIP'te BAŞKA bir       ║
║  görsel seti alıyordu. finalize_job artık run_pipeline/html_preview ile      ║
║  AYNI kaynaktan (select_logo_primary_png, select_logo_mono_png,             ║
║  generate_all_images) üretiyor — bkz. finalize_job içindeki not.            ║
║  run_pipeline'daki watermarklı ÖN-izleme collage'ı (generate_preview_collage)║
║  bilinçli olarak DOKUNULMADI — o sadece ödeme öncesi küçük bir thumbnail,    ║
║  ayrı bir iyileştirme konusu, kapsam dışı bırakıldı (raporda belirtildi).    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import io
import zipfile
import tempfile
import os
import base64
from PIL import Image, ImageOps

from .brand_brief import generate_brand_brief
from .brand_brief_contract import normalize_brief
from .html_preview import generate_html_preview
from .logo_generator import (
    generate_logo_primary,
    generate_logo_icon,
    generate_logo_reversed,
    generate_social_post,
    apply_watermark,
    select_logo_primary_png,
    select_logo_mono_png,
    select_logo_tipo_png,
    hex_to_rgb,
)
from .image_generator import generate_all_images
from .card_generator import generate_card_mockup, generate_card_composite
from .pdf_generator import generate_brand_kit_pdf
from utils.supabase_client import get_db, update_job


def _datauri_to_pil_rgb(data_uri: str, bg_hex: str = "#0F0D0C", size: tuple = (1080, 1080)) -> "Image.Image":
    """Base64 data URI (PNG/JPEG) → düz RGB PIL Image.
    RGBA gelirse bg_hex üstüne composite eder (PDF/ZIP her zaman flat RGB bekliyor).
    Boş veya bozuk veri gelirse bg_hex renginde boş kare döner — finalize_job kırılmaz,
    o slot düz renk olarak çıkar (görünür ama sessiz hata değil, log'a yazılır)."""
    try:
        bg_rgb = hex_to_rgb(bg_hex)
    except Exception:
        bg_rgb = (15, 13, 12)

    if not data_uri or "," not in data_uri:
        return Image.new("RGB", size, bg_rgb)
    try:
        _, b64data = data_uri.split(",", 1)
        raw = base64.b64decode(b64data)
        img = Image.open(io.BytesIO(raw))
        img.load()
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
            base = Image.new("RGB", img.size, bg_rgb)
            base.paste(img, mask=img.split()[-1])
            return base
        return img.convert("RGB")
    except Exception as e:
        print(f"[pipeline] görsel decode hatası, düz zemine düşülüyor: {e}")
        return Image.new("RGB", size, bg_rgb)


def _invert_rgb(img: "Image.Image") -> "Image.Image":
    """Reversed logo varyantı için: RGB'yi ters çevir (light-on-dark ↔ dark-on-light)."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    return ImageOps.invert(img)


def run_pipeline(job_id: str, prompt: str, tier: str = "free") -> None:
    """
    Watermarklı preview üretir. Supabase'e preview_url yazar.
    tier: free | single | starter | pro | agency
    """
    try:
        update_job(job_id, status="processing")

        from .brand_brief import MODEL_MAP, DEFAULT_MODEL
        used_model = MODEL_MAP.get(tier, DEFAULT_MODEL)
        update_job(job_id, tier=tier, ai_model=used_model)

        # 1. Brand brief — Claude API (tier'a göre model seçer)
        brief, brief_tokens = generate_brand_brief(prompt, tier=tier)
        # token yazımı pipeline sonunda html_preview tokenlarıyla birleştirilerek yapılacak
        brand_name = brief.get("brand_name", "BRAND")
        primary = brief.get("primary_color", "#0A0A0A")
        secondary = brief.get("secondary_color", "#F1EBE1")

        # 2. Logo üretimi
        logo_primary = generate_logo_primary(brand_name, primary, secondary)
        logo_icon = generate_logo_icon(brand_name, primary, secondary)
        logo_reversed = generate_logo_reversed(brand_name, primary, secondary)
        social_1 = generate_social_post(
            brand_name, brief.get("social_post_1_caption", brand_name), primary, secondary
        )
        social_2 = generate_social_post(
            brand_name, brief.get("social_post_2_caption", ""), primary, secondary
        )

        # 3. Kartvizit
        card_front, card_back = generate_card_mockup(brief)
        card_composite = generate_card_composite(card_front, card_back)

        # 4. Watermarklı preview — zengin collage
        preview_img = apply_watermark(
            generate_preview_collage(
                logo_primary, logo_icon, social_1, card_composite, brief
            )
        )

        # 5. Supabase Storage'a yükle
        db = get_db()

        preview_bytes = _img_to_bytes(preview_img)
        preview_path = f"previews/{job_id}/preview.jpg"
        db.storage.from_("brandgen").upload(
            preview_path,
            preview_bytes,
            {"content-type": "image/jpeg", "upsert": "true"},
        )
        preview_url = db.storage.from_("brandgen").get_public_url(preview_path)

        # 5c. HTML brand kit üret → doğrudan DB'ye yaz (Storage text/html'i reddeder)
        # html_preview.py içinde Claude API hem strateji hem SVG logoları üretiyor
        html_content, html_tokens = generate_html_preview(brief)

        # 6. Brief'i JSON olarak sakla (finalize için) — _*_b64 alanları hariç (dev büyük)
        import json
        brief_clean = {k: v for k, v in brief.items() if not k.startswith("_")}
        brief_path = f"jobs/{job_id}/brief.json"
        db.storage.from_("brandgen").upload(
            brief_path,
            json.dumps(brief_clean, ensure_ascii=False).encode(),
            {"content-type": "application/json", "upsert": "true"},
        )

        # İki çağrının token toplamını DB'ye yaz
        total_input  = brief_tokens["input_tokens"]  + html_tokens["input_tokens"]
        total_output = brief_tokens["output_tokens"] + html_tokens["output_tokens"]

        update_job(
            job_id,
            status="done",
            preview_url=preview_url,
            preview_html=html_content,
            brand_story_preview=brief.get("brand_story_preview", ""),
            brief_data=brief_clean,
            input_tokens=total_input,
            output_tokens=total_output,
        )

    except Exception as e:
        print(f"Pipeline error [{job_id}]: {e}")
        update_job(job_id, status="error", error=str(e)[:500])


def finalize_job(job_id: str) -> None:
    """
    Ödeme sonrası çalışır.
    Watermarksız tüm dosyaları üretir, zip'ler, Supabase'e yükler.

    2 Tem 2026: Artık run_pipeline/html_preview ile AYNI görsel kaynağını kullanıyor
    (select_logo_primary_png, select_logo_mono_png, generate_all_images) — bkz. dosya
    başlığındaki not. Eşleme:
      logo_primary  ← select_logo_primary_png (PIL, template/stüdyo/energy'e göre)
      logo_icon     ← generate_all_images()["logo_icon"] (Recraft v3)
      logo_reversed ← select_logo_mono_png'nin renk-ters-çevrilmiş hali (ayrı üretim yok)
      social_1/2    ← generate_all_images()["app1"/"app2"] (Flux) — kavram olarak
                      "sosyal medya görseli" korunuyor, üretim kaynağı değişti

    3 Tem 2026: logo_tipo ZIP'e eklendi. Önceden preview'da (html_preview.py) TİPO
    slotu gösteriliyordu ama finalize_job'ın ürettiği indirilebilir ZIP'te logo_tipo
    dosyası HİÇ YOKTU — "Preview ≠ Download" sınıfı bir bug. select_logo_tipo_png
    artık burada da çağrılıyor, ZIP'e ayrı dosya olarak ekleniyor (bkz. aşağıdaki
    _add_img çağrısı).
    """
    try:
        db = get_db()
        import json

        # Brief'i geri al
        brief_bytes = db.storage.from_("brandgen").download(f"jobs/{job_id}/brief.json")
        brief = json.loads(brief_bytes)
        brief = normalize_brief(brief)  # eski job'larda yeni alanlar (fal_app*_prompt vb.) eksik olabilir

        brand_name = brief.get("brand_name", "BRAND")
        studio_label = brief.get("studio_dna", {}).get("label", "")
        bg_hex = brief.get("bg_color", "#0F0D0C")

        # Dosyaları yeniden üret (watermarksız) — preview'da gösterilenle AYNI kaynak
        logo_primary_uri = select_logo_primary_png(brief, studio_label=studio_label)
        # studio_label buraya da geçiyor (3 Tem 2026, font-per-marka) — finalize_job'ın
        # ürettiği ZIP, preview'daki ile AYNI fontu kullansın (aksi hâlde tam da bu
        # dosyanın başında düzeltilen "Preview ≠ İndirilen" sınıfı bir bug'ı, bu sefer
        # font üzerinden, sessizce geri getirirdik).
        logo_mono_uri     = select_logo_mono_png(brief, studio_label=studio_label)
        # logo_tipo: preview'daki ile AYNI kaynak — select_logo_tipo_png artık MONO'nun
        # kopyası değil (3 Tem 2026 fix), bu yüzden burada da ayrıca üretilmesi şart.
        logo_tipo_uri     = select_logo_tipo_png(brief, studio_label=studio_label)
        fal_images        = generate_all_images(brief, studio_label=studio_label)

        logo_primary  = _datauri_to_pil_rgb(logo_primary_uri, bg_hex, size=(1600, 560))
        logo_icon     = _datauri_to_pil_rgb(fal_images.get("logo_icon", ""), bg_hex, size=(1024, 1024))
        logo_reversed = _invert_rgb(_datauri_to_pil_rgb(logo_mono_uri, bg_hex, size=(1600, 420)))
        logo_tipo     = _datauri_to_pil_rgb(logo_tipo_uri, bg_hex, size=(1600, 520))
        social_1      = _datauri_to_pil_rgb(fal_images.get("app1", ""), bg_hex, size=(1024, 1024))
        social_2      = _datauri_to_pil_rgb(fal_images.get("app2", ""), bg_hex, size=(1024, 1024))
        card_front, card_back = generate_card_mockup(brief)

        # PDF (watermarksız)
        pdf_bytes = generate_brand_kit_pdf(
            brief, logo_primary, logo_icon, logo_reversed, social_1, social_2, watermark=False
        )

        # ZIP oluştur
        zip_buf = io.BytesIO()
        safe_name = brand_name.replace(" ", "_").replace("/", "-").upper()
        files_list = []

        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # Logolar
            _add_img(zf, logo_primary, f"{safe_name}_logo_primary.png", files_list)
            _add_img(zf, logo_icon, f"{safe_name}_logo_icon.png", files_list)
            _add_img(zf, logo_reversed, f"{safe_name}_logo_reversed.png", files_list)
            _add_img(zf, logo_tipo, f"{safe_name}_logo_tipo.png", files_list)

            # Sosyal medya
            _add_img(zf, social_1, f"{safe_name}_social_post_1.png", files_list)
            _add_img(zf, social_2, f"{safe_name}_social_post_2.png", files_list)

            # Kartvizit
            _add_img(zf, card_front, f"{safe_name}_card_front.png", files_list)
            _add_img(zf, card_back, f"{safe_name}_card_back.png", files_list)

            # PDF
            zf.writestr(f"{safe_name}_brand_kit.pdf", pdf_bytes)
            files_list.append(f"{safe_name}_brand_kit.pdf")

            # Brand story TXT
            story = brief.get("brand_story", "")
            zf.writestr(f"{safe_name}_brand_story.txt", story)
            files_list.append(f"{safe_name}_brand_story.txt")

            # Color/font guide
            guide = _generate_guide_txt(brief)
            zf.writestr(f"{safe_name}_brand_guide.txt", guide)
            files_list.append(f"{safe_name}_brand_guide.txt")

        zip_bytes = zip_buf.getvalue()

        # Supabase'e yükle
        zip_path = f"downloads/{job_id}/{safe_name}_brand_kit.zip"
        db.storage.from_("brandgen").upload(
            zip_path,
            zip_bytes,
            {"content-type": "application/zip", "upsert": "true"},
        )
        download_url = db.storage.from_("brandgen").get_public_url(zip_path)

        update_job(
            job_id,
            download_url=download_url,
            brand_story=brief.get("brand_story", ""),
            files_list=files_list,
        )

    except Exception as e:
        print(f"Finalize error [{job_id}]: {e}")


# ── Preview Collage ────────────────────────────────────────────────────────────

def generate_preview_collage(
    logo_primary: "Image.Image",
    logo_icon: "Image.Image",
    social_post: "Image.Image",
    card_composite: "Image.Image",
    brief: dict,
) -> "Image.Image":
    """
    Watermark uygulanmadan önce çağrılan zengin preview collage.
    Layout (1600px genişlik):
      ROW 1: Logo primary (geniş) | Logo icon (kare)
      ROW 2: Renk paletiyle birlikte marka bilgisi şeridi
      ROW 3: Sosyal medya post (kare) | Kartvizit composite
    """
    from PIL import Image, ImageDraw
    from .logo_generator import get_font

    CANVAS_W = 1600
    PAD = 32
    BG = (12, 11, 10)

    # ROW 1 — Logo primary (sol, 4/5) + Logo icon (sağ, 1/5)
    logo_h = 480
    icon_w = 280
    logo_w = CANVAS_W - icon_w - PAD * 3

    logo_resized = logo_primary.resize((logo_w, logo_h), Image.LANCZOS)
    icon_resized = logo_icon.resize((icon_w, icon_w), Image.LANCZOS)

    # ROW 2 — Renk + Tipografi şeridi
    swatch_h = 120
    primary_hex = brief.get("primary_color", "#0A0A0A")
    secondary_hex = brief.get("secondary_color", "#F1EBE1")
    accent_hex = brief.get("accent_color", "")
    tagline = brief.get("tagline", "")
    brand_name = brief.get("brand_name", "BRAND")
    font_display = brief.get("font_display", "Big Shoulders Display")
    font_body = brief.get("font_body", "DM Sans")

    # ROW 3 — Sosyal post (sol) + Kartvizit (sağ)
    row3_h = 560
    social_w = 560
    card_w = CANVAS_W - social_w - PAD * 3

    social_resized = social_post.resize((social_w, social_w), Image.LANCZOS)
    card_h_target = row3_h
    card_ratio = card_composite.width / card_composite.height
    card_w_target = int(card_h_target * card_ratio)
    if card_w_target > card_w:
        card_w_target = card_w
        card_h_target = int(card_w_target / card_ratio)
    card_resized = card_composite.resize((card_w_target, card_h_target), Image.LANCZOS)

    total_h = PAD + logo_h + PAD + swatch_h + PAD + row3_h + PAD
    canvas = Image.new("RGB", (CANVAS_W, total_h), BG)
    draw = ImageDraw.Draw(canvas)

    # ROW 1 paste
    canvas.paste(logo_resized, (PAD, PAD))
    icon_y = PAD + (logo_h - icon_w) // 2
    canvas.paste(icon_resized, (PAD + logo_w + PAD, icon_y))

    # ROW 2 — renk şeridi
    row2_y = PAD + logo_h + PAD
    swatch_size = swatch_h - PAD
    colors = [c for c in [primary_hex, secondary_hex, accent_hex] if c]
    swatch_x = PAD
    for hex_color in colors:
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
        except Exception:
            r, g, b = 30, 30, 28
        draw.rectangle(
            [swatch_x, row2_y + PAD // 2, swatch_x + swatch_size, row2_y + PAD // 2 + swatch_size],
            fill=(r, g, b),
        )
        label_font = get_font(22, bold=False)
        draw.text(
            (swatch_x, row2_y + PAD // 2 + swatch_size + 6),
            hex_color.upper(),
            font=label_font,
            fill=(100, 96, 86),
        )
        swatch_x += swatch_size + PAD

    # Tagline + tipografi bilgisi — sağ taraf
    info_x = CANVAS_W // 2
    info_font_lg = get_font(36)
    info_font_sm = get_font(22, bold=False)
    if tagline:
        draw.text((info_x, row2_y + 16), tagline.upper(), font=info_font_lg, fill=(220, 215, 200))
    draw.text(
        (info_x, row2_y + 64),
        f"{font_display} / {font_body}",
        font=info_font_sm,
        fill=(80, 76, 68),
    )

    # ROW 3 paste
    row3_y = row2_y + swatch_h + PAD
    social_y_offset = (row3_h - social_w) // 2
    canvas.paste(social_resized, (PAD, row3_y + max(0, social_y_offset)))
    card_x = PAD + social_w + PAD
    card_y_offset = (row3_h - card_h_target) // 2
    canvas.paste(card_resized, (card_x, row3_y + max(0, card_y_offset)))

    # Alt şerit — brand watermark line
    draw.line([(PAD, total_h - PAD), (CANVAS_W - PAD, total_h - PAD)], fill=(30, 28, 24), width=1)
    footer_font = get_font(20, bold=False)
    draw.text(
        (PAD, total_h - PAD + 4),
        f"{brand_name.upper()} — BRANDGEN.NO1A.COM",
        font=footer_font,
        fill=(50, 47, 40),
    )

    return canvas


# ── Helpers ────────────────────────────────────────────────────────────────────

def _img_to_b64(img: Image.Image, fmt: str = "PNG") -> str:
    """PIL Image → data URI string (HTML embed için)."""
    buf = io.BytesIO()
    if fmt == "JPEG" and img.mode == "RGBA":
        img = img.convert("RGB")
    img.save(buf, format=fmt, quality=85 if fmt == "JPEG" else None)
    mime = "image/jpeg" if fmt == "JPEG" else "image/png"
    return f"data:{mime};base64,{base64.b64encode(buf.getvalue()).decode()}"


def _img_to_bytes(img: Image.Image, fmt: str = "JPEG", quality: int = 92) -> bytes:
    buf = io.BytesIO()
    if fmt == "JPEG" and img.mode == "RGBA":
        img = img.convert("RGB")
    img.save(buf, format=fmt, quality=quality)
    return buf.getvalue()


def _add_img(zf: zipfile.ZipFile, img: Image.Image, name: str, files_list: list):
    buf = io.BytesIO()
    if img.mode == "RGBA":
        img = img.convert("RGB")
    img.save(buf, format="PNG")
    zf.writestr(name, buf.getvalue())
    files_list.append(name)


def _generate_guide_txt(brief: dict) -> str:
    lines = [
        f"BRAND GUIDE — {brief.get('brand_name', 'BRAND').upper()}",
        "=" * 50,
        "",
        f"Tagline: {brief.get('tagline', '')}",
        "",
        "COLORS",
        f"  Primary:   {brief.get('primary_color', '#0A0A0A')}",
        f"  Secondary: {brief.get('secondary_color', '#F1EBE1')}",
    ]
    if brief.get("accent_color"):
        lines.append(f"  Accent:    {brief['accent_color']}")

    lines += [
        "",
        "TYPOGRAPHY",
        f"  Display: {brief.get('font_display', 'Big Shoulders Display')}",
        f"  Body:    {brief.get('font_body', 'DM Sans')}",
        f"  Meta:    {brief.get('font_meta', 'DM Mono')}",
        "",
        "MOOD",
        "  " + ", ".join(brief.get("mood_words", [])),
        "",
        "VISUAL LANGUAGE",
        brief.get("visual_language", ""),
        "",
        "---",
        "Generated by BrandGen.app — Windy Venture Capital",
    ]
    return "\n".join(lines)
