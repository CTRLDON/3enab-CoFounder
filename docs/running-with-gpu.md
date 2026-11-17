# Running the local model on a GPU

This applies only to the Ollama provider (`MODEL_PROVIDER=ollama docker compose --profile ollama up`), which runs on the CPU by default, which works but is slow for a 9B model. With an NVIDIA GPU and the
NVIDIA Container Toolkit installed, create `docker-compose.override.yml` next to `docker-compose.yml`:

```yaml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

Then run `MODEL_PROVIDER=ollama docker compose --profile ollama up`. Compose merges the override automatically.

On smaller machines, choose a smaller model in `.env`, for example `OLLAMA_MODEL=qwen3:8b`, and run
the same command again; the `ollama-pull` service pulls the configured tag. Check what the backend sees at
http://localhost:8000/api/system/status.
