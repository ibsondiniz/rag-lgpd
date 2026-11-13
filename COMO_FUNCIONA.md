# Como funciona

Resumo para estudar antes de uma entrevista técnica.

## 1. Peças

```
rag_lgpd/law.py      baixa a lei do Planalto, limpa o HTML e separa em artigos e trechos
rag_lgpd/search.py   as três buscas: BM25, embeddings e híbrida
rag_lgpd/answer.py   prompt e chamada ao Gemini ou ao Ollama
rag_lgpd/cli.py      comandos perguntar, avaliar-busca e preparar
data/lgpd.json       a lei já processada (73 artigos)
data/perguntas.jsonl 24 perguntas com o artigo certo
```

## 2. Preparar o texto

A página do Planalto mostra o texto consolidado. O que foi alterado por leis posteriores aparece **riscado**, e aparecem notas como "(Redação dada pela Lei nº 13.853, de 2019)". O `law.py`:
1. apaga o texto riscado (`<strike>`), que não vale mais;
2. tira as notas de alteração e os itens vetados;
3. começa um artigo novo a cada parágrafo que abre com "Art. N" e junta os incisos e parágrafos seguintes;
4. para na assinatura ("Brasília, ...").

## 3. Trechos (chunking)

O modelo de embeddings lê no máximo uns 128 *tokens*, cerca de 500 caracteres, e artigos longos como o 7º passam disso. Por isso a busca trabalha com **trechos**: cada parágrafo ou inciso vira um trecho.

Um inciso sozinho perde o sentido. "I - mediante o fornecimento de consentimento pelo titular" não diz que fala das *hipóteses de tratamento*. Então cada trecho começa com o início do artigo:

```
Art. 7º O tratamento de dados pessoais somente poderá ser realizado nas seguintes hipóteses: … I - mediante o fornecimento de consentimento pelo titular;
```

A busca acha trechos, mas o resultado é por **artigo** (a melhor nota entre os trechos dele). O modelo de linguagem recebe o artigo **inteiro**, para ter o contexto completo.

## 4. As três buscas

- **BM25**: a busca clássica por palavras-chave, a mesma ideia dos buscadores.
  - Palavra rara na lei (como "multa") pesa mais que palavra comum (como "dados"); isso é o IDF.
  - Repetir a palavra ajuda, mas com retorno decrescente; o parâmetro `k1` controla isso.
  - Trechos longos são penalizados; o parâmetro `b` controla isso.
  - Antes de comparar, tira acentos e palavras vazias.
- **Embeddings**: um modelo multilíngue pequeno (`paraphrase-multilingual-MiniLM-L12-v2`, via fastembed, roda em CPU) transforma cada trecho num vetor de 384 números.
  - Textos com sentido parecido ficam com vetores próximos.
  - A pergunta vira vetor também, e a busca pega os trechos com maior **similaridade de cosseno** (produto escalar de vetores normalizados).
  - Os vetores da lei são calculados uma vez e guardados em `.cache/`.
- **Híbrida**: junta as duas listas por **Reciprocal Rank Fusion**: cada artigo soma `1 / (60 + posição)` em cada lista. A fusão usa a posição e não a nota, porque a nota do BM25 e o cosseno estão em escalas diferentes e não dão para somar direto.

## 5. Métricas da busca

- **Recall@3**: em quantas perguntas o artigo certo apareceu entre os 3 primeiros. São os 3 que iriam para o LLM.
- **MRR** (*mean reciprocal rank*): média de 1/posição do primeiro acerto. Acertar em 1º vale 1; em 2º, 0,5; não achar, 0. Mede se o certo vem no topo.

Resultado: embeddings 88% e MRR 0,68; híbrida 79%; BM25 58%.

A lição: "híbrida é sempre melhor" não é regra. Aqui as perguntas usam palavras do dia a dia ("punição", "vazamento", "apagar") e a lei usa termos técnicos ("sanção", "incidente de segurança", "eliminação"). O BM25 acerta pouco e, na fusão, empurra artigos errados para cima.

A diferença entre híbrida e embeddings é de 2 perguntas em 24, pequena demais para virar regra geral. Com mais perguntas, o resultado pode mudar. Por isso se **mede** antes de escolher, e se mede de novo quando o conjunto cresce.

## 6. Geração

O prompt (`answer.py`) manda o modelo:
- usar só os artigos enviados;
- citar o artigo de cada afirmação;
- dizer que não encontrou quando os artigos não respondem;
- responder em até 6 frases, simples;
- avisar que não é orientação jurídica.

A temperatura é 0, para a resposta não variar à toa.

Isso reduz a **alucinação**, quando o modelo inventa algo que soa certo. A citação deixa qualquer pessoa conferir a resposta na lei.

## 7. Testes sem rede

- O modelo real não roda no CI. Um "embedder" de brinquedo espalha as palavras do texto em 64 posições por hash, e textos com palavras em comum ficam parecidos. Isso basta para testar a lógica da busca, do cache e da fusão.
- O parser da lei é testado com um HTML pequeno que tem texto riscado, nota de alteração, item vetado e assinatura.
- O Ollama é simulado com `monkeypatch`, e o teste confere o que seria enviado.

## 8. Perguntas prováveis

**Por que não usar um banco vetorial (Pinecone, Qdrant, pgvector)?**
São 550 trechos. Uma matriz NumPy e um produto escalar respondem em milissegundos. Banco vetorial faz sentido com milhões de trechos ou atualização constante; trocar depois só mexe na classe `Embeddings`.

**Como saber se a resposta final está certa, além da busca?**
Próximo passo:
- avaliar fidelidade: a resposta só diz o que está nos artigos?
- avaliar se as citações batem com o texto citado.

Isso pode ser feito à mão numa amostra ou com outro LLM como juiz, sempre conferindo uma parte manualmente.

**Como melhorar a busca?**
- Olhar os erros em `reports/busca.md`. Exemplo: "empresas de fora do Brasil" deveria achar o Art. 3º.
- Testar um modelo de embeddings maior, como o multilingual-e5.
- Testar trechos com mais contexto.
- Testar um *reranker*, que reordena os 20 primeiros com um modelo mais preciso.
- Medir de novo a cada mudança.

**Qual foi o papel da IA?**
Eu escolhi o tema. O Claude Code escreveu o código, os testes e as perguntas de avaliação, e conferiu no texto da lei o artigo esperado de cada uma. Revisei a lista de perguntas e li os erros da avaliação.
