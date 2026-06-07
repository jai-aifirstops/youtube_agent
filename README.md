# YouTube Daily Automation Agent

This project generates a one-minute "top 10 interesting topics" video every day, adds voice narration and generated background music, and can upload the result to an existing YouTube channel through the YouTube Data API.

Important: automation cannot create a YouTube account or channel for you. Create the Google account/channel manually, then authorize this app to upload to that channel.

## What it does

- Fetches daily topic ideas from Wikimedia's "On this day" feed, with built-in fallback facts.
- Builds a concise narration script and YouTube description.
- Generates TTS narration with `edge-tts`.
- Retries TTS generation and falls back to silent placeholder audio if Edge TTS is unavailable.
- Generates royalty-free background music locally.
- Renders a vertical MP4 video suitable for Shorts-style content.
- Uploads through OAuth using the YouTube Data API.
- Runs daily from `.github/workflows/daily-youtube.yml`.

## Local setup

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Dry-run without network, TTS, video rendering, or upload:

```bash
youtube-daily run --offline --dry-run --date 2026-06-06
```

Render a local video without uploading:

```bash
youtube-daily run
```

Render faster for local testing without voice generation:

```bash
youtube-daily run --no-voice
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

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `OUTPUT_DIR` | `dist` | Generated assets directory |
| `TOPIC_COUNT` | `10` | Number of topics per video |
| `VIDEO_LENGTH_SECONDS` | `60` | Target video length |
| `YOUTUBE_PRIVACY_STATUS` | `private` | Upload visibility |
| `YOUTUBE_CATEGORY_ID` | `24` | YouTube category |
| `TTS_VOICE` | `en-US-AriaNeural` | Narration voice |
| `TTS_RATE` | `+0%` | Narration speed |
| `TTS_PITCH` | `+0Hz` | Narration pitch |
| `YOUTUBE_TOKEN_JSON` | unset | Authorized token JSON for CI uploads |
| `YOUTUBE_TOKEN_FILE` | unset | Local token file path |

## Tests

```bash
python -m pytest
```