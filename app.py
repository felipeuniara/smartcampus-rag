"""Interface web do SmartCampus RAG.   Uso: streamlit run app.py"""
import json

import streamlit as st

from smartcampus import config, db, rag
from smartcampus.assistente import Assistente

st.set_page_config(page_title="SmartCampus RAG", page_icon="🎓", layout="wide")

# ------------------------------------------------------------------ barra lateral: "login" e painel
with st.sidebar:
    st.title("🎓 SmartCampus")
    try:
        alunos = db.listar_alunos()
    except Exception as erro:
        st.error(f"Não foi possível conectar ao PostgreSQL.\n\n{erro}")
        st.stop()

    opcoes = {f"{a['nome']} ({a['ra']})": a["ra"] for a in alunos}
    ra = opcoes[st.selectbox("Aluno logado", list(opcoes))]

    modo_padrao = "claude" if config.usar_claude() else "offline"
    modo = st.radio("Modo do assistente", ["claude", "offline"], index=["claude", "offline"].index(modo_padrao),
                    help="offline = sem LLM; usa as mesmas funções de RAG e banco, com respostas extrativas")

    # recria o assistente ao trocar de aluno ou de modo
    chave = f"{ra}:{modo}"
    if st.session_state.get("chave") != chave:
        st.session_state.chave = chave
        st.session_state.bot = Assistente(ra, modo=modo)
        st.session_state.historico = []

    st.divider()
    st.subheader("📄 Boletim")
    boletim = db.gerar_boletim(ra)
    st.dataframe(
        [{
            "Disciplina": d["codigo"],
            **{k: v for k, v in d["notas"].items()},
            "Freq.%": d["frequencia"],
            "Média": d["media"],
            "Situação": d["situacao"],
        } for d in boletim["disciplinas"]],
        hide_index=True, width="stretch",
    )
    alertas = db.listar_alertas(ra)
    if alertas:
        st.subheader("🔔 Alertas (triggers)")
        for a in alertas:
            st.warning(f"**{a['codigo']}** — {a['mensagem']}")

    st.divider()
    if st.button("🔄 Reindexar documentos no ChromaDB"):
        with st.spinner("Indexando..."):
            resumo = rag.indexar()
        st.success(f"{resumo['arquivos']} arquivos, {resumo['chunks']} chunks")
    if st.button("🧹 Limpar conversa"):
        st.session_state.bot = Assistente(ra, modo=modo)
        st.session_state.historico = []
        st.rerun()

# ------------------------------------------------------------------ chat
st.header("Assistente acadêmico")
st.caption(f"RAG com ChromaDB + PostgreSQL (procedures/triggers) · modo **{modo}**"
           + (f" · modelo `{config.CLAUDE_MODELO}`" if modo == "claude" else ""))

if not st.session_state.historico:
    st.info("Experimente: **Qual é o conteúdo da P2 e qual é minha média atual em Banco de Dados?** · "
            "**Gere meu boletim** · **Quanto preciso tirar na P2 para passar?** · "
            "**Abra um chamado pedindo revisão da minha P1 de BDA301**")


def mostrar_chamadas(chamadas):
    if not chamadas:
        return
    with st.expander(f"🔧 {len(chamadas)} chamada(s) de ferramenta"):
        for c in chamadas:
            st.markdown(f"**{c['ferramenta']}** `{json.dumps(c['entrada'], ensure_ascii=False)}`")
            try:
                st.json(json.loads(c["resultado"]), expanded=False)
            except (json.JSONDecodeError, TypeError):
                st.code(c["resultado"])


for msg in st.session_state.historico:
    with st.chat_message(msg["papel"]):
        st.markdown(msg["texto"])
        mostrar_chamadas(msg.get("chamadas"))

if pergunta := st.chat_input("Pergunte sobre provas, regras, notas, boletim..."):
    st.session_state.historico.append({"papel": "user", "texto": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)
    with st.chat_message("assistant"):
        with st.spinner("Consultando documentos e banco de dados..."):
            try:
                r = st.session_state.bot.responder(pergunta)
            except Exception as erro:
                r = {"resposta": f"⚠️ Erro: {erro}", "chamadas": []}
        st.markdown(r["resposta"])
        mostrar_chamadas(r["chamadas"])
    st.session_state.historico.append({"papel": "assistant", "texto": r["resposta"], "chamadas": r["chamadas"]})
