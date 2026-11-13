"""Generation step: the LLM sees only the retrieved articles and must cite them."""

import json
import os
import time
import urllib.request

PROMPT = """Você tira dúvidas sobre a LGPD (Lei 13.709/2018) usando somente os artigos enviados.
Regras:
- Cite o artigo de cada afirmação, no formato (Art. 7º) ou (Art. 7º, I).
- Se os artigos enviados não respondem a pergunta, diga que não encontrou a resposta nesses artigos. Não use outro conhecimento.
- Responda em português, em até 6 frases, em linguagem simples.
- Termine com: "Isto não é orientação jurídica."""


def context(arts, articles):
    """Full text of the retrieved articles, in ranking order."""
    by_id = {a["art"]: a["text"] for a in articles}
    return "\n\n".join(by_id[a] for a in arts)


def user_message(question, ctx):
    return f"Artigos da LGPD:\n\n{ctx}\n\nPergunta: {question}"


def gemini(question, ctx, model=None):
    from google import genai
    from google.genai import errors, types

    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("Defina GEMINI_API_KEY (chave grátis no Google AI Studio) ou use --provider nenhum.")
    client = genai.Client()
    model = model or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    config = types.GenerateContentConfig(system_instruction=PROMPT, temperature=0,
                                         thinking_config=types.ThinkingConfig(thinking_level="low"),
                                         http_options=types.HttpOptions(timeout=90_000))
    for attempt in range(4):
        try:
            return client.models.generate_content(model=model, contents=user_message(question, ctx), config=config).text
        except errors.APIError as e:
            if e.code not in (429, 503) or attempt == 3:  # rate limit or "high demand": worth waiting
                raise
            time.sleep(30 * (attempt + 1))


def ollama(question, ctx, model=None):
    body = {"model": model or os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "stream": False, "options": {"temperature": 0},
            "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": user_message(question, ctx)}]}
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/chat"
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["message"]["content"]
