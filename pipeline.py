# pipeline.py
# Robust JSON-extracting pipeline for Windows + Ollama
# Requires: pip install ollama
from __future__ import annotations

import os
import re
import json
from typing import Any, Dict, List, Tuple, Optional
from ollama import Client

# Use an actually-installed default model; override with OLLAMA_MODEL env var.
MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")  # or "llama3:8b", "mistral:latest"
HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
TIMEOUT_S = 120

# === hardened system prompt with authoritative facts ===
GEN_SYS = (
    "You are a precise JSON generator. "
    "Return ONLY valid JSON with keys: analysis (array), plan (array), output (string). "
    "No code fences, no prose, no markdown—just JSON. "
    "Authoritative facts you MUST follow:\n"
    "- The Python package is 'ollama' (import via: from ollama import Client). Not 'ollamapy'.\n"
    "- The default Ollama server listens at http://127.0.0.1:11434 .\n"
    "- Do NOT use 'ollama start --port ...'. Ollama runs as a service/daemon; 'ollama serve' is rarely needed on Windows installer.\n"
    "- Example models: 'phi3:mini', 'llama3:8b', 'mistral:latest'.\n"
    "- Install the Python client with: pip install ollama.\n"
    "- Provide a minimal, correct Windows Quickstart for Ollama + Python. "
    "If you are unsure, output 'UNKNOWN' for that field instead of guessing."
)

PROMPT_TMPL = """\
Goal:
{goal}

Deliverable:
{deliverable}

Constraints:
- Return STRICT JSON only.
- Keys: analysis (array of objects or strings), plan (array of objects or strings), output (string).
- No markdown, no headings, no backticks, no commentary.
"""

# ---------- JSON tolerant parsing helpers ----------

SMART_QUOTES = {
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
    "\u2018": "'", "\u2019": "'", "\u2032": "'", "\u2033": '"'
}

def _desmart(s: str) -> str:
    for k, v in SMART_QUOTES.items():
        s = s.replace(k, v)
    return s

def _strip_code_fences(s: str) -> str:
    # Prefer ```json blocks
    fence_json = re.findall(r"```json\s*(.*?)\s*```", s, flags=re.IGNORECASE | re.DOTALL)
    if fence_json:
        return fence_json[0].strip()
    # Any code fence
    fence_any = re.findall(r"```\s*(.*?)\s*```", s, flags=re.DOTALL)
    if fence_any:
        return fence_any[0].strip()
    return s

def _find_first_balanced_brace_block(s: str) -> Optional[str]:
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    return None

def _remove_trailing_commas(s: str) -> str:
    return re.sub(r",\s*([}\]])", r"\1", s)

def _extract_first_bracket_array(s: str) -> Optional[str]:
    start = s.find("[")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    return None

def _safe_json_array_or_text(s: str) -> Any:
    t = _strip_code_fences(_desmart(s)).strip()
    # Try to load as JSON
    try:
        j = json.loads(t)
        if isinstance(j, (list, dict, str)):
            return j
    except Exception:
        pass
    # Try to locate [ ... ] block
    arr = _extract_first_bracket_array(t)
    if arr is not None:
        try:
            return json.loads(arr)
        except Exception:
            repaired = _remove_trailing_commas(arr)
            try:
                return json.loads(repaired)
            except Exception:
                pass
    # Fallback to newline-split strings
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    return lines if lines else t

def _coerce_json(text: str) -> Dict[str, Any]:
    """Try very hard to coerce model text into a JSON dict with analysis/plan/output."""
    raw = _desmart(text).strip()
    # Fast path
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Strip code fences
    stripped = _strip_code_fences(raw)
    try:
        obj = json.loads(stripped)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Balanced brace block
    block = _find_first_balanced_brace_block(raw)
    if block:
        try:
            obj = json.loads(block)
            if isinstance(obj, dict):
                return obj
        except Exception:
            repaired = _remove_trailing_commas(block)
            try:
                obj = json.loads(repaired)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass

    # As a last resort, parse === ANALYSIS === / === PLAN === / === OUTPUT === sections
    def sect(name: str) -> Optional[str]:
        m = re.search(
            rf"===\s*{name}\s*===\s*(.*?)(?:(?:\n\s*===)|\Z)",
            raw, flags=re.IGNORECASE | re.DOTALL
        )
        if m:
            return m.group(1).strip()
        return None

    analysis_s = sect("ANALYSIS")
    plan_s = sect("PLAN")
    output_s = sect("OUTPUT")

    if any([analysis_s, plan_s, output_s]):
        result: Dict[str, Any] = {}
        if analysis_s:
            result["analysis"] = _safe_json_array_or_text(analysis_s)
        if plan_s:
            result["plan"] = _safe_json_array_or_text(plan_s)
        if output_s:
            out_try = _strip_code_fences(output_s).strip()
            result["output"] = out_try
        return result

    raise ValueError("Could not coerce model output into JSON.")

def _loads_or_explain(label: str, text: str) -> Dict[str, Any]:
    try:
        return _coerce_json(text)
    except Exception as e:
        preview = text[:1000].replace("\n", "\\n")
        raise RuntimeError(
            f"{label} was not valid JSON. First 1000 chars: {preview}"
        ) from e

# ---------- Model call ----------

def _complete_json(system: str, prompt: str, model: str = MODEL) -> Dict[str, Any]:
    client = Client(host=HOST, timeout=TIMEOUT_S)
    stream = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        stream=True,
        options={"temperature": 0.2},
    )
    chunks: List[str] = []
    for chunk in stream:
        content = chunk.get("message", {}).get("content", "")
        if content:
            chunks.append(content)
    raw = "".join(chunks)

    try:
        return _loads_or_explain("Model JSON", raw)
    except RuntimeError:
        retry_prompt = (
            "Return ONLY strict JSON. No markdown or code fences. "
            "Keys: analysis(array), plan(array), output(string)."
        )
        stream2 = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": retry_prompt},
            ],
            stream=True,
            options={"temperature": 0.0},
        )
        chunks2: List[str] = []
        for chunk in stream2:
            content = chunk.get("message", {}).get("content", "")
            if content:
                chunks2.append(content)
        raw2 = "".join(chunks2)
        return _loads_or_explain("Model JSON (retry)", raw2)

# ---------- sanitizer + README writer ----------

def _fix_ollama_hallucinations(text: str) -> str:
    """Normalize common bad suggestions and ensure correct Quickstart details."""
    if not isinstance(text, str):
        return text
    fixed = text

    # Wrong Python package -> correct one
    fixed = re.sub(r"\bollamapy\b", "ollama", fixed, flags=re.IGNORECASE)

    # Remove bogus 'ollama start ...' or arbitrary port flags
    fixed = re.sub(r"(?mi)^\s*ollama\s+start.*$", "", fixed)
    # Normalize 'ollama serve' if present
    fixed = re.sub(r"(?mi)^\s*ollama\s+serve.*$", "ollama serve", fixed)

    # Normalize host/port mentions
    fixed = re.sub(r"127\.0\.0\.1:?\d{0,5}", "127.0.0.1:11434", fixed)
    fixed = re.sub(r"localhost:?\d{0,5}", "127.0.0.1:11434", fixed)

    # Ensure example model names are valid
    if "llama3" in fixed and "llama3:" not in fixed:
        fixed = fixed.replace("llama3", "llama3:8b")

    # Ensure the Python import example is correct (no-op but explicit)
    fixed = fixed.replace("from ollama import Client", "from ollama import Client")

    # Collapse excessive blank lines
    fixed = re.sub(r"\n{3,}", "\n\n", fixed)

    return fixed


README_HEADER = r"""# Local LLM Lab (Windows) — Ollama + Python

> Minimal quickstart to pull a model, chat via Python, and understand the folder layout.

"""

README_FOOTER = r"""

## Folder Structure
````

local-llm-lab/
├─ pipeline.py
├─ README.md
└─ .venv/                 # optional virtual environment

````

## Quick Commands (PowerShell)
```powershell
# (optional) create & activate venv
python -m venv .venv
.\.venv\Scripts\activate

# install python client
pip install ollama

# pull a small model for testing (or any you prefer)
ollama pull phi3:mini

# run the pipeline
python .\pipeline.py
````

## Notes

* Ollama default API: [http://127.0.0.1:11434](http://127.0.0.1:11434)
* Python client import: from ollama import Client
* Change default model via: \$env\:OLLAMA\_MODEL = "phi3\:mini"  (or edit MODEL in pipeline.py)
  """

# ---------- Orchestration ----------

def _normalize_sections(obj: Dict[str, Any]) -> Tuple[Any, Any, str]:
    keys = {k.lower(): k for k in obj.keys()}

    def pick(*names: str) -> Optional[str]:
        for n in names:
            if n in keys:
                return keys[n]
        return None

    a_key = pick("analysis")
    p_key = pick("plan")
    o_key = pick("output", "result", "results", "readme", "document")

    analysis = obj.get(a_key, [])
    plan = obj.get(p_key, [])
    output = obj.get(o_key, "")

    if isinstance(analysis, str):
        analysis = [analysis]
    if isinstance(plan, str):
        plan = [plan]
    if not isinstance(output, str):
        try:
            output = json.dumps(output, indent=2)
        except Exception:
            output = str(output)

    return analysis, plan, output
def run(goal: str, deliverable: str) -> Tuple[Any, Any, str]:
    prompt = PROMPT_TMPL.format(goal=goal, deliverable=deliverable)
    obj = _complete_json(GEN_SYS, prompt, MODEL)
    return _normalize_sections(obj)

# ---------- CLI ----------

if __name__ == "__main__":
    goal = "Stand up a Windows-based Local LLM Lab using Ollama + Python."
    deliverable = "Generate a minimal README.md with Quickstart, commands, and folder structure."
    analysis, plan, output = run(goal, deliverable)

    # Pretty print sections
    print("\n=== ANALYSIS ===")
    try:
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
    except Exception:
        print(analysis)

    print("\n=== PLAN ===")
    try:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
    except Exception:
        print(plan)

    # Sanitize and write README.md
    clean_output = _fix_ollama_hallucinations(output)
    if not clean_output.strip() or clean_output.strip().upper() == "UNKNOWN":
        clean_output = README_HEADER + README_FOOTER
    else:
        clean_output = README_HEADER + clean_output.strip() + "\n" + README_FOOTER

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(clean_output)

    print("\n=== OUTPUT ===")
    print(clean_output)
    print("\n(Wrote README.md)")


