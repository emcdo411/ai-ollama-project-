
import argparse, json
from app.rag import RAGIndex
from app.ollama_client import chat

MODEL = "mistral:7b"

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--question", required=True)
    p.add_argument("--k", type=int, default=3)
    args = p.parse_args()

    idx = RAGIndex()
    idx.load()
    top = idx.query(args.question, k=args.k)

    context = "\n\n".join([f"[{i+1}] {d['id']}: {d['text']}" for i, d in enumerate(top)])
    prompt = f"""Answer the user's question using ONLY the context below. Cite sources like [1], [2].
Context:
{context}

Question: {args.question}
"""
    msgs = [
        {"role":"system","content":"You answer with citations and stay within provided context."},
        {"role":"user","content": prompt}
    ]
    out = chat(MODEL, msgs)
    print(out)
