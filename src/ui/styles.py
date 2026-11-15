"""Tema visual da interface: claro, minimalista, com destaque em azul cobalto.

Tipografia (fontes livres): Plus Jakarta Sans (Google Fonts, licença OFL) nos títulos e
subtítulos; Arial nos textos, respostas e trechos. As cores ficam nas variáveis de :root.
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

:root {
  --bg: #FFFFFF; --surface: #F8FAFC; --border: #E2E8F0; --text: #0F172A;
  --muted: #64748B; --accent: #2563EB; --accent-soft: #EFF6FF;
  --warn: #B45309; --warn-soft: #FFFBEB; --warn-border: #FCD34D;
  --ok: #15803D; --ok-soft: #F0FDF4;
  --font-head: 'Plus Jakarta Sans', Arial, sans-serif;
  --font-body: Arial, Helvetica, sans-serif;
}

html, body, .stApp, .stMarkdown, .stMarkdown p, .stText, textarea, input, label,
[data-testid="stCaptionContainer"], [data-testid="stExpander"] summary p {
  font-family: var(--font-body) !important;
  color: var(--text);
}
h1, h2, h3, h4, h5, h6, .rag-head, [data-testid="stHeading"] * {
  font-family: var(--font-head) !important;
  letter-spacing: -0.01em;
  color: var(--text);
}
.stApp { background: var(--bg); }
[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); }
.block-container { padding-top: 2rem; max-width: 1100px; }

/* Cabeçalho */
.rag-hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 .25rem 0; }
.rag-hero p { color: var(--muted); margin: 0; font-size: .95rem; }
.rag-hero .dot { color: var(--accent); }

/* Cartões */
.rag-card {
  background: var(--bg); border: 1px solid var(--border); border-radius: 12px;
  padding: 1.1rem 1.25rem; margin: .75rem 0; box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
}
.rag-card.answer { border-left: 4px solid var(--accent); }
.rag-card.refusal { background: var(--warn-soft); border: 1px solid var(--warn-border);
  border-left: 4px solid var(--warn); }
.rag-card .label {
  font-family: var(--font-head); font-size: .72rem; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; color: var(--muted); margin-bottom: .5rem;
}
.rag-card.refusal .label { color: var(--warn); }
.rag-card .body { font-family: var(--font-body); font-size: 1rem; line-height: 1.6; }
.rag-card .body code, .rag-excerpt code {
  background: var(--surface); border: 1px solid var(--border); border-radius: 4px;
  padding: 0 .3rem; font-size: .88em;
}
.rag-card .body pre { background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: .75rem; overflow-x: auto; }
.rag-card .reason { margin-top: .6rem; font-size: .9rem; color: var(--warn); }

/* Citações inline [n] */
.cite {
  display: inline-block; min-width: 1.35rem; padding: 0 .35rem; margin: 0 .1rem;
  border-radius: 999px; background: var(--accent-soft); color: var(--accent);
  font-size: .75rem; font-weight: 700; text-align: center; line-height: 1.35rem;
  border: 1px solid #BFDBFE;
}

/* Chips de métricas */
.rag-chips { display: flex; flex-wrap: wrap; gap: .4rem; margin: .25rem 0 .75rem; }
.chip {
  font-family: var(--font-body); font-size: .78rem; color: var(--muted);
  background: var(--surface); border: 1px solid var(--border); border-radius: 999px;
  padding: .15rem .6rem;
}
.chip b { color: var(--text); font-weight: 600; }
.chip.ok { color: var(--ok); background: var(--ok-soft); border-color: #BBF7D0; }
.chip.warn { color: var(--warn); background: var(--warn-soft); border-color: var(--warn-border); }

/* Fontes */
.rag-source-meta { display: flex; flex-wrap: wrap; gap: .4rem; align-items: center;
  margin-bottom: .6rem; }
.file { font-family: var(--font-body); font-weight: 700; font-size: .85rem; color: var(--accent); }
.section { font-size: .85rem; color: var(--muted); }
.scorebar { height: 6px; background: var(--border); border-radius: 999px; overflow: hidden;
  margin: .2rem 0 .7rem; }
.scorebar > span { display: block; height: 100%; background: var(--accent); border-radius: 999px; }
.rag-excerpt {
  font-family: var(--font-body); font-size: .92rem; line-height: 1.55; white-space: pre-wrap;
  background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
  padding: .75rem .9rem; max-height: 320px; overflow-y: auto;
}

[data-testid="stExpander"] details {
  border: 1px solid var(--border) !important; border-radius: 10px !important;
  background: var(--bg);
}
[data-testid="stExpander"] details:hover { border-color: #93C5FD !important; }
[data-testid="stExpander"] summary:hover p { color: var(--accent); }

.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button {
  border-radius: 8px; font-family: var(--font-head) !important; font-weight: 600;
}
textarea { border-radius: 10px !important; }

.rag-demo {
  background: var(--accent-soft); border: 1px solid #BFDBFE; border-radius: 10px;
  padding: .6rem .9rem; margin: .25rem 0 1rem; font-size: .88rem; color: #1E3A8A;
}
.status-line { font-size: .85rem; margin: .15rem 0; }
.hist { font-size: .82rem; color: var(--muted); margin: .2rem 0; line-height: 1.35; }

/* Conversa (aba Perguntar) */
[data-testid="stChatMessage"] { background: transparent; padding: .5rem 0; gap: .6rem; }
.rag-user {
  display: inline-block; background: var(--accent-soft); border: 1px solid #BFDBFE;
  border-radius: 14px 14px 14px 4px; padding: .55rem .9rem; line-height: 1.5;
  max-width: 100%; overflow-wrap: anywhere;
}
[data-testid="stChatMessage"] .rag-card { margin-top: 0; }
[data-testid="stChatInput"] textarea { font-family: var(--font-body) !important; }

/* Responsividade: tablet e celular */
@media (max-width: 900px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
}
@media (max-width: 640px) {
  .block-container { padding-top: 1rem; }
  .rag-hero h1 { font-size: 1.45rem; }
  .rag-hero p { font-size: .88rem; }
  .rag-card { padding: .8rem .9rem; border-radius: 10px; }
  .rag-card .body { font-size: .95rem; }
  .rag-card .body pre, .rag-excerpt { font-size: .82rem; }
  .chip { font-size: .72rem; padding: .1rem .5rem; }
  .rag-source-meta { flex-direction: column; align-items: flex-start; gap: .15rem; }
  .stButton > button { font-size: .85rem; padding: .35rem .6rem; }
  [data-testid="stMetricValue"] { font-size: 1.3rem; }
}
</style>
"""
