
import os
import json
import faiss
import numpy as np
from typing import List, Tuple
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

class RAGIndex:
    def __init__(self, index_path: str = "data/index.faiss", meta_path: str = "data/meta.json"):
        self.index_path = index_path
        self.meta_path = meta_path
        self.model = SentenceTransformer(EMBED_MODEL)
        self.index = None
        self.meta: List[dict] = []

    def _encode(self, texts: List[str]) -> np.ndarray:
        emb = self.model.encode(texts, normalize_embeddings=True)
        return np.array(emb, dtype="float32")

    def build(self, docs: List[Tuple[str,str]]):
        # docs: list of (doc_id, text)
        vectors = self._encode([t for _, t in docs])
        dim = vectors.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(vectors)
        self.meta = [{"id": did, "text": txt} for (did, txt) in docs]
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, ensure_ascii=False, indent=2)

    def load(self):
        self.index = faiss.read_index(self.index_path)
        with open(self.meta_path, "r", encoding="utf-8") as f:
            self.meta = json.load(f)

    def query(self, question: str, k: int = 3):
        if self.index is None or not self.meta:
            self.load()
        qv = self._encode([question])
        scores, idxs = self.index.search(qv, k)  # inner product, higher is better
        idxs = idxs[0].tolist()
        out = []
        for i in idxs:
            if i < 0: 
                continue
            out.append(self.meta[i])
        return out
