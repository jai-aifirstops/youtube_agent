from __future__ import annotations

import base64
import os
import textwrap
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .documentary import DocumentaryPlan, DocumentaryScene


OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"
VIDEO_SIZE = (1920, 1080)
ARTWORK_SIZE = (2304, 1296)


@dataclass(frozen=True)
class SceneVisualAsset:
    scene_number: int
    path: str
    provider: str
    prompt: str

    def to_dict(self) -> dict:
        return asdict(self)


def prepare_scene_visual_assets(
    plan: DocumentaryPlan,
    assets_dir: Path,
    *,
    provider: str,
    openai_model: str,
    openai_size: str,
) -> list[SceneVisualAsset]:
    assets_dir.mkdir(parents=True, exist_ok=True)
    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        return _generate_openai_assets(plan, assets_dir, model=openai_model, size=openai_size)
    return _generate_fallback_assets(plan, assets_dir)


def _generate_openai_assets(
    plan: DocumentaryPlan,
    assets_dir: Path,
    *,
    model: str,
    size: str,
) -> list[SceneVisualAsset]:
    assets: list[SceneVisualAsset] = []
    try:
        for scene in plan.scenes:
            output_path = assets_dir / f"ai_scene_{scene.number:02d}.png"
            _openai_image(scene.image_prompt, output_path, model=model, size=size)
            assets.append(SceneVisualAsset(scene.number, str(output_path), "openai", scene.image_prompt))
    except Exception as error:
        print(f"OpenAI image generation failed; using fallback art cards. Last error: {error}")
        return _generate_fallback_assets(plan, assets_dir)
    return assets


def _openai_image(prompt: str, output_path: Path, *, model: str, size: str) -> Path:
    import requests

    response = requests.post(
        OPENAI_IMAGES_URL,
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"},
        json={"model": model, "prompt": prompt, "size": size, "n": 1, "response_format": "b64_json"},
        timeout=240,
    )
    response.raise_for_status()
    image_data = response.json()["data"][0]
    if "b64_json" in image_data:
        raw = base64.b64decode(image_data["b64_json"])
    else:
        image_response = requests.get(image_data["url"], timeout=240)
        image_response.raise_for_status()
        raw = image_response.content

    image = Image.open(BytesIO(raw)).convert("RGB")
    ImageOps.fit(image, VIDEO_SIZE, method=Image.Resampling.LANCZOS).save(output_path)
    return output_path


def _generate_fallback_assets(plan: DocumentaryPlan, assets_dir: Path) -> list[SceneVisualAsset]:
    assets = []
    for scene in plan.scenes:
        output_path = assets_dir / f"scene_{scene.number:02d}.png"
        _create_fallback_art_card(scene, output_path)
        assets.append(SceneVisualAsset(scene.number, str(output_path), "fallback", scene.image_prompt))
    return assets


def _create_fallback_art_card(scene: DocumentaryScene, output_path: Path) -> Path:
    image = Image.new("RGB", ARTWORK_SIZE, color=(8, 10, 14))
    draw = ImageDraw.Draw(image)
    title_font = _font(78)
    label_font = _font(42)
    body_font = _font(38)
    small_font = _font(30)

    for y in range(ARTWORK_SIZE[1]):
        shade = int(16 + 42 * (y / ARTWORK_SIZE[1]))
        draw.line((0, y, ARTWORK_SIZE[0], y), fill=(shade // 2, shade, shade + 16))

    draw.rectangle((0, 0, ARTWORK_SIZE[0], ARTWORK_SIZE[1]), outline=(218, 184, 99), width=10)
    draw.line((170, 0, 170, ARTWORK_SIZE[1]), fill=(218, 184, 99), width=3)
    draw.line((ARTWORK_SIZE[0] - 170, 0, ARTWORK_SIZE[0] - 170, ARTWORK_SIZE[1]), fill=(218, 184, 99), width=3)
    draw.ellipse((1500, 110, 2240, 850), outline=(92, 128, 180), width=8)
    draw.rounded_rectangle((130, 115, 690, 205), radius=24, fill=(218, 184, 99))
    draw.text((165, 138), f"SCENE {scene.number:02d}", font=label_font, fill=(8, 10, 14))

    draw.multiline_text(
        (130, 300),
        "\n".join(textwrap.wrap(scene.title.upper(), width=30)),
        font=title_font,
        fill=(244, 240, 229),
        spacing=14,
    )

    prompt_excerpt = scene.image_prompt.replace("Cinematic documentary still, ", "")
    draw.multiline_text(
        (130, 680),
        "\n".join(textwrap.wrap(prompt_excerpt, width=72)[:8]),
        font=body_font,
        fill=(209, 222, 238),
        spacing=12,
    )
    draw.text((130, 1190), "CINEMATIC DOCUMENTARY", font=small_font, fill=(218, 184, 99))

    image.save(output_path)
    return output_path


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()
