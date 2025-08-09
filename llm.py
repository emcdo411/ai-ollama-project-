# llm.py
import os
import json
import requests

BASE_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
CHAT_URL = f"{BASE_URL}/api/chat"

def _raise_for_ollama_errors(data):
    # Ollama returns {"error": "..."} on errors
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"Ollama error: {data['error']}")

def chat(messages, model="mistral", stream=False, temperature=0.7, num_predict=256, timeout=600, **kwargs):
    """
    messages: list of {"role": "user"|"system"|"assistant", "content": "..."}
    Returns:
      - if stream=False: str (assistant content)
      - if stream=True:  generator of str chunks
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }
    payload.update(kwargs)

    resp = requests.post(CHAT_URL, json=payload, stream=stream, timeout=timeout)
    resp.raise_for_status()

    if not stream:
        data = resp.json()
        _raise_for_ollama_errors(data)
        content = (data.get("message") or {}).get("content", "")
        if not content:
            # Surface the raw response so callers see what's wrong
            raise RuntimeError(f"Empty assistant content. Raw response: {json.dumps(data)[:800]}")
        return content

    # Streaming: NDJSON
    def gen():
        any_yield = False
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            _raise_for_ollama_errors(chunk)
            msg = chunk.get("message", {})
            if "content" in msg:
                any_yield = True
                yield msg["content"]
            if chunk.get("done"):
                break
        if not any_yield:
            raise RuntimeError("Streaming produced no chunks.")
    return gen()

def ask(prompt, **kwargs):
    return chat([{"role": "user", "content": prompt}], stream=False, **kwargs)

def ask_stream(prompt, **kwargs):
    return chat([{"role": "user", "content": prompt}], stream=True, **kwargs)
