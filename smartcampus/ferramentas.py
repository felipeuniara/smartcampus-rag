"""Ferramentas (function calling) que o chatbot pode chamar.

Segurança: o RA do aluno NUNCA é um parâmetro das ferramentas. Ele vem da sessão autenticada,
então o modelo não consegue consultar dados de outro aluno, mesmo que o usuário peça.
"""
import json

from . import db, rag

FERRAMENTAS = [
    {
        "name": "buscar_documentos",
        "description": (
            "Busca trechos nos documentos acadêmicos indexados no ChromaDB (plano de ensino, materiais das aulas, "
            "regulamento acadêmico, FAQ da secretaria). Use para qualquer pergunta sobre conteúdo de provas, datas, "
            "pesos, regras de aprovação, frequência, prazos, procedimentos ou matéria das aulas. "
            "Faça uma consulta curta e específica; pode chamar mais de uma vez com consultas diferentes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "consulta": {"type": "string", "description": "Texto da busca, ex.: 'conteúdo da prova P2'"},
                "disciplina": {
                    "type": "string",
                    "description": "Código da disciplina para filtrar (ex.: BDA301). Opcional.",
                },
            },
            "required": ["consulta"],
        },
    },
    {
        "name": "consultar_media",
        "description": (
            "Calcula a média atual do aluno logado em uma disciplina, chamando a procedure sp_calcular_media do "
            "banco. Retorna média ponderada, situação e notas lançadas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"disciplina": {"type": "string", "description": "Código da disciplina, ex.: BDA301"}},
            "required": ["disciplina"],
        },
    },
    {
        "name": "gerar_boletim",
        "description": (
            "Gera o boletim completo do aluno logado (todas as disciplinas, notas, frequência, média e situação), "
            "chamando a procedure sp_gerar_boletim."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "listar_minhas_disciplinas",
        "description": "Lista as disciplinas em que o aluno logado está matriculado (código, nome, professor, frequência).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "consultar_alertas_e_chamados",
        "description": (
            "Lista os alertas acadêmicos abertos (média baixa, frequência baixa, gerados por triggers) "
            "e os chamados/dúvidas do aluno logado com seus status."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "abrir_chamado",
        "description": (
            "Abre um chamado/dúvida para a secretaria ou professor em nome do aluno logado "
            "(ex.: pedido de revisão de nota, dúvida sobre matéria). Só use quando o aluno pedir explicitamente."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "assunto": {"type": "string", "description": "Resumo curto (até 150 caracteres)"},
                "descricao": {"type": "string", "description": "Descrição completa da solicitação"},
                "disciplina": {"type": "string", "description": "Código da disciplina relacionada. Opcional."},
            },
            "required": ["assunto", "descricao"],
        },
    },
]


def executar(nome: str, entrada: dict, ra: str) -> dict:
    """Executa uma ferramenta para o aluno da sessão e devolve um dicionário serializável."""
    entrada = entrada or {}
    if nome == "buscar_documentos":
        trechos = rag.buscar(entrada["consulta"], disciplina=entrada.get("disciplina") or None)
        return {"trechos": [{k: t[k] for k in ("fonte", "secao", "score", "texto")} for t in trechos]}
    if nome == "consultar_media":
        return db.calcular_media(ra, entrada["disciplina"])
    if nome == "gerar_boletim":
        return db.gerar_boletim(ra)
    if nome == "listar_minhas_disciplinas":
        return {"disciplinas": db.listar_disciplinas_do_aluno(ra)}
    if nome == "consultar_alertas_e_chamados":
        return {"alertas_abertos": db.listar_alertas(ra), "chamados": db.listar_chamados(ra)}
    if nome == "abrir_chamado":
        return db.abrir_chamado(
            ra, entrada["assunto"][:150], entrada["descricao"], entrada.get("disciplina") or None
        )
    raise ValueError(f"Ferramenta desconhecida: {nome}")


def executar_json(nome: str, entrada: dict, ra: str) -> tuple[str, bool]:
    """Versão para o loop do LLM: devolve (texto_json, houve_erro)."""
    try:
        return json.dumps(executar(nome, entrada, ra), ensure_ascii=False), False
    except Exception as erro:  # o erro volta para o modelo como tool_result com is_error
        primeira_linha = str(erro).splitlines()[0] if str(erro) else type(erro).__name__
        return f"Erro ao executar {nome}: {primeira_linha}", True
