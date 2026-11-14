"""Interface de demonstração e validação. Rode com: streamlit run src/ui/app.py

A interface só conversa com a API por HTTP (API_URL); não importa nada do backend.
Abas: Perguntar (Enter envia; aceita print), Documentos (a base que o assistente conhece)
e Validação (o conjunto de teste rodado ao vivo contra a API).
"""

from __future__ import annotations

import base64
import csv
import html
import io
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

import httpx
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from styles import CSS  # noqa: E402

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = httpx.Timeout(float(os.getenv("UI_TIMEOUT_S", "300")), connect=5.0)
MAX_IMAGE_MB = 5

STRATEGIES = {"recursive": "Recursiva por seções", "fixed": "Tamanho fixo (baseline)"}
MODES = {  # o primeiro é o padrão da barra lateral (ADR 002 em docs/arquitetura.md)
    "hybrid": "Híbrida (vetorial + BM25) · recomendada",
    "hybrid_rerank": "Híbrida + reranking",
    "vector": "Só vetorial",
    "bm25": "Só BM25",
}
REFUSAL_REASONS = {
    "no_context": "Nenhum trecho da documentação foi recuperado para essa pergunta.",
    "low_relevance": "Os trechos recuperados ficaram abaixo do limite de relevância configurado.",
    "llm_refusal": "O modelo leu os trechos recuperados e não encontrou a resposta neles.",
    "ungrounded_answer": (
        "O modelo respondeu sem citar fontes suficientes, ou fez afirmações que não aparecem "
        "nos trechos citados. A resposta foi descartada para evitar uma possível alucinação."
    ),
}
EXAMPLES = [
    "Como sobrescrever uma dependência durante os testes?",
    "Qual a diferença entre parâmetros de caminho e de consulta?",
    "Como rodar uma tarefa depois de enviar a resposta?",
    "Como configurar GraphQL no FastAPI?",
]
BATCH = 10  # perguntas por chamada na validação de recuperação

st.set_page_config(page_title="Assistente de documentação", page_icon="📘", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


# --- Acesso à API -------------------------------------------------------------


@st.cache_data(ttl=10, show_spinner=False)
def fetch_health() -> dict | None:
    try:
        return httpx.get(f"{API_URL}/health", timeout=5).json()
    except (httpx.HTTPError, ValueError):
        return None


def _error_detail(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = response.text
    return f"Erro {response.status_code}: {detail}"


def api_get(path: str, params: dict | None = None) -> tuple[object | None, str | None]:
    try:
        response = httpx.get(f"{API_URL}{path}", params=params, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        return None, f"Não foi possível falar com a API em {API_URL}: {exc}"
    if response.status_code >= 400:
        return None, _error_detail(response)
    return response.json(), None


def call_api(path: str, payload: dict) -> tuple[dict | None, str | None]:
    try:
        response = httpx.post(f"{API_URL}{path}", json=payload, timeout=TIMEOUT)
    except httpx.TimeoutException:
        return None, (
            "A API demorou demais para responder. Em CPU, a primeira chamada ao modelo "
            "pode levar alguns minutos."
        )
    except httpx.HTTPError as exc:
        return None, f"Não foi possível falar com a API em {API_URL}: {exc}"
    if response.status_code >= 400:
        return None, _error_detail(response)
    return response.json(), None


@st.cache_data(ttl=60, show_spinner=False)
def fetch_documents() -> tuple[object | None, str | None]:
    return api_get("/documents")


@st.cache_data(ttl=60, show_spinner=False)
def fetch_document(source: str, strategy: str) -> tuple[object | None, str | None]:
    return api_get(f"/documents/{quote(source)}", {"strategy": strategy})


@st.cache_data(ttl=60, show_spinner=False)
def fetch_questions() -> tuple[object | None, str | None]:
    return api_get("/validation/questions")


# --- Renderização ----------------------------------------------------------------


_BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)$")
_NUMBERED_RE = re.compile(r"^\s*\d+[.)]\s+(.*)$")


def _inline(text: str) -> str:
    """Escapa o texto e aplica código inline, negrito e selos de citação [n]."""
    safe = html.escape(text)
    safe = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", safe)
    safe = re.sub(r"\*\*([^*\n]+)\*\*", r"<b>\1</b>", safe)
    return re.sub(r"\[(\d{1,3})\]", r'<span class="cite">\1</span>', safe)


def _render_prose(text: str) -> str:
    """Parágrafos, listas com "-" e listas numeradas, linha a linha."""
    out: list[str] = []
    open_list: str | None = None
    for line in text.split("\n"):
        bullet, numbered = _BULLET_RE.match(line), _NUMBERED_RE.match(line)
        kind = "ul" if bullet else "ol" if numbered else None
        if kind != open_list and open_list:
            out.append(f"</{open_list}>")
            open_list = None
        if kind:
            if open_list is None:
                out.append(f"<{kind}>")
                open_list = kind
            out.append(f"<li>{_inline((bullet or numbered).group(1))}</li>")
        elif line.strip():
            out.append(f"<p>{_inline(line.strip())}</p>")
    if open_list:
        out.append(f"</{open_list}>")
    return "".join(out)


def render_answer_html(text: str) -> str:
    """Formata a resposta (do LLM ou do mock) com segurança: todo texto é escapado."""
    parts = re.split(r"```(?:[\w-]+)?\n(.*?)```", text, flags=re.S)
    rendered = []
    for i, part in enumerate(parts):
        if i % 2:  # bloco de código: preserva as quebras de linha
            rendered.append(f"<pre>{html.escape(part)}</pre>")
        else:
            rendered.append(_render_prose(part))
    return "".join(rendered)


def chips(items: list[tuple[str, str, str]]) -> str:
    """items: (rótulo, valor, classe extra)."""
    spans = "".join(
        f'<span class="chip {cls}">{html.escape(label)} <b>{html.escape(value)}</b></span>'
        for label, value, cls in items
    )
    return f'<div class="rag-chips">{spans}</div>'


def relevance(item: dict) -> tuple[str, float | None]:
    """Pontuação exibida e fração 0..1 para a barra (só para escalas limitadas)."""
    if item.get("rerank_score") is not None:
        return f"rerank {item['rerank_score']:.3f}", max(0.0, min(1.0, item["rerank_score"]))
    if item.get("vector_score") is not None:
        return f"cosseno {item['vector_score']:.3f}", max(0.0, min(1.0, item["vector_score"]))
    if item.get("bm25_score") is not None:
        return f"BM25 {item['bm25_score']:.2f}", None
    return f"score {item['score']:.4f}", None


def render_source(title: str, item: dict, expanded: bool = False) -> None:
    score_label, fraction = relevance(item)
    with st.expander(f"{title} · {score_label}", expanded=expanded):
        stages = " → ".join(item.get("stages") or [])
        meta = (
            '<div class="rag-source-meta">'
            f'<span class="file">📄 data/raw_docs/{html.escape(item["source"])}</span>'
            f'<span class="section">› {html.escape(item["section"])}</span></div>'
        )
        bar = (
            f'<div class="scorebar"><span style="width:{fraction * 100:.0f}%"></span></div>'
            if fraction is not None
            else ""
        )
        extra = [("relevância", score_label, "")]
        if stages:
            extra.append(("etapas", stages, ""))
        st.markdown(
            meta
            + bar
            + chips(extra)
            + f'<div class="rag-excerpt">{html.escape(item["text"])}</div>',
            unsafe_allow_html=True,
        )


def render_result(data: dict, mode: str, only_search: bool, mock: bool = False) -> None:
    retrieved = data.get("retrieved", [])
    by_id = {r["chunk_id"]: r for r in retrieved}
    refused = not only_search and data["refused"]

    if not only_search:
        if refused:
            reason = REFUSAL_REASONS.get(data["refusal_reason"], data["refusal_reason"])
            st.markdown(
                '<div class="rag-card refusal"><div class="label">🛡️ Recusa anti-alucinação acionada'
                f'</div><div class="body"><b>{html.escape(data["answer"])}</b></div>'
                f'<div class="reason">{html.escape(reason)}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            answer_label = (
                "Trechos organizados · modo de visualização" if mock else "Resposta fundamentada"
            )
            st.markdown(
                f'<div class="rag-card answer"><div class="label">{answer_label}</div>'
                f'<div class="body">{render_answer_html(data["answer"])}</div></div>',
                unsafe_allow_html=True,
            )

    timings = data.get("timings_ms") or {}
    status = []
    if not only_search:
        status.append(("status", "recusada", "warn") if refused else ("status", "respondida", "ok"))
    status += [
        ("latência", f"{data['latency_ms']:.0f} ms", ""),
        *[(k, f"{v:.0f} ms", "") for k, v in timings.items()],
        ("modo", MODES.get(data["mode_effective"], data["mode_effective"]), ""),
        ("trechos", str(len(retrieved)), ""),
    ]
    st.markdown(chips(status), unsafe_allow_html=True)
    if data.get("mode_effective") != mode:
        st.info("O reranker não estava disponível; a resposta usou a busca híbrida sem reranking.")

    if not only_search and data.get("citations"):
        st.markdown("### Fontes citadas")
        for citation in data["citations"]:
            item = by_id.get(citation["chunk_id"]) or {
                **citation,
                "text": citation["excerpt"],
                "score": 0.0,
                "stages": [],
            }
            render_source(f"[{citation['id']}] {citation['source']}", item)

    if refused:
        st.markdown("### Trechos mais próximos encontrados")
        st.caption(
            "A busca sempre devolve os trechos mais parecidos, mesmo quando nenhum responde à "
            "pergunta. Uma pontuação alta de relevância não significa que a resposta esteja ali: "
            "quem decide é o modelo, e a verificação de citações confirma."
        )
    else:
        title = "Trechos recuperados" if only_search else "Todos os trechos enviados ao modelo"
        st.markdown(f"### {title}")
    if not retrieved:
        st.caption("Nenhum trecho recuperado.")
    for item in retrieved:
        render_source(f"#{item['rank']} {item['source']} › {item['section']}", item)


def to_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return buffer.getvalue()


def rate(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator} ({numerator / denominator:.0%})" if denominator else "—"


# --- Barra lateral ---------------------------------------------------------------

with st.sidebar:
    st.markdown("## Configuração")
    strategy = st.selectbox("Estratégia de chunking", list(STRATEGIES), format_func=STRATEGIES.get)
    mode = st.selectbox("Recuperação", list(MODES), format_func=MODES.get)
    top_k = st.slider("Trechos enviados ao modelo (top-k)", 1, 10, 5)
    only_search = st.toggle("Só recuperar (sem LLM)", value=False)
    st.caption("Valem para as três abas.")

    st.markdown("## Status")
    health = fetch_health()
    if health is None:
        st.markdown(
            f'<p class="status-line">🔴 API indisponível em {API_URL}</p>', unsafe_allow_html=True
        )
    else:
        icon = "🟢" if health["status"] == "ok" else "🟠"
        lines = [
            f"{icon} API: <b>{health['status']}</b>",
            f"{'🟢' if health['qdrant'] else '🔴'} Qdrant",
            f"{'🟢' if health['ollama'] else '🔴'} Ollama",
        ]
        for name, count in (health.get("collections") or {}).items():
            lines.append(
                f"📚 {STRATEGIES.get(name, name)}: {count if count is not None else '?'}" " chunks"
            )
        st.markdown(
            "".join(f'<p class="status-line">{line}</p>' for line in lines), unsafe_allow_html=True
        )

    history = st.session_state.get("history", [])
    if history:
        st.markdown("## Histórico da sessão")
        for entry in reversed(history[-8:]):
            st.markdown(f'<p class="hist">{entry}</p>', unsafe_allow_html=True)


# --- Cabeçalho ---------------------------------------------------------------------

st.markdown(
    '<div class="rag-hero"><h1>Assistente de documentação<span class="dot">.</span></h1>'
    "<p>Responde apenas com base na documentação indexada, cita a fonte de cada afirmação "
    "e avisa quando a informação não está lá. Não digite nem envie dados pessoais.</p></div>",
    unsafe_allow_html=True,
)
st.write("")

MOCK_MODE = bool(health and health.get("llm_mode") == "mock")
if MOCK_MODE:
    st.markdown(
        '<div class="rag-demo">🧪 <b>Modo de Visualização (Mock)</b>: as respostas organizam os '
        "trechos recuperados, com as citações, mas não são geradas por IA. Para ativar o LLM real, "
        "rode <code>scripts\\instalar.ps1</code> (instala o Ollama e baixa os modelos), feche a "
        "janela da API e execute <code>scripts\\run_local.ps1</code> de novo.</div>",
        unsafe_allow_html=True,
    )

tab_ask, tab_docs, tab_validation = st.tabs(["💬 Perguntar", "📚 Documentos", "✅ Validação"])


# --- Aba 1: Perguntar --------------------------------------------------------------


def _use_example(text: str) -> None:
    st.session_state["pending_question"] = text


def _ask_about_image() -> None:
    st.session_state["pending_question"] = ""
    st.session_state["image_only"] = True


with tab_ask:
    st.caption("Experimente")
    for column, text in zip(st.columns(len(EXAMPLES)), EXAMPLES, strict=True):
        column.button(text, on_click=_use_example, args=(text,), use_container_width=True)

    upload_key = f"image_{st.session_state.get('upload_round', 0)}"
    image = st.file_uploader(
        f"Anexar um print (opcional): PNG, JPG ou WEBP, até {MAX_IMAGE_MB} MB",
        type=["png", "jpg", "jpeg", "webp"],
        key=upload_key,
        help="O modelo de visão lê o texto e o código do print; a resposta continua vindo "
        "só da documentação, com citações.",
    )
    if MOCK_MODE:
        st.caption(
            "A leitura de prints precisa do Ollama e fica desativada no Modo de Visualização."
        )
    if image is not None:
        st.image(image.getvalue(), caption=image.name, width=320)
        st.button("Perguntar só sobre a imagem", on_click=_ask_about_image)

    typed = st.chat_input("Escreva sua pergunta e tecle Enter", max_chars=1000)
    pending = st.session_state.pop("pending_question", None)
    image_only = st.session_state.pop("image_only", False)
    question = typed if typed is not None else pending

    if question is not None:
        question = question.strip()
        image_bytes = image.getvalue() if image is not None else None
        if image_bytes and len(image_bytes) > MAX_IMAGE_MB * 1024 * 1024:
            st.warning(f"O print passa de {MAX_IMAGE_MB} MB. Recorte a imagem e envie de novo.")
        elif len(question) < 3 and not (image_only and image_bytes):
            st.warning("Escreva uma pergunta com pelo menos 3 caracteres.")
        else:
            payload = {"question": question, "strategy": strategy, "mode": mode, "top_k": top_k}
            if image_bytes:
                payload["image_base64"] = base64.b64encode(image_bytes).decode("ascii")
            label = "Buscando na documentação…" if only_search else "Buscando e gerando a resposta…"
            if image_bytes:
                label = "Lendo o print e " + label[0].lower() + label[1:]
            with st.spinner(label):
                data, error = call_api("/search" if only_search else "/ask", payload)
            st.session_state["last"] = {
                "data": data,
                "error": error,
                "mode": mode,
                "only": only_search,
                "question": question,
                "image_name": image.name if image is not None else None,
            }
            if data and not only_search:
                mark = "🛡️" if data["refused"] else "✅"
                shown = question[:90] or f"[imagem] {image.name}"
                st.session_state.setdefault("history", []).append(f"{mark} {html.escape(shown)}")
            if data and image is not None:
                st.session_state["upload_round"] = st.session_state.get("upload_round", 0) + 1
            st.rerun()

    last = st.session_state.get("last")
    if last:
        asked = html.escape(last.get("question") or "(só a imagem)")
        attachment = (
            f' <span class="chip">📎 {html.escape(last["image_name"])}</span>'
            if last.get("image_name")
            else ""
        )
        st.markdown(
            f'<div class="rag-asked">Você perguntou: <b>{asked}</b>{attachment}</div>',
            unsafe_allow_html=True,
        )
        if last["error"]:
            st.error(last["error"])
        elif last["data"]:
            if last["data"].get("image_text"):
                with st.expander("Texto lido do print (entrou na pergunta)"):
                    st.code(last["data"]["image_text"], language=None)
            render_result(last["data"], last["mode"], last["only"], mock=MOCK_MODE)


# --- Aba 2: Documentos --------------------------------------------------------------

with tab_docs:
    st.markdown("### A base de conhecimento")
    st.caption(
        "É só isto que o assistente sabe. Os arquivos ficam em `data/raw_docs/` no repositório; "
        "perguntas sobre qualquer outro assunto são recusadas de propósito."
    )
    docs, docs_error = fetch_documents()
    questions, questions_error = fetch_questions()
    by_source: dict[str, list[dict]] = {}
    for q in questions or []:
        if q.get("expected_source"):
            by_source.setdefault(q["expected_source"], []).append(q)

    if docs_error:
        st.error(docs_error)
    elif docs:
        cols = st.columns(4)
        cols[0].metric("Documentos", len(docs))
        cols[1].metric("Seções", sum(d["sections"] for d in docs))
        cols[2].metric("Chunks (fixo)", sum(d["chunks"].get("fixed", 0) for d in docs))
        cols[3].metric("Chunks (recursivo)", sum(d["chunks"].get("recursive", 0) for d in docs))

        filtro = st.text_input("Filtrar por arquivo ou título", placeholder="ex.: pytest")
        needle = filtro.strip().lower()
        visible = [
            d
            for d in docs
            if not needle or needle in d["source"].lower() or needle in d["title"].lower()
        ]
        st.dataframe(
            [
                {
                    "arquivo": d["source"],
                    "título": d["title"],
                    "seções": d["sections"],
                    "caracteres": d["chars"],
                    "chunks (fixo)": d["chunks"].get("fixed", 0),
                    "chunks (recursivo)": d["chunks"].get("recursive", 0),
                    "perguntas de teste": len(by_source.get(d["source"], [])),
                }
                for d in visible
            ],
            hide_index=True,
            use_container_width=True,
        )

        if visible:
            titles = {d["source"]: f"{d['title']} ({d['source']})" for d in visible}
            source = st.selectbox("Abrir um documento", list(titles), format_func=titles.get)
            detail, detail_error = fetch_document(source, strategy)
            if detail_error:
                st.error(detail_error)
            elif detail:
                st.markdown(
                    f'<div class="rag-source-meta"><span class="file">📄 '
                    f"{html.escape(detail['path'])}</span></div>",
                    unsafe_allow_html=True,
                )
                view = st.radio(
                    "Ver",
                    ["Texto", "Chunks", "Perguntas de teste"],
                    horizontal=True,
                    label_visibility="collapsed",
                )
                if view == "Texto":
                    with st.container(height=520, border=True):
                        st.markdown(detail["text"])
                elif view == "Chunks":
                    st.caption(
                        f"{len(detail['chunks'])} chunks na estratégia "
                        f"**{STRATEGIES.get(detail['strategy'], detail['strategy'])}** "
                        "(troque na barra lateral)."
                    )
                    for chunk in detail["chunks"]:
                        with st.expander(
                            f"#{chunk['index']} · {chunk['section'] or '(sem seção)'} · "
                            f"{chunk['chars']} caracteres"
                        ):
                            st.markdown(
                                f'<div class="rag-excerpt">{html.escape(chunk["text"])}</div>',
                                unsafe_allow_html=True,
                            )
                else:
                    doc_questions = by_source.get(source, [])
                    if not doc_questions:
                        st.caption(
                            "Nenhuma pergunta do conjunto de teste aponta para este arquivo."
                        )
                    for q in doc_questions:
                        st.markdown(
                            f"- **{q['id']}** {q['question']}  \n"
                            f"  trecho esperado: `{q['expected_snippets'][0]}`"
                        )
                    if doc_questions and st.button("Testar a recuperação destas perguntas"):
                        data, error = call_api(
                            "/validation/retrieval",
                            {
                                "ids": [q["id"] for q in doc_questions],
                                "strategy": strategy,
                                "mode": mode,
                                "top_k": top_k,
                            },
                        )
                        if error:
                            st.error(error)
                        else:
                            hits = sum(r["hit"] for r in data["rows"])
                            st.success(
                                f"Trecho esperado entre os {top_k} primeiros em "
                                f"{rate(hits, len(data['rows']))} das perguntas."
                            )
                            st.dataframe(
                                [
                                    {
                                        "ok": "✅" if r["hit"] else "❌",
                                        "id": r["id"],
                                        "posição": r["rank"],
                                        "pergunta": r["question"],
                                    }
                                    for r in data["rows"]
                                ],
                                hide_index=True,
                                use_container_width=True,
                            )


# --- Aba 3: Validação ---------------------------------------------------------------

with tab_validation:
    st.markdown("### Validação ao vivo com o conjunto de teste")
    st.caption(
        "Roda as perguntas de `eval/datasets/perguntas_teste.json` contra a API, com a "
        "configuração da barra lateral. É a mesma regra da avaliação oficial (`eval/run_eval.py`), "
        "mas pergunta a pergunta, para você ver onde o sistema acerta e onde erra."
    )
    if MOCK_MODE:
        st.warning(
            "Modo de Visualização ativo: estes números servem para testar a tela, não valem "
            "como resultado do trabalho."
        )
    if questions_error:
        st.error(questions_error)
    elif questions:
        answerable = [q for q in questions if q["answerable"]]
        unanswerable = [q for q in questions if not q["answerable"]]

        st.markdown("#### 1. Recuperação: o trecho certo chega ao modelo? (rápido, sem LLM)")
        st.caption(
            f"Para cada uma das {len(answerable)} perguntas com resposta, confere se o trecho "
            f"esperado está entre os {top_k} primeiros recuperados (Recall@{top_k})."
        )
        if st.button(f"Rodar as {len(answerable)} perguntas com resposta", type="primary"):
            rows: list[dict] = []
            progress = st.progress(0.0, text="Consultando a API…")
            error = None
            for start in range(0, len(answerable), BATCH):
                ids = [q["id"] for q in answerable[start : start + BATCH]]
                data, error = call_api(
                    "/validation/retrieval",
                    {"ids": ids, "strategy": strategy, "mode": mode, "top_k": top_k},
                )
                if error:
                    break
                rows += data["rows"]
                progress.progress(len(rows) / len(answerable), text=f"{len(rows)} perguntas")
            progress.empty()
            st.session_state["val_retrieval"] = {
                "rows": rows,
                "error": error,
                "config": f"{STRATEGIES[strategy]} · {MODES[mode]} · top-{top_k}",
                "k": top_k,
            }

        result = st.session_state.get("val_retrieval")
        if result:
            if result["error"]:
                st.error(result["error"])
            rows = result["rows"]
            if rows:
                hits = sum(r["hit"] for r in rows)
                ranks = [r["rank"] for r in rows if r["rank"]]
                mrr = sum(1 / r for r in ranks) / len(rows)
                cols = st.columns(3)
                cols[0].metric(f"Recall@{result['k']}", f"{hits / len(rows):.0%}")
                cols[1].metric("Acertos", f"{hits}/{len(rows)}")
                cols[2].metric("MRR", f"{mrr:.2f}")
                st.caption(f"Configuração: {result['config']}")
                st.dataframe(
                    [
                        {
                            "ok": "✅" if r["hit"] else "❌",
                            "id": r["id"],
                            "posição": r["rank"],
                            "documento esperado": r["expected_source"],
                            "1º recuperado": (r["retrieved_sources"] or [""])[0],
                            "pergunta": r["question"],
                        }
                        for r in rows
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
                st.download_button(
                    "Baixar CSV",
                    to_csv(rows),
                    file_name="validacao_recuperacao.csv",
                    mime="text/csv",
                )

        st.markdown("#### 2. Resposta e recusa: o modelo cita a fonte e recusa o que não sabe?")
        st.caption(
            "Chama o LLM de verdade (cerca de 10 s a 30 s por pergunta em CPU). Perguntas sem "
            "resposta precisam ser recusadas; perguntas com resposta precisam ser respondidas "
            "citando o documento esperado."
        )
        cols = st.columns(2)
        n_answerable = cols[0].number_input(
            "Perguntas com resposta a testar", 0, len(answerable), min(5, len(answerable))
        )
        include_unanswerable = cols[1].checkbox(
            f"Incluir as {len(unanswerable)} perguntas sem resposta", value=True
        )
        selected = answerable[: int(n_answerable)] + (unanswerable if include_unanswerable else [])
        if st.button(f"Rodar {len(selected)} perguntas com o LLM", disabled=not selected):
            rows = []
            progress = st.progress(0.0, text="Perguntando ao modelo…")
            for i, q in enumerate(selected, start=1):
                data, error = call_api(
                    "/ask",
                    {"question": q["question"], "strategy": strategy, "mode": mode, "top_k": top_k},
                )
                cited = sorted({c["source"] for c in (data or {}).get("citations", [])})
                if error:
                    outcome, ok = f"erro: {error}", False
                elif q["answerable"]:
                    ok = not data["refused"] and q.get("expected_source") in cited
                    outcome = "recusou" if data["refused"] else "respondeu"
                else:
                    ok = data["refused"]
                    outcome = "recusou" if data["refused"] else "respondeu"
                rows.append(
                    {
                        "ok": "✅" if ok else "❌",
                        "id": q["id"],
                        "esperado": "responder citando " + q["expected_source"]
                        if q["answerable"]
                        else "recusar",
                        "obtido": outcome,
                        "fontes citadas": ", ".join(cited),
                        "pergunta": q["question"],
                        "_answerable": q["answerable"],
                        "_ok": ok,
                    }
                )
                progress.progress(i / len(selected), text=f"{i}/{len(selected)} perguntas")
            progress.empty()
            st.session_state["val_generation"] = rows

        rows = st.session_state.get("val_generation")
        if rows:
            with_answer = [r for r in rows if r["_answerable"]]
            without = [r for r in rows if not r["_answerable"]]
            cols = st.columns(2)
            cols[0].metric(
                "Respostas fundamentadas",
                rate(sum(r["_ok"] for r in with_answer), len(with_answer)),
            )
            cols[1].metric("Recusas corretas", rate(sum(r["_ok"] for r in without), len(without)))
            visible_rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
            st.dataframe(visible_rows, hide_index=True, use_container_width=True)
            st.download_button(
                "Baixar CSV",
                to_csv(visible_rows),
                file_name="validacao_respostas.csv",
                mime="text/csv",
                key="csv_generation",
            )
