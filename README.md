# YouTube Documentary Automation Agent

This project generates a 6-10 minute cinematic documentary every day, adds provider-based narration, subtitles, background music, camera motion, transitions, and uploads the exported 1080p MP4 to an existing YouTube channel through the YouTube Data API.

Important: automation cannot create a YouTube account or channel for you. Create the Google account/channel manually, then authorize this app to upload to that channel.

## What it does

- Fetches daily context from Wikimedia's "On this day" feed, with built-in fallback facts.
- Writes a documentary-style script.
- Splits the story into 20-40 scenes.
- Generates an AI image prompt and narration for every scene.
- Generates narration with OpenAI TTS or ElevenLabs.
- Falls back to silent placeholder audio if TTS fails, so upload is not blocked.
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
6. Add one TTS provider secret:
   - OpenAI: `OPENAI_API_KEY`
   - ElevenLabs: `ELEVENLABS_API_KEY`
7. Optional repository variables:
   - `YOUTUBE_PRIVACY_STATUS`: `private`, `unlisted`, or `public` (defaults to `private`).
   - `CHANNEL_NAME`: text used in the generated description and footer.
   - `DOCUMENTARY_TOPIC`: topic override for the next run.
   - `TTS_PROVIDER`: `openai`, `elevenlabs`, or `silent` (defaults to `openai`).

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
| `TTS_PROVIDER` | `openai` | `openai`, `elevenlabs`, or `silent` |
| `OPENAI_API_KEY` | unset | OpenAI TTS key |
| `OPENAI_TTS_MODEL` | `gpt-4o-mini-tts` | OpenAI TTS model |
| `OPENAI_TTS_VOICE` | `alloy` | OpenAI TTS voice |
| `ELEVENLABS_API_KEY` | unset | ElevenLabs TTS key |
| `ELEVENLABS_VOICE_ID` | `21m00Tcm4TlvDq8ikWAM` | ElevenLabs voice |
| `ELEVENLABS_MODEL_ID` | `eleven_multilingual_v2` | ElevenLabs model |
| `TTS_ATTEMPTS` | `3` | Provider retry attempts before silent fallback |
| `TRANSITION_SECONDS` | `1.0` | Fade transition length |
| `YOUTUBE_TOKEN_JSON` | unset | Authorized token JSON for CI uploads |
| `YOUTUBE_TOKEN_FILE` | unset | Local token file path |

## Generated files

Each run writes:

- `documentary_plan.json`: complete title, description, scenes, narration, and prompts.
- `image_prompts.json`: one AI image prompt per scene.
- `narration.txt`: full narration sent to TTS.
- `subtitles.srt`: timed subtitles.
- `background_music.wav`: generated music bed.
- `daily_documentary_<date>.mp4`: exported 1080p video.

## Tests

```bash
python -m pytest
```