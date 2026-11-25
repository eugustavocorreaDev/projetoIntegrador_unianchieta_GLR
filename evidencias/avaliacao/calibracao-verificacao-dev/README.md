# Calibração da verificação de citações (conjunto de desenvolvimento)

Usa **só** `eval/datasets/perguntas_dev.json` (versão 1.1.0: 30 perguntas com resposta e 12 sem). O
conjunto de teste não participou de nenhuma decisão daqui.

1. `coletar_dev.py` gera as respostas reais do `qwen2.5:3b` (`recursive + hybrid`, top-5) e as grava,
   com os trechos enviados ao modelo, em `dev_respostas.json`, que está versionado (coleta de 24/11/2026).
2. `calibrar_grounding.py` aplica o `ground_answer` real a essas respostas, com variações do limiar de
   atribuição, e a 15 respostas forjadas que precisam ser barradas. Reproduza sem chamar o modelo:
   `python evidencias/avaliacao/calibracao-verificacao-dev/calibrar_grounding.py` (regrava `resultado.json`).

## Antes e depois, nas mesmas 42 respostas reais

| Dev | Original (`3207b6b`) | Atual |
| --- | --- | --- |
| Respondidas | 24/30 | 26/30 |
| Fundamentadas (trecho-ouro dentro do trecho citado) | 22/30 | **24/30** |
| Fundamentadas entre as respondidas | 91,7% | 92,3% |
| Recusas corretas (perguntas sem resposta) | 12/12 | 12/12 |
| Falsas recusas | d05, d07, d11, d21, d23, d30 | d21, d23, d24, d30 |

Com 30 perguntas, a diferença de 2 respostas **não é estatisticamente significativa**; ela mostra que
os mecanismos funcionam nos casos analisados, não que a taxa subiu por esse valor.

## O que cada mecanismo faz

| Mudança | Caso | Efeito medido |
| --- | --- | --- |
| Termos críticos (número, identificador, qualificador, negação) | u07 (alucinação) | barra as 7 forjadas de valor/escopo inventado, com e sem `[n]` |
| `[n]` sozinho na linha pertence à frase anterior | d11 | recuperada |
| Reparo: troca o `[n]` errado por outro trecho **do mesmo documento** | d05, d07 | recuperadas |
| Atribuição: frase sem citação ganha o `[n]` de um único trecho que a sustenta (≥ 0,6) | continuações sem `[n]` | recupera respostas com cobertura baixa |
| Frase atribuída não conta na maioria das reprovações | forjada "Django [1]. Ele gera a API..." | evita que uma frase boa dilua uma citada e reprovada |

Os limiares de atribuição 0,5, 0,6, 0,7 e 0,8 dão o **mesmo** resultado (24/30, 2/15 forjadas aceitas);
fica 0,6, no meio da faixa estável.

## O que continua sem solução (limite da checagem lexical)

- **Forjadas ainda aceitas (2 de 15):** "Todos os modelos Pydantic são imutáveis [2]" e a versão com
  negação ("`frozen=True` **não** torna as instâncias imutáveis [2]"). O trecho contém "todos" e "não"
  em outro contexto, e a checagem de termos críticos olha o trecho inteiro.
- **Resposta errada que reaproveita palavras do trecho (d16):** "Como evito reler o `.env`?" respondida
  com `env_file` do Compose (o certo é `lru_cache`), citando um trecho que fala de `.env`. Passa porque a
  checagem é lexical. Também foi observada ao vivo na API. Só uma verificação semântica (NLI ou LLM
  juiz) resolve, com custo de latência em CPU.
- **d21 e d30:** o próprio modelo recusa (no d21, nem o trecho certo foi recuperado). A verificação não
  tem como corrigir.
- **d24:** o modelo citou `http://127.0.0.1:8000/openapi.json`, endereço que não está no trecho
  (só `/openapi.json`). A recusa é coerente com a regra.

## Ressalva de rigor

Os termos críticos nasceram do caso u07, que está no conjunto de teste congelado. As decisões de
limiar usam só o dev, mas o resultado no conjunto de teste deixa de ser uma estimativa limpa para esse
caso.

## Histórico: dev de 18 perguntas (antes do passo 2 e da ampliação)

Regra antiga (cobertura ≥ 0,50): 9/12 fundamentadas, 6/6 recusas, 5 de 8 forjadas aceitas. Com termos
críticos: 8/12, 6/6, 1 de 8. O d07 foi a pergunta perdida (citação com o número errado), que o reparo
de citação passou a recuperar.
