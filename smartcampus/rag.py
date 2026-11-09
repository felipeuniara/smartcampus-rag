"""Base vetorial no ChromaDB: leitura dos documentos, chunking, indexação e busca."""
import re
from pathlib import Path

import chromadb

from . import config

PADRAO_DISCIPLINA = re.compile(r"[A-Z]{3}\d{3}")


# ---------------------------------------------------------------- leitura

def ler_arquivo(caminho: Path) -> str:
    if caminho.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n\n".join(p.extract_text() or "" for p in PdfReader(caminho).pages)
    return caminho.read_text(encoding="utf-8")


def disciplina_do_arquivo(nome: str) -> str:
    """BDA301_plano_de_ensino.md -> BDA301; regulamento_academico.md -> INSTITUCIONAL."""
    achado = PADRAO_DISCIPLINA.search(nome.upper())
    return achado.group(0) if achado else "INSTITUCIONAL"


# ---------------------------------------------------------------- chunking

def _dividir_secoes(texto: str):
    """Divide um markdown em seções pelos títulos (#, ##, ###), guardando o caminho do título."""
    titulos: list[str] = []
    secao_atual, linhas = "", []
    for linha in texto.splitlines():
        m = re.match(r"^(#{1,4})\s+(.*)", linha)
        if m:
            if "".join(linhas).strip():
                yield secao_atual, "\n".join(linhas).strip()
            nivel = len(m.group(1))
            titulos = titulos[: nivel - 1] + [m.group(2).strip()]
            secao_atual, linhas = " > ".join(titulos), []
        else:
            linhas.append(linha)
    if "".join(linhas).strip():
        yield secao_atual, "\n".join(linhas).strip()


def _quebrar(texto: str, tamanho: int, overlap: int):
    """Quebra um texto longo em pedaços de ~tamanho caracteres, respeitando parágrafos, com overlap."""
    if len(texto) <= tamanho:
        return [texto]
    partes, atual = [], ""
    for paragrafo in re.split(r"\n\s*\n", texto):
        if atual and len(atual) + len(paragrafo) > tamanho:
            partes.append(atual.strip())
            atual = atual[-overlap:] + "\n\n"
        atual += paragrafo + "\n\n"
    if atual.strip():
        partes.append(atual.strip())
    return partes


def gerar_chunks(caminho: Path):
    texto = ler_arquivo(caminho)
    disciplina = disciplina_do_arquivo(caminho.name)
    chunks = []
    for secao, corpo in _dividir_secoes(texto):
        for i, pedaco in enumerate(_quebrar(corpo, config.TAMANHO_CHUNK, config.OVERLAP_CHUNK)):
            # o título da seção entra no texto indexado: melhora muito a recuperação
            conteudo = f"[{secao}]\n{pedaco}" if secao else pedaco
            chunks.append({
                "id": f"{caminho.name}::{len(chunks)}",
                "texto": conteudo,
                "metadados": {"fonte": caminho.name, "secao": secao or "-", "disciplina": disciplina, "parte": i},
            })
    return chunks


# ---------------------------------------------------------------- ChromaDB

def _funcao_embedding():
    """Padrão: all-MiniLM-L6-v2 (ONNX, embutido no ChromaDB, sem GPU/PyTorch).
    Opcional: um modelo multilíngue do sentence-transformers (melhor para português),
    ex.: EMBEDDING_MODELO=paraphrase-multilingual-MiniLM-L12-v2 (requer pip install sentence-transformers)."""
    if config.EMBEDDING_MODELO and config.EMBEDDING_MODELO != "padrao":
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        return SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODELO)
    return None  # usa a função padrão do ChromaDB


def obter_colecao():
    cliente = chromadb.PersistentClient(path=config.CHROMA_PATH)
    kwargs = {"embedding_function": ef} if (ef := _funcao_embedding()) else {}
    return cliente.get_or_create_collection(
        name=config.CHROMA_COLECAO,
        metadata={"hnsw:space": "cosine"},  # distância de cosseno
        **kwargs,
    )


def indexar(pasta: Path | None = None, recriar: bool = True) -> dict:
    pasta = Path(pasta or config.PASTA_DOCUMENTOS)
    cliente = chromadb.PersistentClient(path=config.CHROMA_PATH)
    if recriar:
        try:
            cliente.delete_collection(config.CHROMA_COLECAO)
        except Exception:
            pass
    colecao = obter_colecao()

    arquivos = sorted(p for p in pasta.iterdir() if p.suffix.lower() in {".md", ".txt", ".pdf"})
    total = 0
    for arquivo in arquivos:
        chunks = gerar_chunks(arquivo)
        if not chunks:
            continue
        colecao.upsert(
            ids=[c["id"] for c in chunks],
            documents=[c["texto"] for c in chunks],
            metadatas=[c["metadados"] for c in chunks],
        )
        total += len(chunks)
        print(f"  {arquivo.name}: {len(chunks)} chunks")
    return {"arquivos": len(arquivos), "chunks": total}


# ---------------------------------------------------------------- busca híbrida

STOPWORDS = set("""a o e é de da do das dos em no na nos nas um uma uns umas para por com sem que qual quais
quando onde como ao aos à às se meu minha meus minhas eu me seu sua ser são foi está estou the
mais menos ou mas sobre isso esse essa este esta qual tem ter há vai""".split())


def _normalizar(texto: str) -> str:
    import unicodedata
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _tokens(texto: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", _normalizar(texto)) if t not in STOPWORDS and len(t) > 1}


def _score_lexico(consulta: set[str], documento: str) -> float:
    """Fração dos termos da pergunta que aparecem no chunk (0 a 1)."""
    if not consulta:
        return 0.0
    return len(consulta & _tokens(documento)) / len(consulta)


def buscar(consulta: str, k: int | None = None, disciplina: str | None = None) -> list[dict]:
    """Busca híbrida: similaridade vetorial (ChromaDB) + correspondência de palavras-chave.
    O modelo de embedding padrão foi treinado em inglês; o componente léxico compensa isso
    para termos exatos em português como "P2", "frequência" ou "monitoria"."""
    k = k or config.TOP_K
    colecao = obter_colecao()
    if colecao.count() == 0:
        raise RuntimeError("A base vetorial está vazia. Rode: python ingest.py")
    filtro = None
    if disciplina:
        filtro = {"disciplina": {"$in": [disciplina.upper(), "INSTITUCIONAL"]}}

    # 1) candidatos por similaridade vetorial (pegamos mais que k para re-ranquear)
    n = min(colecao.count(), max(k * 4, 12))
    res = colecao.query(query_texts=[consulta], n_results=n, where=filtro)
    candidatos = {
        id_: (doc, meta, 1 - dist)
        for id_, doc, meta, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])
    }

    # 2) candidatos por palavra-chave (a base é pequena, então varremos todos os chunks)
    termos = _tokens(consulta)
    todos = colecao.get(where=filtro, include=["documents", "metadatas"])
    for id_, doc, meta in zip(todos["ids"], todos["documents"], todos["metadatas"]):
        if id_ not in candidatos and _score_lexico(termos, doc) > 0:
            candidatos[id_] = (doc, meta, None)

    # embeddings dos candidatos que vieram só pela busca léxica
    faltando = [i for i, (_, _, s) in candidatos.items() if s is None]
    if faltando:
        extra = colecao.query(query_texts=[consulta], n_results=colecao.count(), where=filtro)
        sims = {i: 1 - d for i, d in zip(extra["ids"][0], extra["distances"][0])}
        for i in faltando:
            doc, meta, _ = candidatos[i]
            candidatos[i] = (doc, meta, sims.get(i, 0.0))

    # 3) pontuação final = 60% vetorial + 40% léxica
    resultados = []
    for doc, meta, sim in candidatos.values():
        lex = _score_lexico(termos, doc)
        resultados.append({
            "texto": doc,
            "fonte": meta["fonte"],
            "secao": meta["secao"],
            "disciplina": meta["disciplina"],
            "similaridade": round(sim, 3),
            "score": round(0.6 * sim + 0.4 * lex, 3),
        })
    resultados.sort(key=lambda r: r["score"], reverse=True)
    return resultados[:k]
