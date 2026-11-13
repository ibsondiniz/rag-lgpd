"""Offline tests: a tiny fake embedder replaces the real model, and no LLM is called."""

import io
import json
import zlib

import numpy as np
import pytest

from rag_lgpd import answer, law
from rag_lgpd.cli import evaluate, main
from rag_lgpd.search import BM25, Embeddings, Hybrid, tokens

PAGE = """<html><body>
<p>CAPÍTULO I</p>
<p>Art. 1º Esta Lei dispõe sobre o tratamento de dados pessoais.</p>
<p>Art. 2º <strike>Texto antigo revogado.</strike> A disciplina da proteção de dados tem como fundamentos: (Redação dada pela Lei nº 13.853, de 2019)</p>
<p>I - o respeito à privacidade;</p>
<p>II - (VETADO).</p>
<p>Art. 3º (VETADO).</p>
<p>Art. 4º Esta Lei entra em vigor na data de sua publicação. Ver também o Art. 1º desta Lei.</p>
<p>Brasília, 14 de agosto de 2018.</p>
<p>Art. 99. Texto depois da assinatura não entra.</p>
</body></html>"""

ARTICLES = [
    {"art": "5", "text": "Art. 5º Para os fins desta Lei, considera-se:\nII - dado pessoal sensível: origem racial, saúde, vida sexual"},
    {"art": "18", "text": "Art. 18. O titular dos dados tem direito a obter do controlador:\nII - acesso aos dados;\nVI - eliminação dos dados"},
    {"art": "52", "text": "Art. 52. Os agentes de tratamento ficam sujeitos às sanções administrativas:\nII - multa simples de até 2%"},
]
CHUNKS = law.chunks(ARTICLES)


def fake_embed(texts):
    """Bag of words hashed into 64 dimensions: similar wording, similar vector."""
    out = np.zeros((len(texts), 64))
    for i, t in enumerate(texts):
        for w in tokens(t):
            out[i, zlib.crc32(w.encode()) % 64] += 1
    return out + 1e-6


def test_parse_drops_struck_text_notes_vetoes_and_signature():
    arts = law.parse(PAGE)
    assert [a["art"] for a in arts] == ["1", "2", "4"]
    two = arts[1]["text"]
    assert "revogado" not in two and "Redação dada" not in two and "VETADO" not in two
    assert two.endswith("I - o respeito à privacidade;")


def test_chunks_carry_the_article_start():
    assert CHUNKS[1] == {"art": "5", "text": "Art. 5º Para os fins desta Lei, considera-se: … II - dado pessoal sensível: origem racial, saúde, vida sexual"}
    assert len(CHUNKS) == 3 + 4


def test_bm25_finds_the_article_with_the_words():
    assert BM25(CHUNKS).search("quais as sanções e a multa", 1) == ["52"]
    assert BM25(CHUNKS).search("direito de acesso aos meus dados", 1) == ["18"]


def test_embeddings_and_hybrid(tmp_path, monkeypatch):
    monkeypatch.setattr("rag_lgpd.search.CACHE", tmp_path)
    emb = Embeddings(CHUNKS, fake_embed)
    assert emb.search("dado pessoal sensível saúde", 1) == ["5"]
    assert list(tmp_path.glob("emb-*.npy"))  # vectors cached for the next run
    hyb = Hybrid(BM25(CHUNKS), emb)
    assert hyb.search("multa sanções", 1) == ["52"]


def test_evaluate_recall_and_mrr():
    class Fixed:
        def search(self, q, k):
            return ["18", "52", "5"]

    rows = evaluate({"fixa": Fixed()}, [{"q": "a", "arts": ["18"]}, {"q": "b", "arts": ["5"]}, {"q": "c", "arts": ["99"]}], k=2)
    assert rows["fixa"]["recall"] == pytest.approx(1 / 3)
    assert rows["fixa"]["mrr"] == pytest.approx((1 + 1 / 3) / 3)
    assert len(rows["fixa"]["misses"]) == 2


def test_prompt_gets_only_retrieved_articles_in_order():
    ctx = answer.context(["52", "5"], ARTICLES)
    assert ctx.index("Art. 52") < ctx.index("Art. 5º") and "Art. 18" not in ctx
    assert answer.user_message("Qual a multa?", ctx).endswith("Pergunta: Qual a multa?")


def test_ollama_call(monkeypatch):
    sent = {}

    def fake_urlopen(req, timeout):
        sent.update(json.loads(req.data))
        return io.BytesIO(json.dumps({"message": {"content": "Multa de até 2% (Art. 52)."}}).encode())

    monkeypatch.setattr(answer.urllib.request, "urlopen", fake_urlopen)
    assert answer.ollama("Qual a multa?", "Art. 52 ...", "modelo-teste") == "Multa de até 2% (Art. 52)."
    assert sent["messages"][0]["content"] == answer.PROMPT and sent["model"] == "modelo-teste"


def test_gemini_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="GEMINI_API_KEY"):
        answer.gemini("x", "y")


def test_cli_with_real_law_and_keyword_search(capsys):
    main(["perguntar", "Quais são as sanções administrativas e a multa?", "--busca", "bm25", "--provider", "nenhum", "-k", "2"])
    out = capsys.readouterr().out
    assert "Art. 52" in out.splitlines()[-1]  # the sanctions article is among the two retrieved
    assert "multa simples, de até 2% (dois por cento)" in out
