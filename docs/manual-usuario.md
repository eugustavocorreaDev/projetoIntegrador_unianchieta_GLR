# Manual do usuário

> As capturas de tela são geradas pela execução real do sistema e ficam em `evidencias/prints/`. Substitua cada referência abaixo pela imagem correspondente quando ela for capturada.

## 1. Abrir a interface

Com o projeto no ar (`docker compose up --build`), acesse <http://localhost:8501>.

A barra lateral mostra o **Status**: API, Qdrant, Ollama e quantos chunks existem em cada coleção. Tudo verde indica que o sistema está pronto.

*Captura: `evidencias/prints/01-tela-inicial.png`*

A interface tem três abas:

- **💬 Perguntar:** para fazer perguntas;
- **📚 Documentos:** para ver o que o assistente sabe;
- **✅ Validação:** para medir se ele acerta.

As opções da barra lateral valem para as três.

## 2. Fazer uma pergunta (aba Perguntar)

1. Digite a pergunta no campo **"Escreva sua pergunta e tecle Enter"** e tecle **Enter**. Outra opção é clicar num dos botões em **Experimente**, que já enviam a pergunta.
2. Aguarde: em CPU, a resposta leva de 10 s a 60 s.
3. Acima da resposta aparece **"Você perguntou: ..."**, para conferir o que foi enviado.

**Perguntar com um print:**
1. Arraste a imagem para **"Anexar um print"** (PNG, JPG ou WEBP, até 5 MB) ou clique para escolher o arquivo.
2. Escreva a pergunta e tecle Enter. Para perguntar só sobre a imagem, use **"Perguntar só sobre a imagem"**.

O modelo de visão lê o texto e o código do print. O que ele leu aparece em **"Texto lido do print"**. A resposta continua vindo só da documentação, com citações. A leitura de prints precisa do Ollama com o modelo `qwen2.5vl:3b` e fica desativada no Modo de Visualização.

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

Na recusa, a lista de baixo passa a se chamar **"Trechos mais próximos encontrados"**. A busca sempre devolve os trechos mais parecidos, mesmo quando nenhum responde. Por isso, uma pontuação alta de relevância ali não quer dizer que a resposta esteja no trecho.

*Captura: `evidencias/prints/04-recusa.png`*

## 5. Comparar estratégias

Na barra lateral:

- **Estratégia de chunking:** recursiva por seções ou tamanho fixo (baseline).
- **Recuperação:** híbrida + reranking, híbrida, só vetorial ou só BM25.
- **Top-k:** quantos trechos vão para o modelo.
- **Só recuperar (sem LLM):** mostra apenas os trechos encontrados, em segundos, sem gerar resposta. Útil para comparar estratégias rapidamente.

*Captura: `evidencias/prints/05-comparacao-estrategias.png`*

## 6. Ver a base de conhecimento (aba Documentos)

Mostra **tudo o que o assistente sabe**: os arquivos de `data/raw_docs/`. Em cima ficam os totais de documentos, seções e chunks por estratégia. Embaixo, uma tabela com uma linha por arquivo, que pode ser filtrada pelo nome. Ao abrir um documento:

- **Texto:** o conteúdo do arquivo, como foi indexado;
- **Chunks:** os pedaços em que ele foi dividido na estratégia da barra lateral (troque a estratégia para comparar);
- **Perguntas de teste:** as perguntas do conjunto de teste que têm a resposta neste arquivo, com o botão **"Testar a recuperação destas perguntas"**.

*Captura: `evidencias/prints/08-documentos.png`*

## 7. Validar o sistema (aba Validação)

Roda o conjunto de teste (`eval/datasets/perguntas_teste.json`) contra a API, com a configuração da barra lateral:

1. **Recuperação (rápido, sem LLM):** confere, nas 50 perguntas com resposta, se o trecho esperado chegou entre os top-k. Mostra o Recall@k, os acertos, o MRR e uma tabela com ✅/❌ por pergunta.
2. **Resposta e recusa (usa o LLM):** pergunta ao modelo de verdade. As perguntas com resposta precisam ser respondidas citando o documento esperado, e as perguntas sem resposta precisam ser recusadas. Mostra a taxa de respostas fundamentadas e de recusas corretas.

As duas partes têm **Baixar CSV**. Os números do Modo de Visualização não valem como resultado. Os números oficiais do trabalho vêm de `eval/run_eval.py` (ver [avaliacao.md](avaliacao.md)).

*Captura: `evidencias/prints/09-validacao.png`*

## 8. Modo de Visualização (Mock)

Se a máquina não tem Ollama, o `scripts/run_local.ps1` sobe o sistema no Modo de Visualização. Uma faixa azul discreta, **Modo de Visualização (Mock)**, aparece no topo e explica como ativar o LLM real. As respostas passam a ser tópicos com as frases dos trechos recuperados, a seção de origem e a citação de cada uma, além do exemplo de código do trecho principal, em vez de texto gerado por um LLM. O cartão da resposta mostra "Trechos organizados · modo de visualização". A busca, as fontes e a recusa funcionam do mesmo jeito.

*Captura: `evidencias/prints/07-modo-demonstracao.png`*

## 9. Falhas tratadas

Se a API ou o Ollama estiverem fora do ar, a interface mostra uma mensagem de erro em vermelho em vez de travar, e o status da barra lateral fica vermelho. O **Histórico da sessão** lista as perguntas feitas, com ✅ para as respondidas e 🛡️ para as recusadas.

*Captura: `evidencias/prints/06-falha-api.png`*
