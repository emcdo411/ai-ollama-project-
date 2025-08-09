
import json
from typing import List, Dict, Callable
from .chain import analyze, plan, generate

def must_include(text: str, substrings: List[str]) -> bool:
    return all(s.lower() in text.lower() for s in substrings)

def is_json_like(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except Exception:
        return False

def run_basic_evals() -> Dict[str, bool]:
    results = {}
    analysis = analyze("Summarize key benefits of local LLMs.", context="Local models can be private and offline.")
    results["analysis_has_bullets"] = ("-" in analysis or "*" in analysis)

    planning = plan(analysis, output_format="markdown")
    results["plan_is_json"] = is_json_like(planning)

    final = generate(planning, style_guide="Use numbered lists where appropriate.")
    results["final_mentions_local"] = must_include(final, ["local"])

    return results
