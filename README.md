# Perguntas sobre a LGPD com citação do artigo

> Retrieval-augmented question answering over Brazil's data protection law (LGPD): local multilingual embeddings, measured retrieval, and answers that cite the article.

[![CI](https://github.com/ibsondiniz/rag-lgpd/actions/workflows/ci.yml/badge.svg)](https://github.com/ibsondiniz/rag-lgpd/actions/workflows/ci.yml)

Você pergunta em português comum ("Quais são as punições para quem descumpre a lei?") e recebe uma resposta curta que cita o artigo de onde veio, por exemplo "(Art. 52, II)".

O modelo de linguagem só vê os artigos que a busca encontrou e é instruído a não usar outro conhecimento. Isso é RAG (*retrieval-augmented generation*):
1. **busca** os artigos certos;
2. **gera** a resposta a partir deles.

O texto da lei vem da página oficial do Planalto, já consolidado com as alterações de 2019. Textos de lei são de domínio público.

## Exemplo real

```
$ rag-lgpd perguntar "Quais são as punições para quem descumpre a lei?"
Quem descumpre a lei fica sujeito a diversas sanções administrativas aplicáveis pela autoridade nacional
(Art. 52, caput). As punições incluem advertência com prazo para correção, multa simples de até 2% do
faturamento limitada a R$ 50.000.000,00 por infração, e multa diária (Art. 52, I, II e III). Também podem
ser aplicadas a publicização da infração, o bloqueio ou a eliminação dos dados pessoais afetados
(Art. 52, IV, V e VI). Além disso, a lei prevê a suspensão parcial do banco de dados, a suspensão do
exercício da atividade de tratamento e a proibição parcial ou total dessas atividades (Art. 52, X, XI e XII).

Isto não é orientação jurídica.

Artigos consultados: Art. 54, Art. 52, Art. 55-J
```

A pergunta diz "punições", mas a lei diz "sanções", e mesmo assim a busca achou o Art. 52. Os incisos citados conferem com o texto da lei; os incisos VII a IX foram vetados, por isso a resposta pula do VI para o X. Resposta gerada pelo `gemini-3.5-flash` no plano grátis.

## A busca foi medida

Antes de pôr um LLM na frente, a busca foi avaliada com 24 perguntas, cada uma com o artigo certo marcado à mão:

| Busca | Acerto entre os 3 primeiros | MRR |
|---|---|---|
| BM25 (palavras-chave) | 58% | 0,49 |
| **Embeddings locais** | **88%** | **0,68** |
| Híbrida (as duas juntas) | 79% | 0,67 |

O BM25 erra quando a pergunta usa palavras diferentes da lei: "punições" contra "sanções", "vazamento" contra "incidente de segurança". Os embeddings comparam o sentido, não a palavra.

Juntar as duas buscas não ajudou neste conjunto: 19 acertos contra 21 dos embeddings sozinhos. Com só 24 perguntas, essa diferença é pequena. Mesmo assim, a busca padrão ficou a de embeddings, que mediu melhor. Os erros de cada busca estão em [reports/busca.md](reports/busca.md).

## Como rodar

```bash
uv sync
uv run rag-lgpd avaliar-busca                        # baixa o modelo de embeddings (~220 MB) na primeira vez
uv run rag-lgpd perguntar "Posso revogar o consentimento?" --provider nenhum   # só mostra os artigos achados
cp .env.example .env                                 # cole a chave grátis do Gemini
uv run --env-file .env rag-lgpd perguntar "Quais são as punições para quem descumpre a lei?"
```

O modelo que gera a resposta é plugável: `--provider gemini` (padrão: `gemini-3.5-flash`, plano grátis), `--provider ollama` (modelo local) ou `--provider nenhum`.

Com Docker, o modelo de embeddings já vem dentro da imagem:

```bash
docker build -t rag-lgpd .
docker run --rm rag-lgpd
docker run --rm --env-file .env rag-lgpd perguntar "O que é dado pessoal sensível?"
```

## Testes

```bash
uv run pytest
uv run ruff check .
```

Os testes não baixam o modelo nem chamam LLM. Um "embedder" de brinquedo (palavras espalhadas em 64 posições) faz o papel do modelo real, e o Ollama é simulado. O GitHub Actions roda tudo a cada push.

## Como funciona

[COMO_FUNCIONA.md](COMO_FUNCIONA.md) explica a divisão da lei em trechos, as três buscas, as métricas e o prompt.

## Autoria

Feito por Ibson Diniz com auxílio do Claude Code, a IA de programação da Anthropic. As perguntas de avaliação e o artigo esperado de cada uma estão em [data/perguntas.jsonl](data/perguntas.jsonl); cada artigo esperado foi conferido no texto da lei. As respostas não são orientação jurídica.

Licença [MIT](LICENSE).
