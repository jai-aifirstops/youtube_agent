# YouTube Documentary Automation Agent

This project generates a 5-8 minute cinematic documentary every day using free services, adds Edge TTS narration, subtitles, background music, camera motion, transitions, and uploads the exported 1080p MP4 to an existing YouTube channel through the YouTube Data API.

Important: automation cannot create a YouTube account or channel for you. Create the Google account/channel manually, then authorize this app to upload to that channel.

## What it does

- Fetches daily context from Wikimedia's "On this day" feed, with built-in fallback facts.
- Writes a documentary-style script.
- Splits the story into 20-30 scenes.
- Searches Wikimedia Commons for each scene.
- Downloads one relevant free Wikimedia image per scene when available.
- Falls back to local Pillow art cards only when Wikimedia lookup or download fails.
- Generates narration with free Edge TTS, then silent placeholder audio if TTS fails.
- Generates royalty-free background music locally.
- Adds Ken Burns-style zoom/pan movement, fade transitions, and burned-in subtitles.
- Writes a timed `subtitles.srt` file automatically.
- Exports a 1080p MP4.
- Uploads through OAuth using the YouTube Data API.
- Runs daily from `.github/workflows/daily-youtube.yml`.

## Local setup

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Dry-run without TTS, video rendering, or upload:

```bash
youtube-daily run --offline --dry-run --date 2026-06-06
```

Render the default 6-minute documentary without uploading:

```bash
youtube-daily run
```

Render a short local smoke test without voice generation:

```bash
youtube-daily run --offline --no-voice --allow-short-render --scene-count 3 --duration-seconds 12
```

Render and upload:

```bash
youtube-daily run --upload
```

## YouTube setup

1. Create a Google account and YouTube channel manually.
2. In Google Cloud Console, create a project, enable the YouTube Data API v3, and configure an OAuth consent screen.
3. Create an OAuth client of type "Desktop app" and download the client secret JSON.
4. Authorize the channel locally:

```bash
youtube-daily auth --client-secret-file client_secret.json --token-file token.json
```

5. Put the full contents of `token.json` into the GitHub Actions secret `YOUTUBE_TOKEN_JSON`.
6. Optional repository variables:
   - `YOUTUBE_PRIVACY_STATUS`: `private`, `unlisted`, or `public` (defaults to `private`).
   - `CHANNEL_NAME`: text used in the generated description and footer.
   - `DOCUMENTARY_TOPIC`: topic override for the next run.
   - `TTS_PROVIDER`: `edge` or `silent` (defaults to `edge`).
   - `IMAGE_PROVIDER`: `wikimedia` or `fallback` (defaults to `wikimedia`).

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `OUTPUT_DIR` | `dist` | Generated assets directory |
| `TOPIC_COUNT` | `8` | Number of source context items |
| `SCENE_COUNT` | `24` | Number of documentary scenes |
| `VIDEO_LENGTH_SECONDS` | `360` | Target video length, 300-480 seconds |
| `YOUTUBE_PRIVACY_STATUS` | `private` | Upload visibility |
| `YOUTUBE_CATEGORY_ID` | `24` | YouTube category |
| `DOCUMENTARY_TOPIC` | daily topic | Topic override |
| `IMAGE_PROVIDER` | `wikimedia` | `wikimedia` or `fallback` visual provider |
| `TTS_PROVIDER` | `edge` | `edge` or `silent` |
| `EDGE_TTS_VOICE` | `en-US-GuyNeural` | Edge narration voice |
| `EDGE_TTS_RATE` | `+0%` | Edge speech rate |
| `EDGE_TTS_PITCH` | `+0Hz` | Edge speech pitch |
| `TTS_ATTEMPTS` | `3` | Provider retry attempts before silent fallback |
| `TRANSITION_SECONDS` | `1.0` | Fade transition length |
| `YOUTUBE_TOKEN_JSON` | unset | Authorized token JSON for CI uploads |
| `YOUTUBE_TOKEN_FILE` | unset | Local token file path |

## Generated files

Each run writes:

- `documentary_plan.json`: complete title, description, scenes, narration, and prompts.
- `image_prompts.json`: one AI image prompt per scene.
- `scene_assets/wikimedia_scene_XX.png`: downloaded Wikimedia Commons images when available.
- `scene_assets/scene_XX.png`: fallback Pillow art cards when Wikimedia images are unavailable.
- `narration.txt`: full narration sent to TTS.
- `subtitles.srt`: timed subtitles.
- `background_music.wav`: generated music bed.
- `daily_documentary_<date>.mp4`: exported 1080p video.

## Tests

```bash
python -m pytest
```