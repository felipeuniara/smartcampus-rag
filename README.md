# 🎓 SmartCampus RAG

Protótipo de assistente acadêmico que responde perguntas sobre a disciplina usando **RAG com ChromaDB**
e consulta notas, médias e boletim em um **banco PostgreSQL com procedures e triggers**, integrando os
dois mundos via **function calling** com o Claude (Anthropic).

> Pergunta: *"Qual é o conteúdo da prova e qual é minha média atual?"*
> → o assistente busca o conteúdo da P2 no **plano de ensino** (ChromaDB) **e** chama a procedure
> `sp_calcular_media` no PostgreSQL, juntando tudo numa resposta só, com a fonte citada.

## Arquitetura

```
             ┌──────────────── Streamlit (app.py) / terminal (chat_cli.py) ────────────────┐
             │                       aluno logado = RA da sessão                          │
             └──────────────────────────────────┬──────────────────────────────────────────┘
                                                │ pergunta
                                     ┌──────────▼──────────┐
                                     │  Assistente (Claude) │  loop de function calling
                                     └───┬─────────────┬───┘
               buscar_documentos         │             │  consultar_media / gerar_boletim /
                                         │             │  abrir_chamado / alertas
                        ┌────────────────▼───┐     ┌───▼──────────────────────────────┐
                        │ ChromaDB           │     │ PostgreSQL (schema smartcampus)  │
                        │ busca híbrida:     │     │ procedures: sp_calcular_media,   │
                        │ vetorial + termos  │     │   sp_gerar_boletim, sp_lancar_   │
                        │ chunks c/ metadados│     │   nota, sp_abrir_chamado         │
                        └────────▲───────────┘     │ triggers: validação, log de nota,│
                                 │ ingest.py       │   recálculo de média, alertas    │
                        documentos/*.md|.pdf       └──────────────────────────────────┘
```

## Estrutura

| Caminho | O que é |
|---|---|
| `sql/smartcampus.sql` | Script completo: tabelas, funções, **4 procedures**, **5 triggers** e inserts |
| `documentos/` | Base de conhecimento: plano de ensino, aulas, regulamento e FAQ (aceita `.md`, `.txt`, `.pdf`) |
| `smartcampus/rag.py` | Leitura, chunking por seção, indexação no ChromaDB e busca híbrida |
| `smartcampus/db.py` | Chamadas às procedures e consultas (sempre parametrizadas) |
| `smartcampus/ferramentas.py` | Definição das ferramentas (JSON Schema) e execução |
| `smartcampus/assistente.py` | Loop de function calling com o Claude + modo offline |
| `app.py` | Interface web (Streamlit) com chat, boletim e alertas |
| `chat_cli.py` | Chat no terminal |
| `ingest.py` | Cria a base vetorial |
| `demo_triggers.py` | Lança uma nota e mostra os triggers em ação (bom para o vídeo) |

## Banco de dados

**Tabelas mínimas:** `alunos`, `disciplinas`, `matriculas`, `notas`, `chamados`
**Tabelas de apoio (alimentadas por triggers):** `log_alteracao_notas`, `alertas`

| Procedure | Função |
|---|---|
| `sp_calcular_media(ra, disciplina, INOUT media, INOUT situacao)` | Média ponderada (P1 35%, P2 35%, Trabalho 30%) e situação conforme o regulamento |
| `sp_gerar_boletim(ra, INOUT boletim JSONB)` | Boletim completo em JSON |
| `sp_lancar_nota(ra, disciplina, avaliacao, valor)` | Lança/corrige nota (upsert) |
| `sp_abrir_chamado(ra, disciplina, assunto, descricao, INOUT id)` | Abre chamado/dúvida |

| Trigger | Evento | Efeito |
|---|---|---|
| `trg_validar_nota` | BEFORE INSERT/UPDATE em `notas` | Rejeita nota fora de 0–10 e arredonda |
| `trg_log_alteracao_nota` | AFTER UPDATE/DELETE em `notas` | Grava valor antigo e novo em `log_alteracao_notas` |
| `trg_recalcular_media` | AFTER INSERT/UPDATE/DELETE em `notas` | Atualiza `matriculas.media` e `situacao` |
| `trg_alerta_media_baixa` | AFTER UPDATE OF media em `matriculas` | Média < 6,0 → cria alerta **e** chamado automático; média ≥ 6 → resolve o alerta |
| `trg_alerta_frequencia` | AFTER INSERT/UPDATE em `matriculas` | Frequência < 75% → alerta |

## Como executar

### 1. Pré-requisitos
- Python 3.10+
- PostgreSQL 14+ (testado no 18)
- (Opcional) chave da API da Anthropic — sem ela o sistema roda em **modo offline**

### 2. Instalar dependências
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
```

### 3. Criar o banco
```bash
psql -U postgres -c "CREATE DATABASE smartcampus;"
psql -U postgres -d smartcampus -f sql/smartcampus.sql
```
O script pode ser executado de novo a qualquer momento: ele recria o schema `smartcampus` do zero.

### 4. Configurar
Copie `.env.example` para `.env` e ajuste `DATABASE_URL` (usuário/senha do seu Postgres)
e, se tiver, `ANTHROPIC_API_KEY`.

### 5. Criar a base vetorial
```bash
python ingest.py
python ingest.py --testar "conteúdo da prova P2"
```
Na primeira execução o ChromaDB baixa o modelo de embeddings (~80 MB).

### 6. Rodar
```bash
streamlit run app.py
```
ou no terminal:
```bash
python chat_cli.py --ra 2026002 --debug
```

## Perguntas para a demonstração

| Pergunta | O que acontece |
|---|---|
| Qual é o conteúdo da P2 e qual é minha média atual em Banco de Dados? | RAG no plano de ensino + `sp_calcular_media` |
| Quanto preciso tirar na P2 para passar em BDA301? | Regulamento/pesos (RAG) + notas do banco; o Claude faz a conta |
| Gere meu boletim | `sp_gerar_boletim` |
| Tenho algum alerta? | Alertas gerados pelos triggers |
| Qual a frequência mínima? O que acontece se eu ficar abaixo? | RAG no regulamento |
| Abra um chamado pedindo revisão da minha P1 de BDA301 | `sp_abrir_chamado` |
| Qual a nota da Ana? | Recusado: o RA vem da sessão, não do texto |

Alunos de exemplo: **2026001** Ana (boas notas) · **2026002** Bruno (média baixa → alertas) ·
**2026003** Carla (frequência 70% → reprovada por falta em BDA301) · **2026004** Diego.

Para mostrar os triggers ao vivo (corrige a P1 da Ana em ESW303 de 9,5 para 3,0):
```bash
python demo_triggers.py 2026001 ESW303 P1 3.0
```
Resultado: linha nova em `log_alteracao_notas`, média recalculada para 3,0, alerta `MEDIA_BAIXA`
e um chamado automático de origem `sistema`. Para voltar ao estado inicial, rode o `sql/smartcampus.sql` de novo.

## Decisões de projeto

- **Busca híbrida.** O modelo de embedding padrão do ChromaDB (all-MiniLM-L6-v2) foi treinado em inglês.
  Em testes, a busca puramente vetorial não trazia a seção "Detalhes da Prova P2" para a pergunta
  "qual o conteúdo da P2". Combinamos 60% similaridade de cosseno + 40% correspondência de termos,
  o que resolveu o problema. Também é possível trocar por um modelo multilíngue (`EMBEDDING_MODELO`).
- **Chunking por seção** do markdown, com o caminho dos títulos incluído no texto do chunk e
  metadados (`fonte`, `secao`, `disciplina`) usados para citar a fonte e filtrar por disciplina.
- **Regras de negócio no banco.** Média, situação, auditoria e alertas ficam em procedures/triggers;
  assim valem para qualquer cliente (chatbot, portal, psql), não só para o Python.
- **Segurança.** O RA do aluno não é parâmetro de nenhuma ferramenta: vem da sessão. Todas as consultas
  são parametrizadas (sem SQL injection) e o prompt instrui o modelo a tratar trechos recuperados como dados
  (mitigação de prompt injection).
- **Modo offline.** Sem chave de API, um roteador por palavras-chave chama as mesmas ferramentas e monta
  uma resposta extrativa — útil para testar e demonstrar sem custo.
- **Modelo.** `claude-opus-5-5` com esforço `medium` (configurável). As requisições usam o parâmetro
  `fallbacks: "default"`: se o modelo recusar um pedido por política, a API tenta outro modelo automaticamente.

## Adicionando documentos

Coloque arquivos `.md`, `.txt` ou `.pdf` em `documentos/` e rode `python ingest.py`
(ou o botão "Reindexar" na interface). Se o nome do arquivo contiver um código de disciplina
(ex.: `IAA302_plano.pdf`), ele recebe esse metadado; caso contrário, é tratado como institucional.
