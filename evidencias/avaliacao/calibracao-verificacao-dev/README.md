# Calibração da verificação de citações (conjunto de desenvolvimento)

Executada em 15/11/2026 depois da avaliação oficial, para decidir se a regra de cobertura
(`MIN_CITATION_COVERAGE=0.5`) devia ser afrouxada. Usa **só** `eval/datasets/perguntas_dev.json`
(12 perguntas com resposta e 6 sem). O conjunto de teste não participou da decisão.

1. `coletar_dev.py` gera as respostas reais do `qwen2.5:3b` (`recursive + hybrid`, top-5) e as
   grava, com os trechos enviados ao modelo, em `dev_respostas.json`, que está versionado.
2. `calibrar_grounding.py` reaplica seis variações da regra às mesmas respostas e a 4 respostas
   forjadas (conhecimento externo com uma citação "de fachada"), que precisam ser barradas.
   Reproduza com `python evidencias/avaliacao/calibracao-verificacao-dev/calibrar_grounding.py`,
   que regrava `resultado.json` sem chamar o modelo.

| Regra | Fundamentadas | Recusas corretas | Forjadas aceitas |
| --- | --- | --- | --- |
| cobertura ≥ 0,50 (**mantida**) | 9/12 | 6/6 | 1/4 |
| cobertura ≥ 0,25 | 9/12 | 6/6 | 1/4 |
| cobertura ≥ 0,00 | 10/12 | 6/6 | 1/4 |
| ≥ 0,50 + conferir frases sem citação no contexto | 9/12 | 6/6 | 3/4 |
| ≥ 0,25 + conferir frases sem citação no contexto | 10/12 | 6/6 | 3/4 |
| ≥ 0,00 + conferir frases sem citação no contexto | 11/12 | 6/6 | 3/4 |

**Decisão:** manter a regra. Conferir as frases sem citação contra todo o contexto aceita
respostas forjadas, porque palavras do domínio ("API", "senhas") sempre aparecem em algum
trecho. Baixar só a cobertura ganha 1 pergunta em 12, pouco para afrouxar a proteção.

A resposta forjada que a regra atual aceita é "O FastAPI usa bcrypt com 12 rodadas por padrão
[1]": "FastAPI" e "padrão" estão no trecho citado, o que dá 50% de sustentação lexical.
