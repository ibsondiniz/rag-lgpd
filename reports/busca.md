# Avaliação da busca

24 perguntas com o artigo certo marcado à mão. Acerto = artigo certo entre os 3 primeiros.

| Busca | Recall@3 | MRR |
|---|---|---|
| bm25 | 58% | 0.49 |
| embeddings | 88% | 0.68 |
| hibrida | 79% | 0.67 |

## Erros: bm25

- Em quais hipóteses uma empresa pode tratar dados pessoais? (esperado 7; veio 18, 44, 61)
- A LGPD vale para dados usados só para fins jornalísticos? (esperado 4; veio 65, 43, 5)
- Como deve ser dado o consentimento do titular? (esperado 8; veio 14, 5, 60)
- Quando os dados pessoais devem ser apagados? (esperado 15, 16; veio 37, 49, 46)
- Quais são as punições para quem descumpre a lei? (esperado 52; veio 5, 1, 2)
- O que a empresa deve fazer quando há vazamento de dados? (esperado 48; veio 31, 61, 54)
- Quando é permitido transferir dados pessoais para outro país? (esperado 33; veio 4, 5, 26)
- Quais são as competências da Autoridade Nacional de Proteção de Dados? (esperado 55-J, 55-A; veio 5, 55-K, 62)
- A lei se aplica a empresas de fora do Brasil? (esperado 3; veio 4, 55-G, 24)
- Em quanto tempo o controlador deve responder a um pedido de acesso aos dados? (esperado 19; veio 40, 12, 7)

## Erros: embeddings

- O que a empresa deve fazer quando há vazamento de dados? (esperado 48; veio 44, 55-J, 58-B)
- A lei se aplica a empresas de fora do Brasil? (esperado 3; veio 61, 64, 4)
- Em quanto tempo o controlador deve responder a um pedido de acesso aos dados? (esperado 19; veio 18, 41, 20)

## Erros: hibrida

- Quais são as punições para quem descumpre a lei? (esperado 52; veio 5, 3, 4)
- O que a empresa deve fazer quando há vazamento de dados? (esperado 48; veio 26, 7, 18)
- Quando é permitido transferir dados pessoais para outro país? (esperado 33; veio 4, 5, 26)
- A lei se aplica a empresas de fora do Brasil? (esperado 3; veio 4, 61, 64)
- Em quanto tempo o controlador deve responder a um pedido de acesso aos dados? (esperado 19; veio 18, 9, 7)
