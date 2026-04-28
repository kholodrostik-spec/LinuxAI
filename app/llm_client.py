import requests

from app.config import LLM_MODEL

OLLAMA_URL = "http://localhost:11434/api/chat"

SYSTEM_PROMPT = (
    "You are LinuxAI, a careful Linux setup assistant. "
    "Use only the provided SQL facts and vector documents when possible. "
    "Do not invent package names, driver names, or commands. "
    "Start with safe diagnostic commands before installation commands. "
    "Always explain what each command does. "
    "Always include verification steps. "
    "Mark medium-risk and high-risk commands clearly. "
    "Always respond in English."
)


def ask_llm(prompt: str) -> str:
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        "stream": False,
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=240)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot connect to Ollama at {OLLAMA_URL}. "
            "Make sure Ollama is running: systemctl start ollama"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Ollama request timed out after 240 seconds. "
            "The model may still be loading — try again."
        )
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"Ollama returned an error: {exc}") from exc

    data = response.json()
    return data["message"]["content"]
