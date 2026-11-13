"""Usage:
  rag-lgpd perguntar "Quais direitos o titular tem?" [--busca hibrida|embeddings|bm25] [--provider gemini|ollama|nenhum] [-k 4]
  rag-lgpd avaliar-busca [--saida reports/busca.md]   recall and MRR of the three searches on data/perguntas.jsonl
  rag-lgpd preparar                                   downloads the law again from planalto.gov.br
"""

import argparse
import json
import sys
from pathlib import Path

from rag_lgpd import answer, law
from rag_lgpd.search import BM25, Embeddings, Hybrid

QUESTIONS = Path(__file__).resolve().parent.parent / "data" / "perguntas.jsonl"


def engines(chunks, embed=None):
    bm25, emb = BM25(chunks), Embeddings(chunks, embed)
    return {"bm25": bm25, "embeddings": emb, "hibrida": Hybrid(bm25, emb)}


def evaluate(engs, questions, k=3):
    """recall@k: share of questions with a right article in the top k. MRR: mean of 1/rank of the first right article."""
    rows = {}
    for name, e in engs.items():
        hits, rr, misses = 0, 0.0, []
        for q in questions:
            got = e.search(q["q"], 10)
            rank = next((i + 1 for i, a in enumerate(got) if a in q["arts"]), None)
            hits += bool(rank and rank <= k)
            rr += 1 / rank if rank else 0
            if not rank or rank > k:
                misses.append((q["q"], q["arts"], got[:k]))
        rows[name] = {"recall": hits / len(questions), "mrr": rr / len(questions), "misses": misses}
    return rows


def report(rows, n, k):
    out = ["# Avaliação da busca", "", f"{n} perguntas com o artigo certo marcado à mão. Acerto = artigo certo entre os {k} primeiros.", "",
           f"| Busca | Recall@{k} | MRR |", "|---|---|---|"]
    out += [f"| {name} | {r['recall'] * 100:.0f}% | {r['mrr']:.2f} |" for name, r in rows.items()]
    for name, r in rows.items():
        out += ["", f"## Erros: {name}", ""]
        out += [f"- {q} (esperado {', '.join(exp)}; veio {', '.join(got)})" for q, exp, got in r["misses"]] or ["- nenhum"]
    return "\n".join(out) + "\n"


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="rag-lgpd", description="Perguntas sobre a LGPD com citação do artigo.")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("perguntar")
    a.add_argument("pergunta")
    a.add_argument("--busca", default="embeddings", choices=["embeddings", "hibrida", "bm25"], help="padrão: a que mediu melhor")
    a.add_argument("--provider", default="gemini", choices=["gemini", "ollama", "nenhum"])
    a.add_argument("--modelo")
    a.add_argument("-k", type=int, default=4, help="quantos artigos mandar ao modelo")
    e = sub.add_parser("avaliar-busca")
    e.add_argument("--saida")
    e.add_argument("-k", type=int, default=3)
    sub.add_parser("preparar")
    args = p.parse_args(argv)

    if args.cmd == "preparar":
        arts = law.parse(law.download())
        law.save(arts)
        print(f"{len(arts)} artigos salvos em {law.DATA}")
        return

    articles = law.load()
    chunks = law.chunks(articles)
    if args.cmd == "avaliar-busca":
        questions = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
        rows = evaluate(engines(chunks), questions, args.k)
        for name, r in rows.items():
            print(f"{name:<11} recall@{args.k} {r['recall'] * 100:.0f}%  MRR {r['mrr']:.2f}")
        if args.saida:
            Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
            Path(args.saida).write_text(report(rows, len(questions), args.k), encoding="utf-8")
        return

    engine = BM25(chunks) if args.busca == "bm25" else engines(chunks)[args.busca]
    arts = engine.search(args.pergunta, args.k)
    ctx = answer.context(arts, articles)
    if args.provider == "nenhum":
        print(ctx)
    else:
        print(getattr(answer, args.provider)(args.pergunta, ctx, args.modelo))
    print("\nArtigos consultados: " + ", ".join(f"Art. {a}" for a in arts))
