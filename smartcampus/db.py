"""Acesso ao banco relacional. Toda regra de negócio fica nas procedures/triggers do PostgreSQL;
aqui só chamamos essas rotinas com consultas parametrizadas (nada de concatenar texto no SQL)."""
from contextlib import contextmanager
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

from . import config


@contextmanager
def conectar():
    conn = psycopg.connect(
        config.DATABASE_URL,
        autocommit=True,
        row_factory=dict_row,
        options=f"-c search_path={config.DB_SCHEMA}",
    )
    try:
        yield conn
    finally:
        conn.close()


def _limpar(valor):
    """Converte Decimal/datas para tipos serializáveis em JSON."""
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, dict):
        return {k: _limpar(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_limpar(v) for v in valor]
    if hasattr(valor, "isoformat"):
        return valor.strftime("%d/%m/%Y %H:%M")
    return valor


def _consultar(sql: str, params=()):
    with conectar() as conn:
        return [_limpar(dict(r)) for r in conn.execute(sql, params).fetchall()]


# ---------------------------------------------------------------- alunos

def listar_alunos():
    return _consultar("SELECT ra, nome, curso FROM alunos ORDER BY nome")


def obter_aluno(ra: str):
    linhas = _consultar("SELECT id, ra, nome, email, curso FROM alunos WHERE ra = %s", (ra,))
    return linhas[0] if linhas else None


def listar_disciplinas_do_aluno(ra: str):
    return _consultar(
        """SELECT d.codigo, d.nome, d.professor, m.semestre, m.frequencia
             FROM matriculas m
             JOIN alunos a ON a.id = m.aluno_id
             JOIN disciplinas d ON d.id = m.disciplina_id
            WHERE a.ra = %s ORDER BY d.codigo""",
        (ra,),
    )


# ---------------------------------------------------------------- procedures

def calcular_media(ra: str, codigo: str):
    """Chama a procedure sp_calcular_media e devolve média + situação + notas."""
    codigo = codigo.upper().strip()
    with conectar() as conn:
        linha = conn.execute("CALL sp_calcular_media(%s, %s)", (ra, codigo)).fetchone()
    notas = _consultar(
        """SELECT n.avaliacao, n.peso, n.valor
             FROM notas n
             JOIN matriculas m ON m.id = n.matricula_id
             JOIN alunos a ON a.id = m.aluno_id
             JOIN disciplinas d ON d.id = m.disciplina_id
            WHERE a.ra = %s AND d.codigo = %s ORDER BY n.avaliacao""",
        (ra, codigo),
    )
    return {
        "disciplina": codigo,
        "media_atual": _limpar(linha["p_media"]),
        "situacao": linha["p_situacao"],
        "notas_lancadas": notas,
        "observacao": "Média ponderada considerando apenas as avaliações já lançadas.",
    }


def gerar_boletim(ra: str):
    """Chama a procedure sp_gerar_boletim, que devolve o boletim em JSON."""
    with conectar() as conn:
        linha = conn.execute("CALL sp_gerar_boletim(%s)", (ra,)).fetchone()
    return _limpar(linha["p_boletim"])


def abrir_chamado(ra: str, assunto: str, descricao: str, codigo: str | None = None):
    with conectar() as conn:
        linha = conn.execute(
            "CALL sp_abrir_chamado(%s, %s, %s, %s)",
            (ra, codigo.upper() if codigo else None, assunto, descricao),
        ).fetchone()
    return {"chamado_id": linha["p_chamado_id"], "status": "aberto"}


def lancar_nota(ra: str, codigo: str, avaliacao: str, valor: float):
    """Uso administrativo (demonstração dos triggers) — não é exposto ao chatbot."""
    with conectar() as conn:
        conn.execute(
            "CALL sp_lancar_nota(%s::varchar, %s::varchar, %s::varchar, %s::numeric)",
            (ra, codigo.upper(), avaliacao.upper(), valor),
        )


# ---------------------------------------------------------------- consultas de apoio

def listar_alertas(ra: str, apenas_abertos: bool = True):
    return _consultar(
        """SELECT al.tipo, al.mensagem, al.valor, al.resolvido, al.criado_em, d.codigo
             FROM alertas al
             JOIN matriculas m ON m.id = al.matricula_id
             JOIN alunos a ON a.id = m.aluno_id
             JOIN disciplinas d ON d.id = m.disciplina_id
            WHERE a.ra = %s AND (NOT %s OR NOT al.resolvido)
            ORDER BY al.criado_em DESC""",
        (ra, apenas_abertos),
    )


def listar_chamados(ra: str):
    return _consultar(
        """SELECT c.id, c.assunto, c.status, c.origem, c.resposta, c.criado_em, d.codigo AS disciplina
             FROM chamados c
             JOIN alunos a ON a.id = c.aluno_id
             LEFT JOIN disciplinas d ON d.id = c.disciplina_id
            WHERE a.ra = %s ORDER BY c.criado_em DESC""",
        (ra,),
    )


def listar_log_notas(limite: int = 20):
    return _consultar(
        """SELECT l.avaliacao, l.valor_antigo, l.valor_novo, l.operacao, l.alterado_em,
                  a.ra, d.codigo
             FROM log_alteracao_notas l
             JOIN matriculas m ON m.id = l.matricula_id
             JOIN alunos a ON a.id = m.aluno_id
             JOIN disciplinas d ON d.id = m.disciplina_id
            ORDER BY l.alterado_em DESC LIMIT %s""",
        (limite,),
    )
