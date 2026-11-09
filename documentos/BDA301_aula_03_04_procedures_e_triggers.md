# Aulas 3 e 4 — Stored Procedures e Triggers (BDA301)

## Funções x Procedures

No PostgreSQL, uma **função** (`CREATE FUNCTION`) sempre retorna um valor e pode ser usada dentro
de um `SELECT`. Uma **procedure** (`CREATE PROCEDURE`, disponível desde o PostgreSQL 11) é executada
com o comando `CALL` e pode controlar transações com `COMMIT` e `ROLLBACK` dentro do corpo.

Parâmetros podem ser:

- `IN`: entrada (padrão).
- `OUT`: saída (em procedures, permitido a partir do PostgreSQL 14).
- `INOUT`: entrada e saída; o valor final é devolvido como resultado do `CALL`.

Exemplo:

```sql
CREATE PROCEDURE sp_calcular_media(p_ra VARCHAR, p_codigo VARCHAR, INOUT p_media NUMERIC DEFAULT NULL)
LANGUAGE plpgsql AS $$
BEGIN
  SELECT SUM(valor * peso) / SUM(peso) INTO p_media FROM notas ...;
END; $$;

CALL sp_calcular_media('2026001', 'BDA301');
```

Vantagens das procedures: reaproveitamento da regra de negócio, menos tráfego de rede,
segurança (o usuário recebe permissão de `EXECUTE` sem acessar as tabelas diretamente).

## Triggers

Um **trigger** executa automaticamente uma função quando ocorre um evento (`INSERT`, `UPDATE`,
`DELETE` ou `TRUNCATE`) em uma tabela.

- **BEFORE**: executa antes da gravação; pode alterar `NEW` ou cancelar a operação com `RAISE EXCEPTION`.
  Usado para validação e normalização de dados.
- **AFTER**: executa depois da gravação; usado para auditoria, logs e atualizações em outras tabelas.
- **FOR EACH ROW**: executa uma vez por linha afetada; **FOR EACH STATEMENT**: uma vez por comando.
- `NEW` contém a linha nova (INSERT/UPDATE); `OLD` contém a linha antiga (UPDATE/DELETE).
- `TG_OP` informa a operação que disparou o trigger.

Exemplo de auditoria de nota:

```sql
CREATE FUNCTION trg_fn_log() RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO log_alteracao_notas(nota_id, valor_antigo, valor_novo) VALUES (OLD.id, OLD.valor, NEW.valor);
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_log AFTER UPDATE ON notas FOR EACH ROW EXECUTE FUNCTION trg_fn_log();
```

Cuidados: evitar triggers em cascata infinita, manter a lógica curta e documentar os efeitos colaterais.
