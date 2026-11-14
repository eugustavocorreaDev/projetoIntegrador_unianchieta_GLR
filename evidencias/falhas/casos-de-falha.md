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

## Caso 1: o reranker piorava a ordem dos trechos (configuração padrão)

- **Data e versão:** 2026-11-14, antes do commit da interação 7 do `PROMPTS.md`
- **Configuração:** estratégias `fixed` e `recursive`, modo `hybrid_rerank` (então padrão), `top_k=5`, `EMBED_MODEL=nomic-embed-text`, reranker `ms-marco-MultiBERT-L-12`
- **Pergunta:** as 50 perguntas com resposta do conjunto de teste
- **Esperado:** o trecho esperado entre os 5 primeiros, como acontece sem o reranker
- **Observado:** Recall@5 de 58% (`fixed`) e 60% (`recursive`), contra 98% e 96% da busca `hybrid` sem reranking. Na interface, a pergunta "COMO FAZ UM OVO FRITO?" mostrou trechos sem relação com nota de rerank 0,998
- **Evidência:** aba Validação / `POST /validation/retrieval` (tabela completa na ADR 002 de `docs/arquitetura.md`). **Pendente:** salvar a saída oficial de `eval/run_eval.py` em `evidencias/avaliacao/`
- **Categoria:** recuperação (trecho certo fora do top-k)
- **Causa provável:** o modelo do reranker reordena mal trechos técnicos em português. A hipótese de truncamento (`max_length` de 128 tokens) foi testada com 128, 256 e 512 tokens e descartada: o Recall@5 ficou entre 56% e 70% em todos os casos
- **Correção aplicada:** o modo padrão passou a ser `hybrid` (`RETRIEVAL_MODE`, `docker-compose.yml` e a barra lateral da interface). O `hybrid_rerank` continua disponível para a comparação
- **Resultado depois da correção:** Recall@5 da configuração padrão de 60% → 96% (`recursive`). Comando: aba Validação, "Rodar as 50 perguntas com resposta"

---

## Caso 2: recusa indevida de uma pergunta com print

- **Data e versão:** 2026-11-14, antes do commit da interação 7 do `PROMPTS.md`
- **Configuração:** estratégia `recursive`, modo `hybrid`, `top_k=5`, `LLM_MODEL=qwen2.5:3b`, `VISION_MODEL=qwen2.5vl:3b`
- **Pergunta:** "Por que aparece este erro e como resolvo?" com o print de um terminal mostrando `RuntimeError: Form data requires "python-multipart" to be installed.`
- **Esperado:** resposta citando `cabecalhos-cookies-formularios.md` ("Para trabalhar com formulários é necessário instalar o pacote `python-multipart`...")
- **Observado:** o modelo de visão transcreveu o print sem erros, e a busca trouxe o trecho certo na 1ª posição. Mesmo assim, o LLM respondeu "Não encontrei essa informação na documentação indexada." (`refusal_reason=llm_refusal`). Tempos: leitura da imagem 69 s, busca 6 s, geração 52 s (CPU, com outro processo pesado rodando)
- **Evidência:** evento `ask.completed` em `logs/app.log`, com `image_text` e `decision: refused:llm_refusal`
- **Categoria:** recusa indevida
- **Causa provável:** o prompt é rígido (recusar quando a resposta não estiver nos trechos), e o modelo de 3B não ligou a mensagem de erro em inglês ao trecho em português, que fala de "formulários"
- **Correção proposta:** testar um prompt que peça para relacionar mensagens de erro aos trechos, ou um modelo maior (ex.: `qwen2.5:7b`), e medir a taxa de falsas recusas na aba Validação antes e depois
- **Resultado depois da correção:** pendente

---
