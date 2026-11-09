"""Configurações lidas do arquivo .env (ou das variáveis de ambiente)."""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

# Banco relacional (PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/smartcampus")
DB_SCHEMA = "smartcampus"

# Base vetorial (ChromaDB)
PASTA_DOCUMENTOS = Path(os.getenv("PASTA_DOCUMENTOS", RAIZ / "documentos"))
CHROMA_PATH = os.getenv("CHROMA_PATH", str(RAIZ / "chroma_db"))
CHROMA_COLECAO = os.getenv("CHROMA_COLECAO", "smartcampus_docs")
TAMANHO_CHUNK = int(os.getenv("TAMANHO_CHUNK", "900"))
OVERLAP_CHUNK = int(os.getenv("OVERLAP_CHUNK", "150"))
TOP_K = int(os.getenv("TOP_K", "4"))
EMBEDDING_MODELO = os.getenv("EMBEDDING_MODELO", "padrao")

# LLM (Claude). MODO_ASSISTENTE: auto | claude | offline
MODO_ASSISTENTE = os.getenv("MODO_ASSISTENTE", "auto").lower()
CLAUDE_MODELO = os.getenv("CLAUDE_MODELO", "claude-opus-5-5")
CLAUDE_EFFORT = os.getenv("CLAUDE_EFFORT", "medium")  # low | medium | high


def usar_claude() -> bool:
    """Decide se o assistente usa o Claude ou o modo offline (sem LLM)."""
    if MODO_ASSISTENTE == "claude":
        return True
    if MODO_ASSISTENTE == "offline":
        return False
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))
