
import argparse, os, glob
from app.rag import RAGIndex

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--docs", default="data/sample_docs")
    p.add_argument("--index", default="data/index.faiss")
    p.add_argument("--meta", default="data/meta.json")
    args = p.parse_args()

    docs = []
    for path in glob.glob(os.path.join(args.docs, "*.txt")):
        with open(path, "r", encoding="utf-8") as f:
            docs.append((os.path.basename(path), f.read()))

    idx = RAGIndex(index_path=args.index, meta_path=args.meta)
    idx.build(docs)
    print(f"Indexed {len(docs)} docs -> {args.index}")
