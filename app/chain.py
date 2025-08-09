
from typing import Dict, Any
from .ollama_client import chat

MODEL = "mistral:7b"

SYSTEM_ANALYZE = "You are an analyst. Extract key points, entities, and risks as bullet points."
SYSTEM_PLAN = "You are a planner. Produce a concise JSON plan with fields: objective, steps[], risks[], success_criteria[]"
SYSTEM_WRITE = "You are a writer. Using the plan, produce the final deliverable. Be precise and follow the format requested."

def analyze(task: str, context: str = "") -> str:
    msgs = [
        {"role":"system","content": SYSTEM_ANALYZE},
        {"role":"user","content": f"Task: {task}\nContext:\n{context}"}
    ]
    return chat(MODEL, msgs)

def plan(analysis: str, output_format: str = "markdown") -> str:
    msgs = [
        {"role":"system","content": SYSTEM_PLAN},
        {"role":"user","content": f"Create a plan. Output JSON only. Output_format: {output_format}.\nAnalysis:\n{analysis}"}
    ]
    return chat(MODEL, msgs)

def generate(plan_json: str, style_guide: str = "") -> str:
    msgs = [
        {"role":"system","content": SYSTEM_WRITE},
        {"role":"user","content": f"Follow this style guide:\n{style_guide}\nUse this plan (JSON):\n{plan_json}"}
    ]
    return chat(MODEL, msgs)
