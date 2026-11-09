CREATE SCHEMA smartcampus;
SET search_path TO smartcampus;

-- 1. TABELAS

CREATE TABLE alunos (
    id          SERIAL PRIMARY KEY,
    ra          VARCHAR(10)  NOT NULL UNIQUE,          -- Registro Acadêmico
    nome        VARCHAR(120) NOT NULL,
    email       VARCHAR(120) NOT NULL UNIQUE,
    curso       VARCHAR(80)  NOT NULL,
    criado_em   TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE disciplinas (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(10)  NOT NULL UNIQUE,
    nome          VARCHAR(120) NOT NULL,
    professor     VARCHAR(120) NOT NULL,
    carga_horaria INT          NOT NULL CHECK (carga_horaria > 0),
    semestre      VARCHAR(7)   NOT NULL                  -- ex.: 2026.2
);

CREATE TABLE matriculas (
    id            SERIAL PRIMARY KEY,
    aluno_id      INT NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    disciplina_id INT NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    semestre      VARCHAR(7)   NOT NULL,
    frequencia    NUMERIC(5,2) NOT NULL DEFAULT 100 CHECK (frequencia BETWEEN 0 AND 100),
    media         NUMERIC(4,2),                         -- mantida pelos triggers
    situacao      VARCHAR(20)  NOT NULL DEFAULT 'Em curso',
    UNIQUE (aluno_id, disciplina_id, semestre)
);

CREATE TABLE notas (
    id            SERIAL PRIMARY KEY,
    matricula_id  INT NOT NULL REFERENCES matriculas(id) ON DELETE CASCADE,
    avaliacao     VARCHAR(20)  NOT NULL CHECK (avaliacao IN ('P1', 'P2', 'TRABALHO')),
    peso          NUMERIC(3,2) NOT NULL CHECK (peso > 0 AND peso <= 1),
    valor         NUMERIC(4,2) NOT NULL,
    lancado_em    TIMESTAMP    NOT NULL DEFAULT now(),
    UNIQUE (matricula_id, avaliacao)
);

CREATE TABLE chamados (
    id             SERIAL PRIMARY KEY,
    aluno_id       INT NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    disciplina_id  INT REFERENCES disciplinas(id),
    assunto        VARCHAR(150) NOT NULL,
    descricao      TEXT         NOT NULL,
    origem         VARCHAR(10)  NOT NULL DEFAULT 'aluno' CHECK (origem IN ('aluno', 'sistema')),
    status         VARCHAR(15)  NOT NULL DEFAULT 'aberto'
                   CHECK (status IN ('aberto', 'em andamento', 'respondido', 'fechado')),
    resposta       TEXT,
    criado_em      TIMESTAMP    NOT NULL DEFAULT now(),
    respondido_em  TIMESTAMP
);

CREATE TABLE log_alteracao_notas (
    id            SERIAL PRIMARY KEY,
    nota_id       INT          NOT NULL,
    matricula_id  INT          NOT NULL,
    avaliacao     VARCHAR(20)  NOT NULL,
    valor_antigo  NUMERIC(4,2),
    valor_novo    NUMERIC(4,2),
    operacao      VARCHAR(10)  NOT NULL,
    usuario_db    VARCHAR(60)  NOT NULL DEFAULT current_user,
    alterado_em   TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE alertas (
    id            SERIAL PRIMARY KEY,
    matricula_id  INT NOT NULL REFERENCES matriculas(id) ON DELETE CASCADE,
    tipo          VARCHAR(30)  NOT NULL,              -- MEDIA_BAIXA, FREQUENCIA_BAIXA
    mensagem      TEXT         NOT NULL,
    valor         NUMERIC(5,2),
    resolvido     BOOLEAN      NOT NULL DEFAULT FALSE,
    criado_em     TIMESTAMP    NOT NULL DEFAULT now()
);

-- 2. FUNÇÕES AUXILIARES

CREATE OR REPLACE FUNCTION fn_media_ponderada(p_matricula_id INT)
RETURNS NUMERIC(4,2) LANGUAGE sql STABLE AS $$
    SELECT ROUND(SUM(valor * peso) / NULLIF(SUM(peso), 0), 2)
      FROM notas
     WHERE matricula_id = p_matricula_id;
$$;

CREATE OR REPLACE FUNCTION fn_situacao(p_matricula_id INT)
RETURNS VARCHAR LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_qtd   INT;
    v_media NUMERIC(4,2);
    v_freq  NUMERIC(5,2);
BEGIN
    SELECT COUNT(*) INTO v_qtd FROM notas WHERE matricula_id = p_matricula_id;
    SELECT frequencia INTO v_freq FROM matriculas WHERE id = p_matricula_id;
    v_media := fn_media_ponderada(p_matricula_id);

    IF v_freq < 75 THEN
        RETURN 'Reprovado por falta';
    ELSIF v_qtd < 3 THEN
        RETURN 'Em curso';
    ELSIF v_media >= 6 THEN
        RETURN 'Aprovado';
    ELSIF v_media >= 4 THEN
        RETURN 'Exame final';
    ELSE
        RETURN 'Reprovado';
    END IF;
END;
$$;

-- 3. PROCEDURES

-- 3.1 Calcula (e grava) a média de um aluno em uma disciplina

CREATE OR REPLACE PROCEDURE sp_calcular_media(
    p_ra              VARCHAR,
    p_codigo          VARCHAR,
    INOUT p_media     NUMERIC DEFAULT NULL,
    INOUT p_situacao  VARCHAR DEFAULT NULL
) LANGUAGE plpgsql AS $$
DECLARE
    v_matricula_id INT;
BEGIN
    SELECT m.id INTO v_matricula_id
      FROM matriculas m
      JOIN alunos a      ON a.id = m.aluno_id
      JOIN disciplinas d ON d.id = m.disciplina_id
     WHERE a.ra = p_ra AND d.codigo = p_codigo
     ORDER BY m.semestre DESC
     LIMIT 1;

    IF v_matricula_id IS NULL THEN
        RAISE EXCEPTION 'Aluno % não está matriculado na disciplina %', p_ra, p_codigo;
    END IF;

    p_media    := fn_media_ponderada(v_matricula_id);
    p_situacao := fn_situacao(v_matricula_id);

    UPDATE matriculas
       SET media = p_media, situacao = p_situacao
     WHERE id = v_matricula_id;
END;
$$;

-- 3.2 Gera o boletim completo do aluno em JSON (disciplinas, notas, média, situação)

CREATE OR REPLACE PROCEDURE sp_gerar_boletim(
    p_ra            VARCHAR,
    INOUT p_boletim JSONB DEFAULT NULL
) LANGUAGE plpgsql AS $$
DECLARE
    v_aluno alunos%ROWTYPE;
BEGIN
    SELECT * INTO v_aluno FROM alunos WHERE ra = p_ra;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Aluno com RA % não encontrado', p_ra;
    END IF;

    UPDATE matriculas m
       SET media = fn_media_ponderada(m.id), situacao = fn_situacao(m.id)
     WHERE m.aluno_id = v_aluno.id;

    SELECT jsonb_build_object(
        'ra', v_aluno.ra,
        'aluno', v_aluno.nome,
        'curso', v_aluno.curso,
        'gerado_em', to_char(now(), 'DD/MM/YYYY HH24:MI'),
        'disciplinas', COALESCE(jsonb_agg(
            jsonb_build_object(
                'codigo', d.codigo,
                'disciplina', d.nome,
                'professor', d.professor,
                'semestre', m.semestre,
                'frequencia', m.frequencia,
                'notas', (SELECT COALESCE(jsonb_object_agg(n.avaliacao, n.valor), '{}'::jsonb)
                            FROM notas n WHERE n.matricula_id = m.id),
                'media', m.media,
                'situacao', m.situacao
            ) ORDER BY d.codigo), '[]'::jsonb)
    ) INTO p_boletim
      FROM matriculas m
      JOIN disciplinas d ON d.id = m.disciplina_id
     WHERE m.aluno_id = v_aluno.id;
END;
$$;

-- 3.3 Lança ou corrige uma nota (os triggers fazem o resto)

CREATE OR REPLACE PROCEDURE sp_lancar_nota(
    p_ra        VARCHAR,
    p_codigo    VARCHAR,
    p_avaliacao VARCHAR,
    p_valor     NUMERIC
) LANGUAGE plpgsql AS $$
DECLARE
    v_matricula_id INT;
    v_peso NUMERIC(3,2);
BEGIN
    SELECT m.id INTO v_matricula_id
      FROM matriculas m
      JOIN alunos a      ON a.id = m.aluno_id
      JOIN disciplinas d ON d.id = m.disciplina_id
     WHERE a.ra = p_ra AND d.codigo = p_codigo
     ORDER BY m.semestre DESC LIMIT 1;

    IF v_matricula_id IS NULL THEN
        RAISE EXCEPTION 'Matrícula não encontrada para RA % em %', p_ra, p_codigo;
    END IF;

    v_peso := CASE upper(p_avaliacao) WHEN 'TRABALHO' THEN 0.30 ELSE 0.35 END;

    INSERT INTO notas (matricula_id, avaliacao, peso, valor)
    VALUES (v_matricula_id, upper(p_avaliacao), v_peso, p_valor)
    ON CONFLICT (matricula_id, avaliacao)
    DO UPDATE SET valor = EXCLUDED.valor, lancado_em = now();
END;
$$;

-- 3.4 Abre um chamado/dúvida (usado pelo chatbot)
CREATE OR REPLACE PROCEDURE sp_abrir_chamado(
    p_ra        VARCHAR,
    p_codigo    VARCHAR,          -- pode ser NULL
    p_assunto   VARCHAR,
    p_descricao TEXT,
    INOUT p_chamado_id INT DEFAULT NULL
) LANGUAGE plpgsql AS $$
DECLARE
    v_aluno_id INT;
    v_disc_id  INT;
BEGIN
    SELECT id INTO v_aluno_id FROM alunos WHERE ra = p_ra;
    IF v_aluno_id IS NULL THEN
        RAISE EXCEPTION 'Aluno com RA % não encontrado', p_ra;
    END IF;
    IF p_codigo IS NOT NULL THEN
        SELECT id INTO v_disc_id FROM disciplinas WHERE codigo = upper(p_codigo);
    END IF;

    INSERT INTO chamados (aluno_id, disciplina_id, assunto, descricao, origem)
    VALUES (v_aluno_id, v_disc_id, p_assunto, p_descricao, 'aluno')
    RETURNING id INTO p_chamado_id;
END;
$$;

-- 4. TRIGGERS

-- 4.1 Valida a nota antes de gravar (0 a 10, uma casa de arredondamento)
CREATE OR REPLACE FUNCTION trg_fn_validar_nota()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.valor < 0 OR NEW.valor > 10 THEN
        RAISE EXCEPTION 'Nota inválida (%): deve estar entre 0 e 10', NEW.valor;
    END IF;
    NEW.valor := ROUND(NEW.valor, 1);
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validar_nota
BEFORE INSERT OR UPDATE OF valor ON notas
FOR EACH ROW EXECUTE FUNCTION trg_fn_validar_nota();

-- 4.2 Registra toda alteração/exclusão de nota (auditoria)
CREATE OR REPLACE FUNCTION trg_fn_log_alteracao_nota()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW.valor IS DISTINCT FROM OLD.valor THEN
            INSERT INTO log_alteracao_notas (nota_id, matricula_id, avaliacao, valor_antigo, valor_novo, operacao)
            VALUES (OLD.id, OLD.matricula_id, OLD.avaliacao, OLD.valor, NEW.valor, 'UPDATE');
        END IF;
        RETURN NEW;
    ELSE -- DELETE
        INSERT INTO log_alteracao_notas (nota_id, matricula_id, avaliacao, valor_antigo, valor_novo, operacao)
        VALUES (OLD.id, OLD.matricula_id, OLD.avaliacao, OLD.valor, NULL, 'DELETE');
        RETURN OLD;
    END IF;
END;
$$;

CREATE TRIGGER trg_log_alteracao_nota
AFTER UPDATE OR DELETE ON notas
FOR EACH ROW EXECUTE FUNCTION trg_fn_log_alteracao_nota();

-- 4.3 Recalcula média e situação da matrícula sempre que uma nota muda
CREATE OR REPLACE FUNCTION trg_fn_recalcular_media()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_matricula_id INT := COALESCE(NEW.matricula_id, OLD.matricula_id);
BEGIN
    UPDATE matriculas
       SET media = fn_media_ponderada(v_matricula_id),
           situacao = fn_situacao(v_matricula_id)
     WHERE id = v_matricula_id;
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_recalcular_media
AFTER INSERT OR UPDATE OR DELETE ON notas
FOR EACH ROW EXECUTE FUNCTION trg_fn_recalcular_media();

-- 4.4 Gera alerta + chamado automático quando a média fica abaixo de 6,0
CREATE OR REPLACE FUNCTION trg_fn_alerta_media_baixa()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_aluno  alunos%ROWTYPE;
    v_disc   disciplinas%ROWTYPE;
BEGIN
    IF NEW.media IS NOT NULL AND NEW.media < 6
       AND (OLD.media IS NULL OR OLD.media >= 6 OR OLD.media IS DISTINCT FROM NEW.media) THEN

        -- evita alertas duplicados: só um alerta aberto por matrícula
        IF NOT EXISTS (SELECT 1 FROM alertas
                        WHERE matricula_id = NEW.id AND tipo = 'MEDIA_BAIXA' AND NOT resolvido) THEN
            SELECT * INTO v_aluno FROM alunos WHERE id = NEW.aluno_id;
            SELECT * INTO v_disc  FROM disciplinas WHERE id = NEW.disciplina_id;

            INSERT INTO alertas (matricula_id, tipo, mensagem, valor)
            VALUES (NEW.id, 'MEDIA_BAIXA',
                    format('Média %s em %s está abaixo de 6,0. Procure a monitoria.', NEW.media, v_disc.nome),
                    NEW.media);

            INSERT INTO chamados (aluno_id, disciplina_id, assunto, descricao, origem)
            VALUES (NEW.aluno_id, NEW.disciplina_id,
                    'Alerta automático: média baixa',
                    format('O aluno %s (RA %s) está com média %s em %s. Encaminhar para monitoria/coordenação.',
                           v_aluno.nome, v_aluno.ra, NEW.media, v_disc.nome),
                    'sistema');
        ELSE
            UPDATE alertas SET valor = NEW.media,
                   mensagem = format('Média %s em %s está abaixo de 6,0. Procure a monitoria.', NEW.media,
                                     (SELECT nome FROM disciplinas WHERE id = NEW.disciplina_id))
             WHERE matricula_id = NEW.id AND tipo = 'MEDIA_BAIXA' AND NOT resolvido;
        END IF;

    ELSIF NEW.media IS NOT NULL AND NEW.media >= 6 THEN
        UPDATE alertas SET resolvido = TRUE
         WHERE matricula_id = NEW.id AND tipo = 'MEDIA_BAIXA' AND NOT resolvido;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_alerta_media_baixa
AFTER UPDATE OF media ON matriculas
FOR EACH ROW EXECUTE FUNCTION trg_fn_alerta_media_baixa();

-- 4.5 Alerta de frequência abaixo de 75%
CREATE OR REPLACE FUNCTION trg_fn_alerta_frequencia()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.frequencia < 75 AND (TG_OP = 'INSERT' OR OLD.frequencia >= 75) THEN
        INSERT INTO alertas (matricula_id, tipo, mensagem, valor)
        VALUES (NEW.id, 'FREQUENCIA_BAIXA',
                format('Frequência de %s%% está abaixo do mínimo de 75%%.', NEW.frequencia),
                NEW.frequencia);
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_alerta_frequencia
AFTER INSERT OR UPDATE OF frequencia ON matriculas
FOR EACH ROW EXECUTE FUNCTION trg_fn_alerta_frequencia();

-- 5. DADOS DE EXEMPLO

INSERT INTO alunos (ra, nome, email, curso) VALUES
 ('2026001', 'Ana Beatriz Souza',   'ana.souza@smartcampus.edu.br',   'Ciência da Computação'),
 ('2026002', 'Bruno Henrique Lima', 'bruno.lima@smartcampus.edu.br',  'Ciência da Computação'),
 ('2026003', 'Carla Mendes',        'carla.mendes@smartcampus.edu.br','Sistemas de Informação'),
 ('2026004', 'Diego Martins',       'diego.martins@smartcampus.edu.br','Sistemas de Informação');

INSERT INTO disciplinas (codigo, nome, professor, carga_horaria, semestre) VALUES
 ('BDA301', 'Banco de Dados Avançado',        'Prof.ª Helena Ribeiro', 80, '2026.2'),
 ('IAA302', 'Inteligência Artificial Aplicada','Prof. Marcos Tavares', 80, '2026.2'),
 ('ESW303', 'Engenharia de Software',          'Prof.ª Juliana Castro', 60, '2026.2');

INSERT INTO matriculas (aluno_id, disciplina_id, semestre, frequencia) VALUES
 (1, 1, '2026.2', 92), (1, 2, '2026.2', 88), (1, 3, '2026.2', 95),
 (2, 1, '2026.2', 80), (2, 2, '2026.2', 76),
 (3, 1, '2026.2', 70), (3, 3, '2026.2', 90),
 (4, 2, '2026.2', 85), (4, 3, '2026.2', 82);

-- Notas (os triggers calculam médias, situação e alertas automaticamente)
CALL sp_lancar_nota('2026001', 'BDA301', 'P1', 8.5);
CALL sp_lancar_nota('2026001', 'BDA301', 'TRABALHO', 9.0);
CALL sp_lancar_nota('2026001', 'IAA302', 'P1', 7.0);
CALL sp_lancar_nota('2026001', 'IAA302', 'P2', 6.5);
CALL sp_lancar_nota('2026001', 'IAA302', 'TRABALHO', 8.0);
CALL sp_lancar_nota('2026001', 'ESW303', 'P1', 9.5);

CALL sp_lancar_nota('2026002', 'BDA301', 'P1', 4.5);
CALL sp_lancar_nota('2026002', 'BDA301', 'TRABALHO', 6.0);
CALL sp_lancar_nota('2026002', 'IAA302', 'P1', 5.0);

CALL sp_lancar_nota('2026003', 'BDA301', 'P1', 7.5);
CALL sp_lancar_nota('2026003', 'ESW303', 'P1', 6.0);
CALL sp_lancar_nota('2026003', 'ESW303', 'P2', 7.0);
CALL sp_lancar_nota('2026003', 'ESW303', 'TRABALHO', 8.0);

CALL sp_lancar_nota('2026004', 'IAA302', 'P1', 3.0);
CALL sp_lancar_nota('2026004', 'ESW303', 'P1', 8.0);

-- Correção de nota: dispara log de alteração e recalcula média
CALL sp_lancar_nota('2026002', 'BDA301', 'P1', 5.0);

INSERT INTO chamados (aluno_id, disciplina_id, assunto, descricao, status, resposta, respondido_em) VALUES
 (1, 1, 'Dúvida sobre trigger', 'Qual a diferença entre BEFORE e AFTER?', 'respondido',
  'BEFORE pode alterar NEW antes da gravação; AFTER roda depois e é usado para auditoria.', now());

-- 6. CONSULTAS DE DEMONSTRAÇÃO (descomente para testar no psql)

-- CALL sp_calcular_media('2026001', 'BDA301');
-- CALL sp_gerar_boletim('2026002');
-- SELECT * FROM log_alteracao_notas;
-- SELECT * FROM alertas;
-- SELECT * FROM chamados ORDER BY id;
