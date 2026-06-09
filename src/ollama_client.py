"""ollama_client.py — copied verbatim from tradesresource."""
import json
import os
import urllib.error
import urllib.request

DEFAULT_OLLAMA_MODEL = "llama3:latest"
DEFAULT_OLLAMA_URL = "http://localhost:11434"


def ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL).rstrip("/")


def list_ollama_models(timeout_seconds: int = 3) -> list[str]:
    try:
        request = urllib.request.Request(f"{ollama_base_url()}/api/tags")
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return sorted(model["name"] for model in payload.get("models", []))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return []


def generate_with_ollama(
    prompt: str,
    model: str = DEFAULT_OLLAMA_MODEL,
    timeout_seconds: int = 30,
) -> tuple[str | None, str | None]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 300},
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{ollama_base_url()}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            result = json.loads(response.read().decode("utf-8"))
        text = result.get("response", "").strip()
        return (text or None), None
    except urllib.error.HTTPError as exc:
        return None, f"Ollama HTTP error: {exc.code}"
    except (OSError, urllib.error.URLError) as exc:
        return None, f"Ollama unavailable: {exc}"
    except json.JSONDecodeError:
        return None, "Ollama returned an unreadable response"
