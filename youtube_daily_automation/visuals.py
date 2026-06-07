from __future__ import annotations

import hashlib
import re
import shutil
import textwrap
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .documentary import DocumentaryPlan, DocumentaryScene


COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
VIDEO_SIZE = (1920, 1080)
ARTWORK_SIZE = (2304, 1296)


@dataclass(frozen=True)
class SceneVisualAsset:
    scene_number: int
    path: str
    provider: str
    prompt: str
    source_title: str | None = None
    source_url: str | None = None
    license_name: str | None = None
    artist: str | None = None
    search_query: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def prepare_scene_visual_assets(
    plan: DocumentaryPlan,
    assets_dir: Path,
    *,
    provider: str,
) -> list[SceneVisualAsset]:
    assets_dir.mkdir(parents=True, exist_ok=True)
    if provider == "fallback":
        return _generate_fallback_assets(plan, assets_dir)
    if provider != "wikimedia":
        raise ValueError("IMAGE_PROVIDER must be wikimedia or fallback.")
    return [_wikimedia_asset_or_fallback(scene, assets_dir) for scene in plan.scenes]


def _wikimedia_asset_or_fallback(scene: DocumentaryScene, assets_dir: Path) -> SceneVisualAsset:
    query = _search_query(scene)
    try:
        result = _search_wikimedia_image(query)
        if result is None:
            raise RuntimeError("No Wikimedia image result found.")
        output_path = assets_dir / f"wikimedia_scene_{scene.number:02d}.png"
        _download_cached_image(result["url"], output_path, assets_dir / "cache", cache_key=query)
        return SceneVisualAsset(
            scene_number=scene.number,
            path=str(output_path),
            provider="wikimedia",
            prompt=scene.image_prompt,
            source_title=result.get("title"),
            source_url=result.get("description_url"),
            license_name=result.get("license"),
            artist=result.get("artist"),
            search_query=query,
        )
    except Exception as error:
        print(f"Wikimedia image lookup failed for scene {scene.number}; using fallback art card. Last error: {error}")
        output_path = assets_dir / f"scene_{scene.number:02d}.png"
        _create_fallback_art_card(scene, output_path)
        return SceneVisualAsset(scene.number, str(output_path), "fallback", scene.image_prompt, search_query=query)


def _search_wikimedia_image(query: str) -> dict | None:
    import requests

    response = requests.get(
        COMMONS_API_URL,
        params={
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": 8,
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata",
            "iiurlwidth": 1920,
            "iiurlheight": 1080,
            "format": "json",
            "formatversion": 2,
        },
        headers={"User-Agent": "youtube-agent/0.1 (free documentary automation)"},
        timeout=30,
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", [])
    for page in pages:
        imageinfo = (page.get("imageinfo") or [{}])[0]
        if imageinfo.get("mime") not in {"image/jpeg", "image/png", "image/webp"}:
            continue
        metadata = imageinfo.get("extmetadata") or {}
        return {
            "title": page.get("title"),
            "url": imageinfo.get("thumburl") or imageinfo.get("url"),
            "description_url": imageinfo.get("descriptionurl"),
            "license": _metadata_value(metadata.get("LicenseShortName")),
            "artist": _metadata_value(metadata.get("Artist")),
        }
    return None


def _download_cached_image(url: str, output_path: Path, cache_dir: Path, *, cache_key: str) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{_slug(cache_key)}_{hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]}.png"
    if cache_path.exists():
        shutil.copyfile(cache_path, output_path)
        return output_path

    _download_and_fit_image(url, cache_path)
    shutil.copyfile(cache_path, output_path)
    return output_path


def _download_and_fit_image(url: str, output_path: Path) -> Path:
    import requests

    response = requests.get(url, headers={"User-Agent": "youtube-agent/0.1"}, timeout=60)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content)).convert("RGB")
    ImageOps.fit(image, VIDEO_SIZE, method=Image.Resampling.LANCZOS).save(output_path)
    return output_path


def _search_query(scene: DocumentaryScene) -> str:
    title = scene.title.split(":", 1)[-1].strip()
    title_words = _keywords(title, limit=4)
    narration_words = _keywords(scene.narration, limit=4)
    return " ".join(dict.fromkeys([*title_words, *narration_words])) or title or scene.title


def _keywords(text: str, *, limit: int) -> list[str]:
    stop_words = {
        "about",
        "after",
        "another",
        "before",
        "begins",
        "documentary",
        "every",
        "layer",
        "reveals",
        "scene",
        "story",
        "their",
        "there",
        "these",
        "those",
        "through",
        "with",
    }
    words = re.findall(r"[A-Za-z][A-Za-z-]{2,}", text)
    keywords = []
    for word in words:
        normalized = word.lower()
        if normalized in stop_words:
            continue
        keywords.append(word)
        if len(keywords) == limit:
            break
    return keywords


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "wikimedia-image"


def _metadata_value(value: object) -> str | None:
    if isinstance(value, dict):
        value = value.get("value")
    if value is None:
        return None
    return " ".join(str(value).replace("<br>", " ").split())


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
    draw.text((130, 1190), "FREE WIKIMEDIA DOCUMENTARY", font=small_font, fill=(218, 184, 99))

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
