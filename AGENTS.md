# AGENTS.md

Guidance for AI agents working in this repository.

## Repository status

`youtube_agent` is currently an **empty scaffold**. The only tracked source file is `README.md` (title: `# youtube_agent`). There is no application code, dependency manifest, Dockerfile, CI config, or run scripts yet.

## Cursor Cloud specific instructions

### Services

There are **no services to start**. No dev server, database, or container stack is defined in this repository.

### Dependencies

No package manager lockfile or install step exists (`package.json`, `requirements.txt`, `pyproject.toml`, etc. are absent). The VM update script is a no-op until dependencies are added.

### Lint / test / build / run

| Task   | Command | Status |
|--------|---------|--------|
| Lint   | —       | Not configured |
| Test   | —       | Not configured |
| Build  | —       | Not configured |
| Run    | —       | No application entrypoint |

### VM tooling

The cloud VM provides standard development tools (git, Node.js via nvm, Python 3). Once application code and manifests are added, update this section with the real install, start, and test commands.

### Likely future stack (inferred from repo name)

When implementation begins, this project may need YouTube/Google API credentials (e.g. `YOUTUBE_API_KEY`, OAuth client ID/secret) and possibly an LLM API key. None are required or referenced in the repo today.
