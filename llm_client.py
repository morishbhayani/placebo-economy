import os
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(
    dotenv_path=Path(__file__).resolve().parent / ".env"
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemini-3.8-flash"
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:3b"
)

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/generate"
)


# =========================================================
# GEMINI THROUGH OPENROUTER
# =========================================================

def _gemini_generate(prompt, max_tokens=2048):

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured"
        )

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "reasoning": {
                "effort": "minimal"
            },
            "max_tokens": max_tokens
        },
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    content = (
        data
        .get("choices", [{}])[0]
        .get("message", {})
        .get("content")
    )

    if not content:
        raise RuntimeError(
            "Gemini returned no visible content"
        )

    return content.strip()


# =========================================================
# GROQ
# =========================================================

def _groq_generate(prompt, max_tokens=2048):

    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not configured"
        )

    if not GROQ_MODEL:
        raise RuntimeError(
            "GROQ_MODEL is not configured"
        )

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens
        },
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    content = (
        data
        .get("choices", [{}])[0]
        .get("message", {})
        .get("content")
    )

    if not content:
        raise RuntimeError(
            "Groq returned no visible content"
        )

    return content.strip()


# =========================================================
# LOCAL OLLAMA
# =========================================================

def _ollama_generate(prompt, max_tokens=2048):

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens
            }
        },
        timeout=180
    )

    response.raise_for_status()

    data = response.json()

    content = data.get("response", "")

    if not content:
        raise RuntimeError(
            "Ollama returned no visible content"
        )

    return content.strip()


# =========================================================
# PROVIDER ROUTING
# =========================================================

PROVIDERS = {
    "Gemini": _gemini_generate,
    "Groq": _groq_generate,
    "Ollama": _ollama_generate
}


def provider_order(primary):

    if primary == "Gemini":
        return ["Gemini", "Groq", "Ollama"]

    if primary == "Groq":
        return ["Groq", "Gemini", "Ollama"]

    if primary == "Ollama":
        return ["Ollama", "Gemini", "Groq"]

    return ["Gemini", "Groq", "Ollama"]


def generate_text(
    prompt,
    primary="Gemini",
    max_tokens=2048,
    show_provider=True
):

    errors = []

    for provider in provider_order(primary):

        try:

            result = PROVIDERS[provider](
                prompt,
                max_tokens=max_tokens
            )

            if show_provider:
                print(
                    f"LLM provider: {provider}"
                )

            return result

        except Exception as error:

            errors.append(
                f"{provider}: {str(error)[:160]}"
            )

            if show_provider:
                print(
                    f"{provider} unavailable — "
                    "trying fallback."
                )

    raise RuntimeError(
        "All LLM providers failed. "
        + " | ".join(errors)
    )
