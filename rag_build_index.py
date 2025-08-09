# rag_build_index.py
import os
import glob
import pickle
from pathlib import Path

import numpy as np

# If FAISS import fails on Windows, skip RAG (as noted in README)
import faiss  # pip install faiss-cpu
from sentence_transformers import SentenceTransformer

DATA_DIR = Path("./data")
OUT_DIR = Path("./rag")
OUT_DIR.mkdir(parents=True, exist_ok=True)

INDEX_PATH = OUT_DIR / "index.faiss"
META_PATH = OUT_DIR / "meta.pkl"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12
    return vectors / norms

def main():
    files = sorted(glob.glob(str(DATA_DIR / "*.txt")))
    if not files:
        raise SystemExit("No .txt files found in ./data. Add a few docs first.")

    texts, ids = [], []
    for i, fp in enumerate(files):
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read().strip()
        if not txt:
            continue
        texts.append(txt)
        ids.append(os.path.basename(fp))

    if not texts:
        raise SystemExit("All files were empty—nothing to index.")

    print(f"Loaded {len(texts)} docs from ./data")

    model = SentenceTransformer(MODEL_NAME)
    emb = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    emb = emb.astype("float32")
    emb = l2_normalize(emb)  # use cosine via inner product + normalized vectors

    d = emb.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(emb)

    faiss.write_index(index, str(INDEX_PATH))
    with open(META_PATH, "wb") as f:
        pickle.dump(
            {
                "ids": ids,
                "model_name": MODEL_NAME,
                "num_docs": len(ids),
            },
            f,
        )

    print(f"Wrote index to {INDEX_PATH} and metadata to {META_PATH}")

if __name__ == "__main__":
    main()
