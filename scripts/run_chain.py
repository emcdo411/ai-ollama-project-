
import argparse, json
from app.chain import analyze, plan, generate

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--task", required=True)
    p.add_argument("--input", default="")
    p.add_argument("--format", default="markdown")
    args = p.parse_args()

    a = analyze(args.task, context=args.input)
    print("\n=== ANALYSIS ===\n", a)

    pl = plan(a, output_format=args.format)
    print("\n=== PLAN (JSON) ===\n", pl)

    g = generate(pl, style_guide="Use short, clear sentences. Prefer lists.")
    print("\n=== OUTPUT ===\n", g)
