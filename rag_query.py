# rag_query.py
import argparse
import pickle
from pathlib import Path

import numpy as np
import faiss  # pip install faiss-cpu
from sentence_transformers import SentenceTransformer

from llm import ask  # uses local Ollama

OUT_DIR = Path("./rag")
INDEX_PATH = OUT_DIR / "index.faiss"
META_PATH = OUT_DIR / "meta.pkl"

def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12
    return vectors / norms

def load_index():
    if not INDEX_PATH.exists() or not META_PATH.exists():
        raise SystemExit("Missing index. Run: python rag_build_index.py")

    index = faiss.read_index(str(INDEX_PATH))
    meta = pickle.loads(META_PATH.read_bytes())
    return index, meta

def retrieve(query: str, k: int, model_name: str, index, ids):
    embedder = SentenceTransformer(model_name)
    q = embedder.encode([query], convert_to_numpy=True).astype("float32")
    q = l2_normalize(q)
    scores, idxs = index.search(q, k)
    idxs = idxs[0].tolist()
    scores = scores[0].tolist()
    hits = [(ids[i], scores[j]) for j, i in enumerate(idxs) if i != -1]
    return hits

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question", type=str, help="Your question")
    parser.add_argument("--k", type=int, default=4, help="Top-K docs")
    parser.add_argument("--model", type=str, default="mistral", help="Ollama model name")
    parser.add_argument("--num_predict", type=int, default=256)
    args = parser.parse_args()

    index, meta = load_index()
    ids = meta["ids"]
    model_name = meta["model_name"]

    hits = retrieve(args.question, args.k, model_name, index, ids)

    if not hits:
        print("No results.")
        return

    # Build a simple context string referencing doc IDs only; keep it compact.
    ctx_lines = [f"[{rank+1}] {doc_id}" for rank, (doc_id, _score) in enumerate(hits)]
    context_header = "CANDIDATE SOURCES:\n" + "\n".join(ctx_lines)

    system = (
        "You are a careful assistant. Answer ONLY using information grounded in the provided sources. "
        "If the sources are insufficient, say so briefly.\n"
        "When you state a fact, include bracketed citations like [1], [2] that refer to the filenames shown below."
    )

    user = (
        f"{context_header}\n\n"
        f"QUESTION: {args.question}\n\n"
        "Answer concisely in 4–6 sentences."
    )

    out = ask(
        prompt=user,
        model=args.model,
        num_predict=args.num_predict,
        temperature=0.2,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )

    print(out)

if __name__ == "__main__":
    main()
