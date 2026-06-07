# YouTube Documentary Automation Agent

This project generates a 6-10 minute cinematic documentary every day, adds provider-based narration, subtitles, background music, camera motion, transitions, and uploads the exported 1080p MP4 to an existing YouTube channel through the YouTube Data API.

Important: automation cannot create a YouTube account or channel for you. Create the Google account/channel manually, then authorize this app to upload to that channel.

## What it does

- Fetches daily context from Wikimedia's "On this day" feed, with built-in fallback facts.
- Writes a documentary-style script.
- Splits the story into 20-40 scenes.
- Generates an AI image prompt and narration for every scene.
- Generates one OpenAI image per scene when `OPENAI_API_KEY` is available.
- Falls back to local Pillow art cards when OpenAI images are unavailable.
- Generates narration with OpenAI TTS by default, falls back to Edge TTS, then silent placeholder audio.
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

Render the default 8-minute documentary without uploading:

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
6. Add these GitHub Actions secrets:
   - `OPENAI_API_KEY`: used for OpenAI image generation and OpenAI TTS.
   - `YOUTUBE_TOKEN_JSON`: authorized OAuth token JSON for uploads.
   - `YOUTUBE_CLIENT_SECRET_JSON`: OAuth client secret JSON for channel authorization records.
7. Optional repository variables:
   - `YOUTUBE_PRIVACY_STATUS`: `private`, `unlisted`, or `public` (defaults to `private`).
   - `CHANNEL_NAME`: text used in the generated description and footer.
   - `DOCUMENTARY_TOPIC`: topic override for the next run.
   - `TTS_PROVIDER`: `openai`, `edge`, or `silent` (defaults to `openai`).
   - `IMAGE_PROVIDER`: `openai` or `fallback` (defaults to `openai`).

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `OUTPUT_DIR` | `dist` | Generated assets directory |
| `TOPIC_COUNT` | `8` | Number of source context items |
| `SCENE_COUNT` | `30` | Number of documentary scenes |
| `VIDEO_LENGTH_SECONDS` | `480` | Target video length, 360-600 seconds |
| `YOUTUBE_PRIVACY_STATUS` | `private` | Upload visibility |
| `YOUTUBE_CATEGORY_ID` | `24` | YouTube category |
| `DOCUMENTARY_TOPIC` | daily topic | Topic override |
| `IMAGE_PROVIDER` | `openai` | `openai` or `fallback` visual provider |
| `OPENAI_API_KEY` | unset | OpenAI image and TTS key |
| `OPENAI_IMAGE_MODEL` | `dall-e-3` | OpenAI image model |
| `OPENAI_IMAGE_SIZE` | `1792x1024` | OpenAI image output size |
| `TTS_PROVIDER` | `openai` | `openai`, `edge`, or `silent` |
| `OPENAI_TTS_MODEL` | `gpt-4o-mini-tts` | OpenAI TTS model |
| `OPENAI_TTS_VOICE` | `onyx` | Natural documentary-style OpenAI voice |
| `EDGE_TTS_VOICE` | `en-US-GuyNeural` | Edge fallback voice |
| `EDGE_TTS_RATE` | `+0%` | Edge fallback speech rate |
| `EDGE_TTS_PITCH` | `+0Hz` | Edge fallback speech pitch |
| `TTS_ATTEMPTS` | `3` | Provider retry attempts before silent fallback |
| `TRANSITION_SECONDS` | `1.0` | Fade transition length |
| `YOUTUBE_TOKEN_JSON` | unset | Authorized token JSON for CI uploads |
| `YOUTUBE_CLIENT_SECRET_JSON` | unset | OAuth client secret JSON reference |
| `YOUTUBE_TOKEN_FILE` | unset | Local token file path |

## Generated files

Each run writes:

- `documentary_plan.json`: complete title, description, scenes, narration, and prompts.
- `image_prompts.json`: one AI image prompt per scene.
- `scene_assets/ai_scene_XX.png`: OpenAI generated scene images when `OPENAI_API_KEY` is available.
- `scene_assets/scene_XX.png`: fallback Pillow art cards when OpenAI images are unavailable.
- `narration.txt`: full narration sent to TTS.
- `subtitles.srt`: timed subtitles.
- `background_music.wav`: generated music bed.
- `daily_documentary_<date>.mp4`: exported 1080p video.

## Tests

```bash
python -m pytest
```