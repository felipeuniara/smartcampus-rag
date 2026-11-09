# Aulas 9 a 11 — Embeddings, ChromaDB e RAG (BDA301)

## Embeddings

Um **embedding** é um vetor numérico que representa o significado de um texto. Textos com sentido
parecido geram vetores próximos no espaço. Modelos como o `all-MiniLM-L6-v2` geram vetores de
**384 dimensões**.

A proximidade é medida por **similaridade de cosseno**: cos(θ) = (A · B) / (|A| × |B|).
O valor vai de -1 a 1; quanto mais próximo de 1, mais semelhantes. A **distância de cosseno** é 1 − similaridade.

## ChromaDB

O ChromaDB é um banco de dados vetorial open source. Conceitos principais:

- **Client**: `chromadb.PersistentClient(path="./chroma_db")` grava os dados em disco.
- **Collection**: conjunto de documentos com seus embeddings; criada com `get_or_create_collection`.
- **add / upsert**: insere `ids`, `documents`, `metadatas` (e opcionalmente `embeddings`).
- **query**: recebe `query_texts` e `n_results` e devolve os documentos mais próximos com suas distâncias.
- **where**: filtro por metadados, por exemplo `where={"disciplina": "BDA301"}`.

Por padrão o ChromaDB usa uma função de embedding local baseada no modelo all-MiniLM-L6-v2 (ONNX).

## Chunking

Documentos longos são divididos em **chunks** (trechos) antes da indexação:

- **Tamanho fixo**: cortes a cada N caracteres; simples, mas pode quebrar frases.
- **Por estrutura**: divide por títulos, seções ou parágrafos; preserva o sentido.
- **Overlap (sobreposição)**: repete parte do chunk anterior no próximo para não perder contexto.

Chunks muito grandes diluem o significado; chunks muito pequenos perdem contexto. Valores comuns: 500 a 1000 caracteres.

## RAG — Retrieval-Augmented Generation

O pipeline RAG tem quatro etapas:

1. **Indexação**: carregar documentos, dividir em chunks, gerar embeddings e salvar no banco vetorial.
2. **Recuperação**: gerar o embedding da pergunta e buscar os k chunks mais similares.
3. **Aumento**: inserir os chunks recuperados no prompt como contexto.
4. **Geração**: o LLM responde usando o contexto e cita as fontes.

Vantagens: reduz alucinações, permite atualizar o conhecimento sem re-treinar o modelo e
permite citar a origem da informação.

## Function calling

No **function calling** (tool use), a aplicação descreve ferramentas para o LLM com nome, descrição
e parâmetros em JSON Schema. O modelo decide quando chamar uma ferramenta; a aplicação executa a
função (por exemplo, uma consulta SQL ou uma procedure) e devolve o resultado ao modelo, que então
formula a resposta final. É assim que o assistente combina RAG (documentos) com dados do banco relacional (notas e médias).

## Segurança

- **SQL injection**: sempre usar consultas parametrizadas; nunca concatenar texto do usuário no SQL.
- **Prompt injection**: textos recuperados ou digitados podem conter instruções maliciosas; o modelo
  deve tratá-los como dados.
- **Menor privilégio**: o chatbot só acessa os dados do aluno autenticado; o identificador do aluno
  vem da sessão, nunca do texto digitado.
