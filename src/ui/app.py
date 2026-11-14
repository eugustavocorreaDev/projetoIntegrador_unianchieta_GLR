"""Interface de demonstração. Rode com: streamlit run src/ui/app.py

A interface só conversa com a API por HTTP (API_URL); não importa nada do backend.
"""

from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path

import httpx
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from styles import CSS  # noqa: E402

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = httpx.Timeout(float(os.getenv("UI_TIMEOUT_S", "300")), connect=5.0)

STRATEGIES = {"recursive": "Recursiva por seções", "fixed": "Tamanho fixo (baseline)"}
MODES = {
    "hybrid_rerank": "Híbrida + reranking",
    "hybrid": "Híbrida (vetorial + BM25)",
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

st.set_page_config(page_title="Assistente de documentação", page_icon="📘", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


# --- Acesso à API -------------------------------------------------------------


@st.cache_data(ttl=10, show_spinner=False)
def fetch_health() -> dict | None:
    try:
        return httpx.get(f"{API_URL}/health", timeout=5).json()
    except (httpx.HTTPError, ValueError):
        return None


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
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = response.text
        return None, f"Erro {response.status_code}: {detail}"
    return response.json(), None


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
            f'<span class="file">📄 {html.escape(item["source"])}</span>'
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

    if not only_search:
        if data["refused"]:
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
        status.append(
            ("status", "recusada", "warn") if data["refused"] else ("status", "respondida", "ok")
        )
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

    title = "Trechos recuperados" if only_search else "Todos os trechos enviados ao modelo"
    st.markdown(f"### {title}")
    if not retrieved:
        st.caption("Nenhum trecho recuperado.")
    for item in retrieved:
        render_source(f"#{item['rank']} {item['source']} › {item['section']}", item)


# --- Barra lateral ---------------------------------------------------------------

with st.sidebar:
    st.markdown("## Configuração")
    strategy = st.selectbox("Estratégia de chunking", list(STRATEGIES), format_func=STRATEGIES.get)
    mode = st.selectbox("Recuperação", list(MODES), format_func=MODES.get)
    top_k = st.slider("Trechos enviados ao modelo (top-k)", 1, 10, 5)
    only_search = st.toggle("Só recuperar (sem LLM)", value=False)

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


# --- Conteúdo principal ------------------------------------------------------------

st.markdown(
    '<div class="rag-hero"><h1>Assistente de documentação<span class="dot">.</span></h1>'
    "<p>Responde apenas com base na documentação indexada, cita a fonte de cada afirmação "
    "e avisa quando a informação não está lá. Não digite dados pessoais.</p></div>",
    unsafe_allow_html=True,
)
st.write("")

MOCK_MODE = bool(health and health.get("llm_mode") == "mock")
if MOCK_MODE:
    st.markdown(
        '<div class="rag-demo">🧪 <b>Modo de Visualização (Mock)</b>: as respostas organizam os '
        "trechos recuperados, com as citações, mas não são geradas por IA. Para ativar o LLM real, "
        "instale o Ollama, rode <code>ollama pull llama3.2:3b</code> e "
        "<code>ollama pull nomic-embed-text</code>, feche a janela da API e execute "
        "<code>scripts\\run_local.ps1</code> de novo.</div>",
        unsafe_allow_html=True,
    )


def _use_example(text: str) -> None:
    st.session_state["question"] = text


st.caption("Experimente")
for column, text in zip(st.columns(len(EXAMPLES)), EXAMPLES, strict=True):
    column.button(text, on_click=_use_example, args=(text,), use_container_width=True)

with st.form("pergunta", border=False):
    question = st.text_area(
        "Pergunta",
        key="question",
        height=96,
        max_chars=1000,
        placeholder="Ex.: Como validar o tamanho de um parâmetro de consulta?",
    )
    submitted = st.form_submit_button("Perguntar", type="primary")

if submitted:
    if len(question.strip()) < 3:
        st.warning("Escreva uma pergunta com pelo menos 3 caracteres.")
    else:
        payload = {"question": question.strip(), "strategy": strategy, "mode": mode, "top_k": top_k}
        label = "Buscando na documentação…" if only_search else "Buscando e gerando a resposta…"
        with st.spinner(label):
            data, error = call_api("/search" if only_search else "/ask", payload)
        st.session_state["last"] = {"data": data, "error": error, "mode": mode, "only": only_search}
        if data and not only_search:
            mark = "🛡️" if data["refused"] else "✅"
            st.session_state.setdefault("history", []).append(
                f"{mark} {html.escape(question.strip()[:90])}"
            )
        st.rerun()

last = st.session_state.get("last")
if last:
    if last["error"]:
        st.error(last["error"])
    elif last["data"]:
        render_result(last["data"], last["mode"], last["only"], mock=MOCK_MODE)
