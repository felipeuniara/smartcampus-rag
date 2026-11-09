# Apresentação e roteiro do vídeo — SmartCampus RAG

## Slides sugeridos (5–6 slides)

1. **Problema e objetivo** — alunos perdem tempo procurando regras, conteúdo de prova e notas em lugares diferentes.
   Um único assistente responde tudo, com fonte.
2. **Arquitetura** — diagrama do README: Streamlit → Claude (function calling) → ChromaDB + PostgreSQL.
3. **Banco relacional** — modelo das tabelas; 4 procedures e 5 triggers (destaque: alerta automático de média baixa
   que já abre um chamado).
4. **RAG** — documentos usados, chunking por seção, metadados, busca híbrida (e por que precisamos dela).
5. **Integração** — exemplo da pergunta mista e as duas ferramentas chamadas; segurança (RA vem da sessão).
6. **Divisão de tarefas e tecnologias** (abaixo).

## Divisão de tarefas (preencher com os nomes do grupo)

| Integrante | Responsabilidade |
|---|---|
| Integrante 1 | Modelagem e script SQL: tabelas, inserts, procedures e triggers |
| Integrante 2 | Documentos da disciplina, chunking e base vetorial no ChromaDB (`rag.py`, `ingest.py`) |
| Integrante 3 | Chatbot e function calling (`assistente.py`, `ferramentas.py`, `db.py`) |
| Integrante 4 | Interface Streamlit, README, vídeo e apresentação |

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Banco relacional | PostgreSQL 18 · PL/pgSQL (procedures, functions, triggers) |
| Banco vetorial | ChromaDB (PersistentClient, distância de cosseno, metadados) |
| Embeddings | all-MiniLM-L6-v2 (ONNX, embutido no ChromaDB) |
| LLM | Claude (Anthropic API) com tool use / function calling |
| Backend | Python 3 · psycopg 3 · pypdf |
| Interface | Streamlit |

## Roteiro do vídeo (até 5 min)

| Tempo | Cena |
|---|---|
| 0:00–0:30 | Apresentação do grupo e do objetivo |
| 0:30–1:15 | `sql/smartcampus.sql` no editor: tabelas, procedures, triggers. No psql: `CALL sp_gerar_boletim('2026002');` |
| 1:15–1:50 | Pasta `documentos/` e `python ingest.py` + `python ingest.py --testar "conteúdo da P2"` |
| 1:50–3:30 | `streamlit run app.py`, logado como Bruno (2026002): <br>1. "Qual é o conteúdo da P2 e qual é minha média atual em Banco de Dados?" (abrir o expander de ferramentas) <br>2. "Quanto preciso tirar na P2 para passar?" <br>3. "Tenho algum alerta?" <br>4. "Abra um chamado pedindo revisão da minha P1 de BDA301" <br>5. "Qual a nota da Ana?" (recusa) |
| 3:30–4:30 | Triggers ao vivo: `python demo_triggers.py 2026001 ESW303 P1 3.0` → log de alteração, média recalculada, alerta e chamado automático; recarregar a interface da Ana e mostrar o alerta |
| 4:30–5:00 | Conclusão: aprendizados e melhorias futuras (login real, embeddings multilíngues, mais disciplinas) |
