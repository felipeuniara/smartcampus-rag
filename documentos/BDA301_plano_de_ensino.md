# Plano de Ensino — Banco de Dados Avançado (BDA301)

**Curso:** Ciência da Computação / Sistemas de Informação
**Semestre:** 2026.2
**Carga horária:** 80 horas (4 aulas semanais)
**Professora:** Prof.ª Helena Ribeiro — helena.ribeiro@smartcampus.edu.br
**Atendimento ao aluno:** terças-feiras, das 17h às 18h30, sala 214 do Bloco B

## Ementa

Programação no servidor de banco de dados: funções, stored procedures e triggers.
Controle de transações e concorrência. Índices e otimização de consultas.
Bancos de dados NoSQL. Bancos de dados vetoriais e embeddings.
Geração aumentada por recuperação (RAG) e integração de bancos de dados com modelos de linguagem.

## Objetivos

- Desenvolver lógica de negócio dentro do SGBD usando PL/pgSQL.
- Garantir integridade e auditoria de dados com triggers.
- Analisar planos de execução e criar índices adequados.
- Compreender o funcionamento de bancos vetoriais (ChromaDB) e da busca por similaridade.
- Construir aplicações que combinam banco relacional, banco vetorial e LLMs.

## Conteúdo programático

| Semana | Tema |
|---|---|
| 1 | Revisão de SQL e modelagem relacional |
| 2 | Funções em PL/pgSQL: variáveis, condicionais e laços |
| 3 | Stored procedures: parâmetros IN, OUT e INOUT; comando CALL |
| 4 | Triggers: BEFORE x AFTER, FOR EACH ROW, variáveis NEW e OLD |
| 5 | Transações, propriedades ACID e níveis de isolamento |
| 6 | Índices B-Tree e Hash, EXPLAIN e EXPLAIN ANALYZE |
| 7 | Bancos NoSQL: documentos, chave-valor e grafos |
| 8 | **Prova P1** |
| 9 | Embeddings e similaridade de cosseno |
| 10 | Bancos vetoriais: ChromaDB, coleções, metadados e consultas |
| 11 | RAG: chunking, recuperação e montagem de contexto |
| 12 | Function calling: integração de LLMs com bancos relacionais |
| 13 | Segurança: SQL injection, prompt injection e controle de acesso |
| 14 | Apresentação dos trabalhos em grupo |
| 15 | **Prova P2** |
| 16 | Exame final |

## Avaliações

| Avaliação | Peso | Data | Conteúdo cobrado |
|---|---|---|---|
| P1 | 35% | 25/09/2026 | Semanas 1 a 7: PL/pgSQL, procedures, triggers, transações, índices e NoSQL |
| Trabalho em grupo (SmartCampus RAG) | 30% | Entrega em 20/11/2026, apresentação em 27/11/2026 | Aplicação com banco relacional, ChromaDB, RAG e function calling |
| P2 | 35% | 04/12/2026 | Semanas 9 a 13: embeddings, bancos vetoriais, ChromaDB, RAG, function calling e segurança |
| Exame final | substitui a menor prova | 11/12/2026 | Todo o conteúdo do semestre |

A média final é calculada por: **Média = P1 × 0,35 + P2 × 0,35 + Trabalho × 0,30**.

### Detalhes da Prova P2

A P2 é individual, sem consulta, com duração de 100 minutos, realizada no laboratório 3.
É composta por 6 questões dissertativas e 10 questões de múltipla escolha.
Os tópicos cobrados são:

1. Embeddings: o que são, dimensão do vetor e similaridade de cosseno.
2. ChromaDB: criação de coleções, `add`, `query`, uso de metadados e filtros `where`.
3. Estratégias de chunking (tamanho fixo, por parágrafo, sobreposição/overlap).
4. Pipeline RAG completo: indexação, recuperação, aumento do prompt e geração.
5. Function calling: definição de ferramentas com JSON Schema e ciclo de chamada.
6. Segurança: SQL injection, prompt injection e princípio do menor privilégio.

### Detalhes da Prova P1 (já realizada)

A P1 cobriu funções, procedures, triggers, transações (ACID), índices e NoSQL.
As notas da P1 foram publicadas no sistema acadêmico em 02/10/2026.

## Trabalho em grupo

Grupos de até 4 alunos desenvolvem o protótipo SmartCampus RAG. Critérios de avaliação:

- Banco relacional com tabelas, procedures e triggers funcionando (30%).
- Base vetorial no ChromaDB com documentos da disciplina (20%).
- Chatbot RAG respondendo com base nos documentos (20%).
- Integração com o banco via function calling (20%).
- Vídeo, README e apresentação (10%).

Entregas fora do prazo perdem 1 ponto por dia de atraso, até o limite de 3 dias.

## Bibliografia

- ELMASRI, R.; NAVATHE, S. *Sistemas de Banco de Dados*. 7. ed. Pearson.
- Documentação oficial do PostgreSQL — capítulos PL/pgSQL e Triggers.
- Documentação oficial do ChromaDB.
- LEWIS, P. et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*, 2020.
