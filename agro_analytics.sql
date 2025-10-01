-- DDL SCRIPT FINAL E DEFINITIVO PARA O AGRO_ANALYTICS
-- Garante que todas as tabelas e sequences existam e estejam formatadas corretamente.

-- 1. LIMPEZA: Tenta deletar tabelas e sequences antigas para um ambiente limpo.
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE COLHEITAS CASCADE CONSTRAINTS';
    -- Removendo PLANEJAMENTO temporariamente, pois não é usado no Python, mas mantendo a Sequence se for necessário no futuro.
    -- EXECUTE IMMEDIATE 'DROP TABLE PLANEJAMENTO CASCADE CONSTRAINTS'; 
    EXECUTE IMMEDIATE 'DROP SEQUENCE COLHEITAS_SEQ';
EXCEPTION
    WHEN OTHERS THEN
        NULL; -- Ignora erros de objeto inexistente
END;
/

-- 2. CRIAÇÃO: Cria a Tabela COLHEITAS (Registros de Colheita)
-- Inclui todas as colunas utilizadas no comando INSERT do Python.
CREATE TABLE COLHEITAS (
    ID                          NUMBER(10)      PRIMARY KEY, 
    UF                          VARCHAR2(2)     NOT NULL, -- Adicionado para resolver ORA-00904
    MES_PLANTIO                 NUMBER(2)       NOT NULL, -- Adicionado para resolver ORA-00904
    TALHAO                      VARCHAR2(50)    NOT NULL,
    MAQUINA_ID                  VARCHAR2(50)    NOT NULL,
    PRODUTIVIDADE_ESPERADA_THA  NUMBER(10, 2),
    PERDA_REGISTRADA_THA        NUMBER(10, 2),
    DATA_COLHEITA               DATE,
    PRECO_TONELADA              NUMBER(10, 2),  
    AREA_TOTAL_HA               NUMBER(10, 2)   
);

-- 3. CRIAÇÃO: Cria a SEQUENCE para gerar IDs de forma automática para a tabela COLHEITAS
-- Garante que a sequência começa em 1.
CREATE SEQUENCE COLHEITAS_SEQ
START WITH 1
INCREMENT BY 1
NOCACHE;

-- 4. Confirma a criação de forma permanente
COMMIT;
