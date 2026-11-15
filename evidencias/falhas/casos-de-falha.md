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
- **Correção tentada (15/11/2026):** uma regra no prompt pedindo para tratar mensagens de erro em inglês como parte da pergunta. Medida com o mesmo erro enviado como texto: o modelo **continuou recusando**, e a regra foi retirada para não alterar o prompt sem ganho medido
- **Correção proposta:** um modelo maior (ex.: `qwen2.5:7b`), medido na aba Validação
- **Resultado depois da correção:** sem melhora com o modelo de 3B

---

## Caso 3: alucinação do valor padrão de workers (u07)

- **Data e versão:** 2026-11-15, avaliação oficial (`evidencias/avaliacao/20261115-172143-principal-recursive-hybrid/`)
- **Configuração:** `recursive`, `hybrid`, `top_k=5`, `LLM_MODEL=qwen2.5:3b`, `MIN_CITATION_COVERAGE=0.5`, `MIN_SUPPORT_RATIO=0.3`
- **Pergunta:** "Quantos workers o fastapi run usa por padrão?" (armadilha: a opção `--workers` é documentada, o valor padrão não)
- **Esperado:** recusa
- **Observado:** "O comando `fastapi run` usa por padrão um único processo. [1]", citando `implantacao.md`. O trecho diz que, **num cluster com Kubernetes**, o recomendado é "rodar um único processo por container". O modelo transformou uma recomendação para um caso específico em valor padrão. É a única entrada de `hallucination_candidates` no `summary.json`
- **Evidência:** `generation_per_question.csv` (linha `u07`) e o evento `ask.completed` correspondente em `evidencias/logs/execucao-completa.jsonl`
- **Categoria:** geração (alucinação com citação)
- **Causa provável:** a verificação é lexical. A frase alucinada reaproveita palavras do trecho citado ("único", "processo"), então passa na sustentação mínima de 30%
- **Correção tentada (15/11/2026):** uma regra no prompt dizendo que valor padrão só pode ser afirmado se o trecho o disser explicitamente. Medida antes e depois com a mesma pergunta: o modelo de 3B **manteve a alucinação**, e a regra foi retirada
- **Correção proposta:** verificação semântica (um LLM maior como juiz, ou NLI entre a frase e o trecho) ou um modelo de geração maior. Ambas custam latência em CPU e ficam como trabalho futuro
- **Resultado depois da correção:** não corrigido; a taxa de recusas corretas oficial é 92,9% (13/14) por causa deste caso

---

## Caso 4: falsas recusas por baixa cobertura de citações

- **Data e versão:** 2026-11-15, avaliação oficial (mesma pasta do caso 3)
- **Configuração:** a mesma do caso 3
- **Pergunta:** 16 das 50 perguntas com resposta (q02, q07, q09, q10, q11, q14, q15, q21, q23, q24, q26, q29, q30, q34, q39, q42)
- **Esperado:** resposta citando o documento esperado
- **Observado:** o modelo respondeu com conteúdo dos trechos, mas citou `[n]` em poucas frases. A cobertura ficou entre 0% e 33%, abaixo do mínimo de 50%, e a verificação descartou a resposta (`ungrounded_answer`). **Nenhuma** frase foi reprovada por falta de sustentação. Em 3 casos o modelo não usou nenhuma citação; em 1 (q02), parou a resposta antes de escrever o comando. É a maior causa da taxa de falsas recusas de 38%
- **Evidência:** `generation_per_question.csv` (coluna `citation_coverage`) e `evidencias/avaliacao/calibracao-verificacao-dev/`
- **Categoria:** recusa indevida (verificação rígida demais para um modelo de 3B)
- **Causa provável:** o modelo de 3B não segue a instrução "cite toda afirmação"
- **Correção avaliada:** seis variações da regra, calibradas **só no conjunto de desenvolvimento**, com 4 respostas forjadas de controle. Afrouxar a cobertura ganha no máximo 1 de 12 perguntas; conferir as frases sem citação contra todo o contexto passa a aceitar 3 de 4 respostas forjadas
- **Decisão:** manter a regra atual. A troca entre cobertura de respostas (62% respondidas) e segurança (93,5% fundamentadas entre as respondidas) é deliberada
- **Resultado depois da correção:** sem mudança, por decisão baseada em dados

---

## Caso 5: resposta correta descartada pelo formato "explicação + código" (corrigido)

- **Data e versão:** 2026-11-15, antes da avaliação oficial
- **Pergunta:** q22, "Como substituo uma dependência real por uma versão de teste?"
- **Observado:** o modelo citou `[1]` na linha de introdução do código ("... use o dicionário `app.dependency_overrides` [1]:"). A verificação ignorava toda linha terminada em ":", a cobertura ia a 0 e a resposta correta era descartada
- **Categoria:** recusa indevida (bug da verificação)
- **Correção aplicada:** `generation/grounding.py` passou a contar as introduções que trazem citação, e as que não trazem continuam ignoradas. Testes de regressão: `test_cited_intro_before_code_counts_as_claim` e `test_bare_intro_without_citation_is_still_ignored`
- **Resultado depois da correção:** q22 respondida citando `testes.md` na medição ao vivo (antes: `ungrounded_answer`)

---
