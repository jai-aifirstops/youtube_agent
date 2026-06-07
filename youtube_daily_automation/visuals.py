from __future__ import annotations

import hashlib
import re
import shutil
import textwrap
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .documentary import DocumentaryPlan, DocumentaryScene


COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
USER_AGENT = "youtube-agent/0.1 (https://github.com/jai-aifirstops/youtube_agent; free documentary automation)"
VIDEO_SIZE = (1920, 1080)
ARTWORK_SIZE = (2304, 1296)
MIN_REAL_IMAGE_RATIO = 0.60


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
    image_url: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def prepare_scene_visual_assets(
    plan: DocumentaryPlan,
    assets_dir: Path,
    *,
    provider: str,
    allow_fallback: bool = False,
) -> list[SceneVisualAsset]:
    assets_dir.mkdir(parents=True, exist_ok=True)
    if provider == "fallback":
        assets = _generate_fallback_assets(plan, assets_dir)
        _log_visual_summary(assets)
        return assets
    if provider != "wikimedia":
        raise ValueError("IMAGE_PROVIDER must be wikimedia or fallback.")
    assets = [_wikimedia_asset_or_fallback(scene, assets_dir, topic=_topic_from_plan(plan)) for scene in plan.scenes]
    _log_visual_summary(assets)
    real_count = _real_image_count(assets)
    required_count = int(len(assets) * MIN_REAL_IMAGE_RATIO + 0.999)
    if real_count < required_count and not allow_fallback:
        raise RuntimeError(
            "Wikimedia image coverage too low: "
            f"{real_count}/{len(assets)} real images downloaded; at least {required_count} required. "
            "Re-run with --allow-fallback to permit fallback cards."
        )
    return assets


def _wikimedia_asset_or_fallback(scene: DocumentaryScene, assets_dir: Path, *, topic: str) -> SceneVisualAsset:
    query = _search_query(scene)
    try:
        result = _find_real_image(scene, topic=topic)
        if result is None:
            raise RuntimeError("No Wikimedia or Wikipedia image result found.")
        output_path = assets_dir / f"{result['provider']}_scene_{scene.number:02d}.png"
        _download_cached_image(result["url"], output_path, assets_dir / "cache", cache_key=result["query"])
        return SceneVisualAsset(
            scene_number=scene.number,
            path=str(output_path),
            provider=result["provider"],
            prompt=scene.image_prompt,
            source_title=result.get("title"),
            source_url=result.get("description_url"),
            license_name=result.get("license"),
            artist=result.get("artist"),
            search_query=result.get("query"),
            image_url=result.get("url"),
        )
    except Exception as error:
        print(f"Wikimedia image lookup failed for scene {scene.number}; using fallback art card. Last error: {error}")
        output_path = assets_dir / f"scene_{scene.number:02d}.png"
        _create_fallback_art_card(scene, output_path)
        return SceneVisualAsset(scene.number, str(output_path), "fallback", scene.image_prompt, search_query=query)


def _find_real_image(scene: DocumentaryScene, *, topic: str) -> dict | None:
    queries = _query_candidates(scene, topic=topic)
    for query in queries:
        result = _search_wikimedia_image(query)
        if result:
            result["query"] = query
            result["provider"] = "wikimedia"
            return result

    for query in queries:
        result = _wikipedia_summary_image(query)
        if result:
            result["query"] = query
            result["provider"] = "wikipedia"
            return result
    return None


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
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    pages_payload = response.json().get("query", {}).get("pages", {})
    pages = pages_payload.values() if isinstance(pages_payload, dict) else pages_payload
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


def _wikipedia_summary_image(query: str) -> dict | None:
    import requests

    title = quote(query.replace(" ", "_"), safe="")
    response = requests.get(WIKIPEDIA_SUMMARY_URL.format(title=title), headers={"User-Agent": USER_AGENT}, timeout=30)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    payload = response.json()
    image = payload.get("thumbnail") or payload.get("originalimage")
    url = image.get("source") if isinstance(image, dict) else None
    if not url:
        return None
    return {
        "title": payload.get("title"),
        "url": url,
        "description_url": (payload.get("content_urls") or {}).get("desktop", {}).get("page"),
        "license": "Wikipedia summary thumbnail",
        "artist": None,
    }


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

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content)).convert("RGB")
    ImageOps.fit(image, VIDEO_SIZE, method=Image.Resampling.LANCZOS).save(output_path)
    return output_path


def _search_query(scene: DocumentaryScene) -> str:
    title = scene.title.split(":", 1)[-1].strip()
    title_words = _keywords(title, limit=4)
    narration_words = _keywords(scene.narration, limit=4)
    return " ".join(dict.fromkeys([*title_words, *narration_words])) or title or scene.title


def _query_candidates(scene: DocumentaryScene, *, topic: str) -> list[str]:
    title = scene.title.split(":", 1)[-1].strip()
    topic_keywords = _keywords(topic, limit=3)
    title_keywords = _keywords(title, limit=4)
    narration_keywords = _keywords(scene.narration, limit=4)
    candidates = [
        _search_query(scene),
        " ".join([*title_keywords, *topic_keywords]),
        title,
        " ".join([*topic_keywords, *narration_keywords[:2]]),
        topic,
        " ".join(topic_keywords),
    ]
    return [candidate for candidate in dict.fromkeys(c.strip() for c in candidates) if candidate]


def _topic_from_plan(plan: DocumentaryPlan) -> str:
    return plan.title.split(":", 1)[0].strip() or plan.title


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


def _log_visual_summary(assets: list[SceneVisualAsset]) -> None:
    real_assets = [asset for asset in assets if asset.provider in {"wikimedia", "wikipedia"}]
    fallback_assets = [asset for asset in assets if asset.provider == "fallback"]
    print("Visual asset summary:")
    print(f"  total scenes: {len(assets)}")
    print(f"  images downloaded: {len(real_assets)}")
    print(f"  fallback cards used: {len(fallback_assets)}")
    print("  image URLs:")
    for asset in real_assets:
        print(f"    scene {asset.scene_number:02d}: {asset.image_url or asset.source_url}")


def _real_image_count(assets: list[SceneVisualAsset]) -> int:
    return sum(1 for asset in assets if asset.provider in {"wikimedia", "wikipedia"})


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
