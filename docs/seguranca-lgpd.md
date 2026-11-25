# Segurança, privacidade e limitações

## Segredos

- O projeto não usa nenhuma chave de API: todos os modelos rodam localmente.
- `.env` está no `.gitignore` e a CI falha se algum `.env` for versionado. Só o `.env.example`, sem segredos, vai para o repositório.
- `GET /config` expõe apenas parâmetros não sensíveis (há teste para isso).

## Dados e LGPD

- **Corpus e datasets:** só documentação aberta (MIT) e texto original sem dados pessoais.
- **Perguntas dos usuários:** podem conter dados pessoais se alguém os digitar. A interface avisa para não fazer isso. Os logs gravam a pergunta **truncada em 200 caracteres** e **não gravam IP**: o access log do Uvicorn fica desligado (`--no-access-log`).
- **Retenção:** os logs ficam em `logs/app.log` (rotação de 5 MB, 3 arquivos) só na máquina de quem executa. Nada é enviado a terceiros.
- **Evidências:** antes de copiar logs ou capturas para `evidencias/`, confira que não há dados pessoais, senhas ou chaves.

## Superfície de ataque

| Risco | Tratamento |
| --- | --- |
| Entrada gigante | `question` limitada a 1000 caracteres e `top_k` a 20 (validação Pydantic, 422) |
| Reindexação por terceiros | `POST /ingest` pode ser desligado com `ENABLE_INGEST_ENDPOINT=false`; a API não tem autenticação e foi feita para uso local |
| Injeção de HTML pela resposta do modelo | A interface escapa todo texto do LLM e dos trechos antes de renderizar (há teste) |
| Injeção de prompt vinda dos documentos | Mitigada: só documentos do próprio repositório são indexados, e o prompt manda usar os trechos só como fonte. Não é eliminada |
| Download com path traversal | `scripts/download_fastapi_docs.py` ignora caminhos absolutos e com `..` |
| Containers | A API e a interface rodam com usuário sem privilégios (UID 1000) |

## Limitações conhecidas (o que o sistema não faz)

- Não responde sobre nada fora da documentação indexada; recusa de propósito.
- A verificação de citações exige cobertura mínima e sustentação **lexical**: cada afirmação citada precisa compartilhar termos com o trecho que cita. Ela também exige que números, identificadores de código e qualificadores de escopo ("padrão", "sempre", "apenas") da afirmação existam no trecho citado, o que barra valores inventados com as palavras do trecho. Ela barra afirmações sem relação com os trechos e valores inventados, mas uma paráfrase errada que reutiliza os mesmos termos e qualificadores passa. A taxa é estimada na análise manual de erros.
- A recusa estrita gera falsos negativos (resposta correta sem citação é descartada), medidos por `false_refusal_rate`.
- `MIN_VECTOR_SCORE` vem desligado e depende de calibração por corpus e modelo de embeddings.
- O BM25 roda em memória: adequado até dezenas de milhares de chunks, não para corpora muito maiores.
- Em CPU, cada resposta leva de 10 s a 60 s. Não há streaming de tokens.
- O modo demonstração (`LLM_MODE=mock`) não entende a pergunta: só compara termos. Ele existe para desenvolver sem Ollama e é sinalizado na interface.
- A interface carrega a fonte Plus Jakarta Sans do Google Fonts: o navegador de quem abre a página faz uma requisição ao Google. Sem internet, os títulos usam Arial.
- A API não tem autenticação nem limite de requisições: não deve ser exposta à internet.
- Documentos da documentação oficial do FastAPI perdem os exemplos de código incluídos por diretiva.
