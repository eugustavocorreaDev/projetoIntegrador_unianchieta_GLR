# Manual do usuário

> As capturas de tela são geradas pela execução real do sistema e ficam em `evidencias/prints/`. Substitua cada referência abaixo pela imagem correspondente quando ela for capturada.

## 1. Abrir a interface

Com o projeto no ar (`docker compose up --build`), acesse <http://localhost:8501>.

A barra lateral mostra o **Status**: API, Qdrant, Ollama e quantos chunks existem em cada coleção. Tudo verde indica que o sistema está pronto.

*Captura: `evidencias/prints/01-tela-inicial.png`*

## 2. Fazer uma pergunta

1. Digite a pergunta na caixa **Pergunta** ou clique num dos botões em **Experimente**.
2. Clique em **Perguntar**.
3. Aguarde: em CPU, a resposta leva de 10 s a 60 s.

*Captura: `evidencias/prints/02-pergunta.png`*

## 3. Ler a resposta e as fontes

- O cartão **Resposta fundamentada**, com borda azul, traz a resposta. Os números em selo azul (por exemplo, **1**) indicam de qual trecho veio cada afirmação.
- Abaixo, os chips mostram a latência total, o tempo de recuperação e de geração, o modo de busca usado e quantos trechos foram enviados ao modelo.
- Em **Fontes citadas**, cada cartão expansível mostra o arquivo de origem, a seção, a pontuação de relevância (com barra) e o trecho exato recuperado.
- Em **Todos os trechos enviados ao modelo**, aparecem todos os trechos do contexto, inclusive os não citados.

*Captura: `evidencias/prints/03-resposta-com-citacoes.png`*

## 4. Quando o sistema recusa

Se a documentação não cobre a pergunta (por exemplo, "Como configurar GraphQL no FastAPI?"), aparece o cartão amarelo **Recusa anti-alucinação acionada** com a mensagem "Não encontrei essa informação na documentação indexada." e o motivo:

| Motivo exibido | O que significa |
| --- | --- |
| Nenhum trecho recuperado | A busca não achou nada parecido |
| Abaixo do limite de relevância | Os trechos achados são pouco parecidos com a pergunta |
| O modelo não encontrou a resposta | O modelo leu os trechos e recusou |
| Resposta sem citação descartada | O modelo tentou responder sem citar fonte, e a resposta foi bloqueada |

*Captura: `evidencias/prints/04-recusa.png`*

## 5. Comparar estratégias

Na barra lateral:

- **Estratégia de chunking:** recursiva por seções ou tamanho fixo (baseline).
- **Recuperação:** híbrida + reranking, híbrida, só vetorial ou só BM25.
- **Top-k:** quantos trechos vão para o modelo.
- **Só recuperar (sem LLM):** mostra apenas os trechos encontrados, em segundos, sem gerar resposta. Útil para comparar estratégias rapidamente.

*Captura: `evidencias/prints/05-comparacao-estrategias.png`*

## 6. Modo de Visualização (Mock)

Se a máquina não tem Ollama, o `scripts/run_local.ps1` sobe o sistema no Modo de Visualização. Uma faixa azul discreta, **Modo de Visualização (Mock)**, aparece no topo e explica como ativar o LLM real. As respostas passam a ser tópicos com as frases dos trechos recuperados, a seção de origem e a citação de cada uma, além do exemplo de código do trecho principal, em vez de texto gerado por um LLM. O cartão da resposta mostra "Trechos organizados · modo de visualização". A busca, as fontes e a recusa funcionam do mesmo jeito.

*Captura: `evidencias/prints/07-modo-demonstracao.png`*

## 7. Falhas tratadas

Se a API ou o Ollama estiverem fora do ar, a interface mostra uma mensagem de erro em vermelho em vez de travar, e o status da barra lateral fica vermelho. O **Histórico da sessão** lista as perguntas feitas, com ✅ para as respondidas e 🛡️ para as recusadas.

*Captura: `evidencias/prints/06-falha-api.png`*
