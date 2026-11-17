# Troubleshooting

## `docker compose` is an unknown command

`docker compose` (with a space) is the Compose v2 plugin for the Docker CLI. Check what is installed:

```bash
docker version            # Docker itself
docker compose version    # Compose v2 plugin — what `docker compose up` needs
docker-compose version    # legacy standalone Compose v1, if present
```

Install the plugin:

- **macOS / Windows:** install or update Docker Desktop; it includes Compose v2.
- **Ubuntu / Debian with Docker's apt repository:** `sudo apt-get update && sudo apt-get install docker-compose-plugin`
- **Fedora / RHEL with Docker's repository:** `sudo dnf install docker-compose-plugin`
- **Any Linux, manual install** (x86_64 shown; use `aarch64` on ARM):

  ```bash
  mkdir -p ~/.docker/cli-plugins
  curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
    -o ~/.docker/cli-plugins/docker-compose
  chmod +x ~/.docker/cli-plugins/docker-compose
  docker compose version
  ```

If only the legacy `docker-compose` (v1.27 or newer) is available, `docker-compose up` reads the same file.

## Live ventures say the model is not ready

Check http://localhost:8000/api/system/status — the `model.detail` field says what is wrong.

- **"GEMINI_API_KEY is not set"**: create a key at https://aistudio.google.com/apikey, put `GEMINI_API_KEY=...` in
  `.env` next to `docker-compose.yml`, then `docker compose up` again (Compose reads `.env` at start-up).
- **"rejected the key"**: the key is wrong, revoked, or the Gemini API is not available for its project or region.
- **"rate limit or daily quota reached"**: free-tier limits. Wait a minute, or set `GEMINI_MODEL` to another free model.
- **Ollama** (`MODEL_PROVIDER=ollama`): the `ollama-pull` service may still be downloading, or the tag in
  `OLLAMA_MODEL` does not exist; see `docker compose --profile ollama logs ollama-pull`.

Scripted demo ventures work meanwhile.
