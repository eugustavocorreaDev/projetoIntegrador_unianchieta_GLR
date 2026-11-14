# Projetos de IA na Programação: Enunciados, Calendário e Rubrica

Versão de 09/10/2026

## Visão geral

Cada grupo de 4 alunos escolhe um dos 16 temas e entrega, entre 30/11 e 02/12, um software funcional, com evidências verificáveis de funcionamento, que usa IA como componente do produto, construído com apoio de assistentes de código e avaliado com métricas, acompanhado de um trabalho de pesquisa em padrão ABNT e de uma documentação técnica.

- **Objetivo de aprendizagem:** projetar, construir e avaliar sistemas com IA com práticas reais de engenharia: testes, integração contínua, containers, métricas e análise crítica das limitações.
- **Formato:** grupos de 4 pessoas, um repositório Git por grupo e um tema por grupo, sem repetição enquanto houver temas livres.
- **Escolha do tema:** na aula de 17/10 cada grupo indica 3 opções em ordem de preferência, e o professor faz a atribuição.
- **Stack comum sugerida:** Python, FastAPI, Streamlit ou React, Git, Docker e Ollama para rodar modelos abertos localmente. Todo o projeto deve rodar a custo zero, conforme as regras de uso de IA. Cada tema indica ferramentas específicas.

Os papéis abaixo indicam quem lidera cada frente. Todos os integrantes escrevem código e precisam saber explicar qualquer parte do projeto.

| Papel | Lidera |
| --- | --- |
| Dados e Qualidade | Datasets, anotação, testes automatizados e integração contínua |
| Backend e Infraestrutura | APIs, containers, deploy e observabilidade |
| IA e Avaliação | Prompts, modelos, agentes, métricas e experimentos |
| Produto e Interface | Interface, documentação, vídeo da demo e coordenação das duas documentações |

## Calendário

As aulas vão de 17/10 a 28/11, quatro marcos de acompanhamento caem nos sábados de 24/10 a 21/11, e o envio final acontece de 30/11 a 02/12.

Linha do tempo: período de aulas de 17/10 a 28/11; marcos em 24/10, 07/11, 14/11 e 21/11; último dia de aula em 28/11; janela de envio final de 30/11 a 02/12.

O que cada marco exige:

1. **Aula inicial, 17/10:** formação dos grupos, apresentação dos temas e indicação de 3 preferências por grupo.
2. **Marco 1, 24/10:** proposta técnica de 1 a 2 páginas (problema, arquitetura, métricas de sucesso e plano), repositório criado e integração contínua mínima rodando um teste.
3. **Marco 2, 07/11:** protótipo ponta a ponta, ainda simples, com testes e Docker.
4. **Marco 3, 14/11:** MVP completo do tema, protocolo de avaliação definido (dados de teste separados, métricas e baseline) e introdução, referencial teórico e metodologia do trabalho de pesquisa redigidos.
5. **Marco 4, 21/11:** avaliação experimental concluída, funcionalidades congeladas, documentação técnica completa, pasta de evidências montada e rascunho do trabalho de pesquisa.
6. **28/11:** demonstrações curtas em aula, com feedback do professor e dos colegas.
7. **30/11 a 02/12:** envio final, conforme a seção Repositório e itens de envio.

As datas dos marcos usam os sábados do período (17/10 e 28/11 são sábados). Se a turma se reúne em outro dia, cada marco pode ser movido para a data equivalente. O sábado 31/10 fica para acompanhamento, sem entrega, e a defesa oral individual será marcada pelo professor.

## Regras de uso de IA na programação

O uso de IA é incentivado e deve ser registrado: o grupo responde por todo o código entregue, independentemente de quem ou do que o escreveu.

- **Ferramentas:** assistentes de código e modelos que o grupo possa usar sem pagar, como planos gratuitos para estudantes (por exemplo, o do GitHub Copilot, conforme as condições vigentes) ou ferramentas de código aberto com modelos locais (por exemplo, Continue ou Aider com Ollama). O README declara quais foram usadas.
- **Registro em `PROMPTS.md`:** pelo menos 10 interações relevantes, cada uma com o prompt, um resumo da resposta e o que foi aceito, corrigido ou descartado, com o motivo.
- **Testes primeiro:** código gerado por IA só entra na branch principal com teste automatizado que passa na integração contínua.
- **Revisão cruzada:** nenhum integrante aprova o próprio pull request. Todo PR tem ao menos um revisor humano do grupo.
- **Segredos:** chaves de API ficam em variáveis de ambiente e o arquivo `.env` fica no `.gitignore`. Nenhuma chave no histórico do Git.
- **Dados e LGPD:** usar apenas dados abertos, públicos ou sintéticos. Nenhum dado pessoal real em datasets, prompts ou logs.
- **Custo:** custo zero. Nenhum integrante paga por API, hospedagem ou ferramenta. Use modelos abertos locais (Ollama, llama.cpp), camadas gratuitas, notebooks em nuvem gratuitos e software de código aberto. Quem usar uma camada gratuita documenta o limite de uso e garante que o projeto também funcione com um modelo local.
- **Licenças:** bibliotecas e códigos de terceiros são permitidos com a licença citada no README. Copiar um projeto pronto sem declarar é falta de integridade acadêmica.
- **Defesa oral individual:** cada integrante explica, sem consultar a IA, um trecho do código escolhido pelo professor. A data da defesa será definida pelo professor.

## Repositório e itens de envio

O envio final, entre 30/11 e 02/12, consiste no link de um repositório que qualquer pessoa consegue executar com um comando, mais as evidências de funcionamento, o trabalho de pesquisa em padrão ABNT, a documentação técnica e o registro de uso de IA.

Estrutura mínima do repositório:

```text
README.md             problema, arquitetura, como rodar, contribuição de cada integrante
PROMPTS.md            registro de uso de IA na programação
LICENSE
docker-compose.yml    sobe o projeto com um comando
.github/workflows/    integração contínua (testes e lint)
src/                  código da aplicação
tests/                testes automatizados
eval/                 scripts, dados e resultados da avaliação experimental
evidencias/           vídeo, logs, prints e índice das evidências de funcionamento
docs/                 documentação técnica em Markdown e trabalho de pesquisa em PDF
```

| Item de envio | Requisito |
| --- | --- |
| Link do repositório | Acesso público, ou privado com o professor como colaborador, enviado até 02/12 |
| Versão avaliada | Tag `v1.0` criada até 02/12, com commits de todos os integrantes. Commits posteriores não são considerados |
| Execução reproduzível | `docker compose up` sobe o projeto sem pagamento de nenhum serviço. O README lista as variáveis necessárias, sem as chaves |
| Evidências de funcionamento | Pasta `evidencias/` com vídeo, execução verde da integração contínua, resultados da avaliação e índice, conforme a seção Evidências de funcionamento |
| Trabalho de pesquisa (ABNT) | PDF em `docs/`, de 12 a 20 páginas textuais, conforme a seção Documentação a entregar |
| Documentação técnica | Pasta `docs/` em Markdown, com o conteúdo mínimo descrito na seção Documentação a entregar |
| `PROMPTS.md` | Pelo menos 10 interações registradas, conforme as regras de uso de IA |
| Canal de envio | A definir pelo professor (por exemplo, o AVA com o link do repositório) |

## Evidências de funcionamento

Além do link do repositório, cada grupo envia provas substanciais de que construiu o sistema e de que ele funciona, de modo que o professor consiga conferir cada afirmação do trabalho de pesquisa. As evidências ficam na pasta `evidencias/` do repositório, com um `README.md` que as indexa.

| # | Evidência | O que enviar | Como o professor confere | Obrigatória |
| --- | --- | --- | --- | --- |
| 1 | Execução gravada | Vídeo de 3 a 5 minutos, com a tela inteira visível, subindo o projeto do zero com `docker compose up` e percorrendo o fluxo principal | Assiste e compara com o código da tag `v1.0` | Sim |
| 2 | Integração contínua | Link da execução verde dos testes na tag `v1.0` e uma captura dela | Abre a execução no repositório | Sim |
| 3 | Resultados da avaliação | Tabelas, gráficos e saídas brutas (CSV ou JSON) geradas pelos scripts de `eval/`, com o comando que as regera | Reexecuta o comando e compara os números | Sim |
| 4 | Logs de uma execução completa | Trechos de logs com data e hora, mostrando entradas, decisões do sistema e saídas | Confere a coerência com o vídeo e com o código | Sim |
| 5 | Capturas de tela | Pelo menos 5 situações de uso diferentes, incluindo uma falha tratada pelo sistema | Compara com o vídeo e com a execução local | Não |
| 6 | Casos de falha | Pelo menos 3 casos em que o sistema errou, com a análise da causa | Lê a análise e testa o caso, se possível | Sim |
| 7 | Histórico do Git | Commits de todos os integrantes e pull requests revisados por outro membro | Consulta o histórico no repositório | Sim |
| 8 | Índice de evidências | `evidencias/README.md` ligando cada afirmação do trabalho de pesquisa à evidência que a comprova | Usa como roteiro de conferência | Sim |

- **Gerado pelo próprio sistema:** as evidências precisam sair da execução real do projeto. Capturas editadas, números inventados ou resultados copiados de outro lugar são fraude acadêmica.
- **Resultado ruim não reprova:** um experimento que não deu certo, bem documentado e analisado, vale mais do que um resultado bom sem comprovação.
- **Conferência ao vivo:** na defesa oral, o professor pode escolher uma evidência e pedir que o grupo a reproduza na hora.
- **Sem segredos:** vídeos, logs e capturas não podem mostrar chaves de API, senhas ou dados pessoais.

## Documentação a entregar

Cada grupo entrega dois documentos com finalidades diferentes: um trabalho de pesquisa em padrão ABNT, que apresenta e avalia o projeto como um estudo, e uma documentação técnica, que permite a outra pessoa instalar, usar e reproduzir o sistema.

| Aspecto | Trabalho de pesquisa (ABNT) | Documentação técnica |
| --- | --- | --- |
| Pergunta que responde | Por que o problema importa e com que evidência a solução funciona | Como instalar, usar, manter e reproduzir o sistema |
| Leitor | Professor e banca acadêmica | Desenvolvedor ou usuário que não conhece o projeto |
| Formato | PDF em padrão ABNT | Markdown na pasta `docs/` do repositório |
| Extensão | De 12 a 20 páginas textuais | O necessário para cumprir o conteúdo mínimo |
| Rascunhos | 14/11 (introdução, referencial teórico e metodologia) e 21/11 (completo) | 21/11 (completa) |

### Trabalho de pesquisa (padrão ABNT)

- **Normas:** formatação conforme a ABNT NBR 14724 (trabalhos acadêmicos), citações pela NBR 10520, referências pela NBR 6023, resumo pela NBR 6028, sumário pela NBR 6027 e numeração progressiva das seções pela NBR 6024. Vale a versão vigente de cada norma.
- **Formatação:** papel A4, fonte tamanho 12 (Times New Roman ou Arial), espaçamento de 1,5 entre linhas, margens de 3 cm (superior e esquerda) e 2 cm (inferior e direita), citações longas com recuo de 4 cm e fonte tamanho 10.
- **Estrutura:** elementos pré-textuais (capa, folha de rosto, resumo e abstract com palavras-chave, listas de figuras e de tabelas quando houver, sumário), elementos textuais (1 Introdução, 2 Referencial teórico, 3 Metodologia, 4 Resultados e discussão, 5 Considerações finais) e elementos pós-textuais (referências e apêndices).
- **O que cada capítulo cobre:** a introdução apresenta o problema, o objetivo e a justificativa. O referencial teórico resume o estado da arte do tema. A metodologia descreve a arquitetura, os dados, as métricas e o baseline. Os resultados apresentam a avaliação experimental com tabelas e gráficos. As considerações finais tratam de limitações, riscos éticos e trabalhos futuros.
- **Fontes:** no mínimo 8 referências, das quais pelo menos 4 são artigos científicos, documentação oficial ou normas. Blogs e páginas de empresas podem complementar, mas não substituem fontes primárias.
- **Uso de IA na escrita:** permitido para revisar e organizar o texto. Toda citação e toda referência precisam ser conferidas pelo grupo na fonte original. Referência inexistente ou inventada é falta grave.
- **Ferramentas gratuitas:** LibreOffice Writer ou Google Docs com modelo ABNT, ou LaTeX com a classe abnTeX2, e Zotero para gerenciar as referências.
- **Entrega:** arquivo PDF em `docs/pesquisa-abnt.pdf`.

### Documentação técnica

A documentação técnica fica na pasta `docs/` do repositório, em Markdown, e pode ser publicada sem custo com MkDocs e GitHub Pages, de forma opcional. Conteúdo mínimo:

1. **Visão geral e arquitetura:** diagrama de componentes (Mermaid ou imagem) e fluxo de dados.
2. **Instalação e execução:** pré-requisitos, variáveis de ambiente (sem as chaves) e o comando que sobe o projeto.
3. **Decisões de arquitetura:** de 3 a 5 registros curtos, cada um com contexto, decisão e alternativas descartadas.
4. **Referência da API ou da interface:** endpoints (a documentação OpenAPI do FastAPI serve) ou comandos disponíveis.
5. **Dados e modelos:** origem, licença, tratamento e uma ficha do modelo ou do conjunto de dados.
6. **Guia de avaliação:** como reproduzir os experimentos e as métricas com um comando.
7. **Testes e integração contínua:** o que é testado, como executar e qual a cobertura.
8. **Segurança, privacidade e limitações:** riscos conhecidos, o que o sistema não faz e o tratamento de dados conforme a LGPD.
9. **Manual do usuário:** passo a passo com capturas de tela.

Critério de qualidade: uma pessoa que não participou do projeto precisa conseguir instalar, executar e reproduzir os resultados usando apenas essa documentação.

## Rubrica de avaliação

A avaliação soma 100 pontos: os critérios 1 a 6 valem para o grupo e o critério 7 é individual. Cada tema traz, ao final, critérios específicos que detalham os critérios 2 e 3.

| # | Critério | Peso | Nível máximo | Nível insuficiente |
| --- | --- | --- | --- | --- |
| 1 | Problema, arquitetura e planejamento | 10 | Problema delimitado, métricas de sucesso definidas antes do código, arquitetura documentada e plano cumprido nos marcos | Problema vago, sem métricas, marcos não cumpridos |
| 2 | Funcionamento do MVP e do desafio do tema | 20 | Fluxo principal funciona de ponta a ponta, o desafio do tema é enfrentado, não contornado, e o funcionamento é comprovado por evidências verificáveis | Funciona apenas em exemplos escolhidos a dedo ou sem evidências que permitam conferir |
| 3 | Avaliação experimental | 20 | Conjunto de teste separado, comparação com um baseline simples, análise de erros e resultados reproduzíveis | Apenas demonstração visual, sem números |
| 4 | Qualidade de engenharia | 15 | Testes automatizados, integração contínua verde, Docker, tratamento de erros, cuidados de segurança e custo zero | Sem testes, sem CI, segredos expostos ou dependência de serviço pago |
| 5 | Uso crítico da IA | 10 | `PROMPTS.md` mostra decisões, correções e descartes; o grupo sabe explicar o que a IA errou | Registro genérico ou código gerado sem revisão |
| 6 | Documentação (pesquisa ABNT e técnica) e demonstração | 15 | Pesquisa conforme a ABNT, com referências verificáveis e limitações discutidas com honestidade; documentação técnica que permite instalar e reproduzir o sistema sem ajuda; vídeo mostrando o sistema funcionando | Pesquisa fora do padrão ou com referências inventadas; documentação que não permite rodar o sistema |
| 7 | Contribuição individual e defesa oral | 10 | Commits relevantes e explicação segura de um trecho do código sem consultar a IA | Poucos commits ou incapacidade de explicar o próprio trabalho |

## Tema 1. Revisor de código com agentes

O grupo constrói um bot que revisa pull requests, comenta bugs, riscos e estilo, e só publica sugestões de correção que passam nos testes.

- **O que constroem:** uma GitHub App ou Action que lê o diff de um PR, consulta o contexto do repositório e publica comentários em linha, com severidade e patch sugerido.
- **Stack sugerida:** Python, GitHub API e Actions, tree-sitter, modelo aberto local (Ollama), pytest.
- **MVP até 14/11:** bot funcionando em um repositório de teste do grupo, comentando 20 PRs preparados com defeitos conhecidos.
- **Desafio central:** reduzir falsos positivos e executar os testes de cada patch sugerido antes de comentá-lo.
- **Critérios específicos (rubrica 2 e 3):**
  - Conjunto de 30 PRs rotulados, com e sem defeitos reais, separado do conjunto usado para ajustar os prompts.
  - Precisão e cobertura (recall) dos defeitos encontrados, comparadas com um linter tradicional como baseline.
  - Percentual de patches sugeridos que passam nos testes do projeto.
  - Análise dos 10 piores erros do bot, com a causa de cada um.

## Tema 2. Sandbox seguro para código gerado por agentes

O grupo constrói um serviço que executa código escrito por agentes de IA em ambiente isolado e prova, com ataques escritos pelo próprio grupo, que o isolamento resiste.

- **O que constroem:** uma API que recebe código em Python e JavaScript, executa em container isolado com limites de CPU, memória, rede e tempo, e devolve a saída, os erros e um registro do que o código tentou fazer.
- **Stack sugerida:** Python ou Go, Docker com gVisor ou Firecracker, FastAPI, Redis para a fila, Prometheus e Grafana.
- **MVP até 14/11:** API executando trechos nas duas linguagens com os limites aplicados, e um agente que a usa para resolver 10 problemas de programação.
- **Desafio central:** escrever ataques contra o próprio sandbox (fork bomb, enchimento de disco, tentativa de acesso à rede, leitura de arquivos do host) e demonstrar que cada um é contido sem derrubar o serviço.
- **Critérios específicos (rubrica 2 e 3):**
  - Catálogo de pelo menos 10 ataques, cada um com resultado esperado e resultado observado.
  - Tempo de inicialização do ambiente e custo por execução, medidos em pelo menos 50 execuções.
  - 20 execuções em paralelo sem vazamento de dados entre elas.
  - Falhas de contenção encontradas e documentadas com honestidade, com a correção aplicada.

## Tema 3. Plataforma de avaliação de LLMs e agentes

O grupo constrói um framework que roda baterias de testes sobre prompts, modelos e agentes e acusa regressões a cada mudança, como uma integração contínua para IA.

- **O que constroem:** uma biblioteca com linha de comando e um painel que executam casos de teste (entrada e critério de sucesso), registram os resultados por versão e comparam modelos.
- **Stack sugerida:** Python, pytest, PostgreSQL ou SQLite, Streamlit, modelos abertos via Ollama.
- **MVP até 14/11:** 100 casos de teste de uma tarefa escolhida, comparação de 3 modelos e painel com os resultados por versão.
- **Desafio central:** usar um LLM como juiz e calibrá-lo contra notas humanas, detectando quando o juiz erra.
- **Critérios específicos (rubrica 2 e 3):**
  - Amostra de pelo menos 30 casos avaliada por humanos do grupo, para comparar com as notas do juiz.
  - Concordância entre juiz e humanos medida (percentual de acordo ou kappa de Cohen).
  - Regressão demonstrada: o grupo piora um prompt de propósito e a plataforma acusa a queda.
  - Tempo e consumo de tokens por bateria de testes, e relatório dos casos em que o juiz errou.

## Tema 4. RAG de nível de produção para documentação técnica

O grupo constrói um assistente que responde dúvidas sobre uma documentação grande, sempre citando a fonte, e mede com números qual estratégia de recuperação funciona melhor.

- **O que constroem:** indexação de uma documentação de código aberto (por exemplo, a de uma biblioteca popular), busca, resposta com citações e interface web.
- **Stack sugerida:** pgvector ou Qdrant, modelos abertos de embeddings e de geração (Ollama), reranker, FastAPI, React ou Streamlit.
- **MVP até 14/11:** assistente respondendo com citação a 50 perguntas de teste, com a qualidade da recuperação medida.
- **Desafio central:** comparar estratégias de divisão do texto (chunking), busca híbrida e reranking, e tratar perguntas cuja resposta não está na documentação, caso em que o sistema deve dizer que não sabe.
- **Critérios específicos (rubrica 2 e 3):**
  - 50 perguntas com a resposta e o trecho-fonte esperados, escritos antes de ajustar o sistema.
  - Recall@k da recuperação para cada estratégia testada, em tabela comparativa.
  - Taxa de respostas fundamentadas na fonte citada e taxa de recusas corretas em perguntas sem resposta.
  - Análise dos casos de alucinação encontrados e da correção aplicada.

## Tema 5. Gateway de LLMs (custo, cache e resiliência)

O grupo constrói um proxy único para vários provedores de modelo, que reduz custo e aumenta a disponibilidade com roteamento, cache e fallback.

- **O que constroem:** um serviço com API padronizada que roteia pedidos entre modelos, com cache semântico, limites de gasto, fallback quando um provedor falha e painel de métricas.
- **Stack sugerida:** FastAPI, Redis, Prometheus e Grafana, Ollama com modelos locais de tamanhos diferentes e, opcionalmente, uma camada gratuita de API.
- **MVP até 14/11:** gateway com 3 rotas (modelo local pequeno, modelo local maior e, opcionalmente, uma camada gratuita), cache e painel com custo estimado (tokens × preços públicos de referência), latência e taxa de acerto do cache.
- **Desafio central:** um classificador que escolhe o modelo mais barato capaz de responder bem, validado com dados.
- **Critérios específicos (rubrica 2 e 3):**
  - Conjunto de 100 requisições representativas, com a qualidade esperada de cada resposta.
  - Economia de custo estimado (tokens × preços públicos de referência) comparada a enviar tudo ao modelo local maior, junto com a perda de qualidade medida.
  - Taxa de acerto do cache e ocorrência de respostas desatualizadas vindas dele.
  - Teste de falha simulada de um provedor, mostrando o fallback funcionando.

## Tema 6. Fábrica de servidores MCP

O grupo constrói servidores MCP que dão ferramentas reais a um assistente de IA e um gerador que cria novos servidores a partir de uma especificação.

- **O que constroem:** 3 servidores MCP (por exemplo, calendário, banco de dados e uma API pública), um cliente que os orquestra e um template que gera novos servidores.
- **Stack sugerida:** Python (FastMCP) ou TypeScript, Docker, FastAPI, pytest.
- **MVP até 14/11:** assistente cumprindo 10 tarefas que exigem mais de uma ferramenta, de ponta a ponta.
- **Desafio central:** autenticação, permissões por ferramenta (leitura versus escrita), confirmação humana para ações destrutivas e geração de servidores a partir de uma especificação em YAML ou OpenAPI.
- **Critérios específicos (rubrica 2 e 3):**
  - 10 tarefas de teste com taxa de sucesso medida.
  - Testes de segurança: uma ferramenta sem permissão deve ser negada, e ações destrutivas devem exigir confirmação.
  - Tempo para gerar um novo servidor com o gerador, comparado a escrevê-lo à mão.
  - Documentação de cada ferramenta exposta, com exemplos de uso.

## Tema 7. Do ticket ao pull request: agente de engenharia de software

O grupo constrói um sistema multiagente que lê uma issue, planeja a solução, escreve código e testes, roda a integração contínua e abre o pull request.

- **O que constroem:** um orquestrador com agentes especializados (planejador, programador, testador e revisor) que trabalha numa cópia isolada do repositório.
- **Stack sugerida:** LangGraph com modelo aberto local (Ollama), Docker como ambiente isolado, GitHub API, pytest.
- **MVP até 14/11:** resolver 10 issues pequenas de um repositório de teste e abrir os PRs correspondentes.
- **Desafio central:** definir quando o agente para e pede ajuda humana, evitar loops e limitar o consumo por issue.
- **Critérios específicos (rubrica 2 e 3):**
  - 20 issues com testes de aceitação escritos antes da execução do agente.
  - Taxa de resolução e consumo médio de tokens e de tempo por issue.
  - Análise das falhas por categoria (entendeu mal o pedido, quebrou outro teste, travou em loop).
  - Limite de passos e de tokens por issue, comprovado em execução.

## Tema 8. Agente de observabilidade (AIOps)

O grupo constrói um agente que lê logs, métricas e traces de uma aplicação e diagnostica a causa provável de falhas injetadas de propósito.

- **O que constroem:** uma aplicação de exemplo em microsserviços, um pipeline de telemetria e um agente que investiga alertas e produz um diagnóstico com evidências.
- **Stack sugerida:** OpenTelemetry, Prometheus, Loki ou Elasticsearch, Docker Compose, modelo aberto local (Ollama).
- **MVP até 14/11:** 10 falhas injetáveis (latência, falta de memória, dependência fora do ar, erro de configuração) e um agente que diagnostica cada uma.
- **Desafio central:** correlacionar eventos entre serviços e sugerir a remediação, executando-a apenas com aprovação humana.
- **Critérios específicos (rubrica 2 e 3):**
  - Taxa de diagnósticos corretos por tipo de falha.
  - Tempo até o diagnóstico, comparado a uma triagem manual feita pelo próprio grupo.
  - Cada diagnóstico cita a evidência usada (linhas de log ou métricas).
  - Nenhuma ação de remediação executada sem aprovação humana, comprovado em teste.

## Tema 9. Assistente de dados com text-to-SQL seguro

O grupo constrói uma interface em linguagem natural para consultar um banco real, garantindo que as consultas geradas sejam corretas, seguras e explicadas ao usuário.

- **O que constroem:** um assistente que traduz perguntas em SQL sobre dados abertos (por exemplo, dados do governo), valida a consulta, executa e mostra tabela e gráfico.
- **Stack sugerida:** PostgreSQL ou DuckDB, SQLGlot, modelo aberto local (Ollama), Streamlit.
- **MVP até 14/11:** 50 perguntas de teste com as consultas de referência e a acurácia medida.
- **Desafio central:** validar o SQL antes de executar (somente leitura, limite de linhas e de custo estimado), explicar a consulta ao usuário e perguntar quando o esquema for ambíguo.
- **Critérios específicos (rubrica 2 e 3):**
  - Acurácia por execução: o resultado da consulta gerada precisa ser igual ao da consulta de referência.
  - Tentativas de comandos destrutivos e de injeção de SQL bloqueadas, com o catálogo dos casos testados.
  - Comparação com um baseline simples, por exemplo o mesmo modelo sem receber o esquema ou sem a etapa de validação.
  - Explicação das consultas em linguagem que um usuário não técnico entenda, avaliada em amostra.

## Tema 10. Assistente multimodal em tempo real (voz e visão)

O grupo constrói um assistente que conversa por voz, enxerga a câmera ou a tela e responde dentro de um orçamento de latência medido etapa por etapa.

- **O que constroem:** uma aplicação web com captura de áudio e imagem, reconhecimento de fala, modelo com visão, síntese de voz e respostas em streaming.
- **Stack sugerida:** WebRTC ou WebSocket, modelos abertos e locais (Whisper para fala, Piper para voz, modelo com visão via Ollama), FastAPI, React.
- **MVP até 14/11:** demonstração que descreve o que a câmera vê e responde em voz, com a latência medida.
- **Desafio central:** permitir interrupção natural da fala (barge-in), transmitir em streaming de ponta a ponta e manter a latência dentro de uma meta definida pelo grupo.
- **Critérios específicos (rubrica 2 e 3):**
  - Latência por etapa (captura, reconhecimento, modelo e síntese) medida em pelo menos 30 interações.
  - Taxa de respostas corretas em uma bateria de 20 cenas ou perguntas preparadas pelo grupo.
  - Comportamento sob condições ruins (rede lenta, ruído de fundo), documentado.
  - Análise de quanto cada etapa consome da latência total e do que foi feito para reduzi-la.

## Tema 11. Memória de longo prazo para agentes

O grupo constrói uma camada de memória persistente para assistentes de IA, que decide o que lembrar, resolve contradições e permite esquecer.

- **O que constroem:** um serviço com operações de salvar, buscar, atualizar e esquecer memórias, integrado a um chatbot que mantém continuidade entre sessões.
- **Stack sugerida:** Python, FastAPI, pgvector ou Qdrant, embeddings, PostgreSQL, modelo aberto local (Ollama).
- **MVP até 14/11:** chatbot que lembra corretamente de fatos do usuário ao longo de 20 sessões simuladas.
- **Desafio central:** decidir o que merece ser lembrado, tratar fatos que mudam (o usuário mudou de cidade) e garantir o direito ao esquecimento, em linha com a LGPD.
- **Critérios específicos (rubrica 2 e 3):**
  - Benchmark próprio de conversas longas simuladas, com perguntas sobre fatos de sessões antigas.
  - Taxa de lembranças corretas e taxa de informações desatualizadas devolvidas por engano.
  - Custo em tokens por sessão, comparado a enviar todo o histórico no prompt (baseline).
  - Teste automatizado que comprova que apagar o usuário remove todas as suas memórias.

## Tema 12. Gerador de testes com mutação

O grupo constrói uma ferramenta que gera testes automaticamente e prova a qualidade deles injetando bugs propositais e medindo quantos os testes detectam.

- **O que constroem:** um pipeline que lê um projeto Python, gera testes com IA, executa a análise de mutação e usa os mutantes que sobreviveram para pedir testes melhores.
- **Stack sugerida:** Python, pytest, mutmut ou Cosmic Ray, módulo ast ou tree-sitter, modelo aberto local (Ollama), GitHub Actions.
- **MVP até 14/11:** geração de testes para 3 bibliotecas pequenas de código aberto, com o mutation score antes e depois.
- **Desafio central:** o ciclo de melhoria (mutantes sobreviventes alimentam novos testes) e a detecção de testes inúteis, que passam sempre.
- **Critérios específicos (rubrica 2 e 3):**
  - Mutation score e cobertura de linhas antes e depois, nas 3 bibliotecas.
  - Comparação com um gerador simples como baseline, por exemplo testes de propriedade automáticos.
  - Percentual de testes gerados que falham por erro do próprio teste, e não do código.
  - Tempo e consumo de tokens de geração por biblioteca.

## Tema 13. Assistente de revisão de arquitetura

O grupo constrói um agente que lê um repositório inteiro, desenha sua arquitetura e propõe refatorações priorizadas, validando as sugestões com métricas.

- **O que constroem:** um analisador que monta o grafo de dependências, gera diagramas de componentes, mede acoplamento e complexidade e propõe refatorações com justificativa.
- **Stack sugerida:** Python, tree-sitter, networkx, radon ou SonarQube, Mermaid, modelo aberto local (Ollama).
- **MVP até 14/11:** análise de 3 repositórios abertos de tamanhos diferentes, com relatório, diagrama e as 5 melhores refatorações de cada um.
- **Desafio central:** validar as sugestões em vez de confiar nelas, aplicando uma refatoração em um repositório de teste e mostrando com números se a qualidade melhorou, e lidar com repositórios que não cabem no contexto do modelo.
- **Critérios específicos (rubrica 2 e 3):**
  - Métricas antes e depois de pelo menos 2 refatorações aplicadas (complexidade, acoplamento e testes passando).
  - Fidelidade do diagrama gerado, conferida manualmente em um repositório que o grupo conhece bem.
  - Estratégia para repositórios grandes (divisão e resumo), com seus limites documentados.
  - Comparação com o resultado de uma ferramenta tradicional de análise estática como baseline.

## Tema 14. Destilação: do LLM grande ao modelo pequeno especializado

O grupo treina um modelo pequeno para executar uma tarefa específica quase tão bem quanto um LLM grande, a uma fração do custo, e mede o que se perde no caminho.

- **O que constroem:** um pipeline que usa um modelo aberto maior (por exemplo, de 7B a 8B parâmetros, rodando localmente ou em notebook gratuito) como professor para gerar e rotular dados de uma tarefa (por exemplo, classificar chamados de suporte), filtra a qualidade e treina um modelo pequeno com esses dados.
- **Stack sugerida:** Python, Hugging Face (transformers, datasets, PEFT/LoRA), modelo aberto de 1B a 3B parâmetros, MLflow ou Weights & Biases, Ollama ou llama.cpp para servir. O treino precisa de GPU, que pode ser a de um notebook em nuvem gratuito; o ambiente deve ser combinado até 24/10.
- **MVP até 14/11:** modelo pequeno treinado com pelo menos 2.000 exemplos gerados e filtrados, servido por uma API local, com tabela de qualidade, latência e custo por 1.000 requisições em comparação com o modelo maior.
- **Desafio central:** a qualidade dos dados sintéticos (duplicatas, vazamento entre treino e teste) e a análise do que a destilação perde, como casos raros e entradas fora do padrão.
- **Critérios específicos (rubrica 2 e 3):**
  - Conjunto de teste de pelo menos 200 exemplos rotulados por humanos, nunca usado no treino.
  - Qualidade, latência e custo estimado de três sistemas: modelo maior (professor), modelo pequeno sem treino específico e modelo destilado.
  - Relatório de duplicatas e de vazamento entre treino e teste.
  - Análise de erros do modelo destilado, com atenção aos casos raros.

## Tema 15. Agente de QA para interfaces

O grupo constrói um agente que testa uma aplicação web como um usuário, a partir de cenários escritos em português, e relata o que quebrou com evidências.

- **O que constroem:** um agente que recebe um cenário em linguagem natural, navega numa aplicação usando automação de navegador e um modelo com visão, executa os passos, verifica o resultado e gera um relatório com capturas de tela.
- **Stack sugerida:** Playwright, Python ou TypeScript, modelo com visão aberto e local (via Ollama), aplicação de demonstração de código aberto, GitHub Actions.
- **MVP até 14/11:** 15 cenários descritos em texto e executados automaticamente, com relatório de aprovados e reprovados e evidências visuais.
- **Desafio central:** separar falhas reais de falsos alarmes (um seletor mudou, uma animação atrasou) e fazer o agente se recuperar de mudanças de interface sem esconder bugs verdadeiros.
- **Critérios específicos (rubrica 2 e 3):**
  - 10 defeitos injetados de propósito na aplicação e a taxa de detecção do agente.
  - Taxa de falsos alarmes e estabilidade em 5 execuções repetidas do mesmo cenário.
  - Comparação com scripts Playwright escritos à mão como baseline.
  - Bônus: converter execuções bem-sucedidas em scripts determinísticos reutilizáveis na integração contínua.

## Tema 16. Agente de infraestrutura como código

O grupo constrói um agente que transforma uma descrição de infraestrutura em código Terraform ou Kubernetes e só propõe aplicá-lo depois de passar por três portões: segurança, custo e revisão humana.

- **O que constroem:** um agente que gera arquivos de infraestrutura como código a partir de texto, valida com análise estática, estima o custo mensal e apresenta o plano para aprovação.
- **Stack sugerida:** Terraform ou OpenTofu, Kubernetes (kind ou minikube), Checkov ou tfsec, Infracost, LocalStack, modelo aberto local (Ollama).
- **MVP até 14/11:** 5 arquiteturas geradas, validadas e aplicadas em ambiente local simulado, com relatório de achados de segurança e de custo.
- **Desafio central:** nunca aplicar nada sem os três portões e tratar pedidos "armadilha" (bucket público, porta aberta ao mundo, credencial dentro do código), que o agente deve recusar ou corrigir.
- **Critérios específicos (rubrica 2 e 3):**
  - 10 pedidos armadilha e a taxa de bloqueio ou correção pelo agente.
  - Estimativa de custo comparada com a da ferramenta de referência.
  - Correção funcional: a infraestrutura gerada sobe e passa em testes de verificação.
  - Explicação em linguagem simples de cada mudança proposta.
