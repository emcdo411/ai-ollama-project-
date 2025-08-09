
import requests
from typing import List, Dict, Any, Optional

OLLAMA_URL = "http://localhost:11434/api/chat"

def chat(model: str, messages: List[Dict[str, str]], temperature: float = 0.2, top_p: float = 0.9, stream: bool = False) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "options": {
            "temperature": temperature,
            "top_p": top_p
        },
        "stream": stream
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    # Ollama returns a dict with 'message':{'content':...} for non-stream
    if isinstance(data, dict) and 'message' in data and 'content' in data['message']:
        return data['message']['content']
    # some versions may return 'content' at top-level
    if isinstance(data, dict) and 'content' in data:
        return data['content']
    return str(data)
