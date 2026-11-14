# Casos de falha

São exigidos pelo menos 3 casos em que o sistema errou, com a análise da causa. Os casos vêm da execução real: a coluna `hallucination_candidates` do `summary.json`, perguntas com `relevant_rank` vazio em `retrieval_per_question.csv`, ou erros observados no uso.

Copie o bloco abaixo para cada caso.

---

## Caso N: título curto

- **Data e versão:** AAAA-MM-DD, commit `abcdef0`
- **Configuração:** estratégia `...`, modo `...`, `top_k=...`, `LLM_MODEL=...`, `MIN_VECTOR_SCORE=...`
- **Pergunta:** "..."
- **Esperado:** resposta e trecho-fonte esperados, ou recusa
- **Observado:** resposta do sistema, trechos recuperados (posição e pontuação) e a `raw_answer` do log
- **Evidência:** `evidencias/avaliacao/<pasta>/generation_per_question.csv` (linha `id`), trecho de log em `evidencias/logs/`
- **Categoria:** recuperação (trecho certo fora do top-k) · chunking (resposta partida entre chunks) · geração (alucinação, citação errada, paráfrase imprecisa) · recusa indevida · outro
- **Causa provável:** ...
- **Correção aplicada ou proposta:** ...
- **Resultado depois da correção:** métrica antes → depois, com o comando usado

---
