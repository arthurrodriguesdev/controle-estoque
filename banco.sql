-- Projeto físico do banco de dados (SQLite)
CREATE TABLE IF NOT EXISTS usuario (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nome    TEXT NOT NULL,
    login   TEXT NOT NULL UNIQUE,
    senha   TEXT NOT NULL            -- guardada como hash, nunca em texto puro
);

CREATE TABLE IF NOT EXISTS produto (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nome           TEXT NOT NULL,
    categoria      TEXT NOT NULL,
    preco          REAL NOT NULL CHECK (preco >= 0),
    quantidade     INTEGER NOT NULL DEFAULT 0 CHECK (quantidade >= 0),
    estoque_minimo INTEGER NOT NULL DEFAULT 5
);

CREATE TABLE IF NOT EXISTS movimentacao (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id  INTEGER NOT NULL,
    tipo        TEXT NOT NULL CHECK (tipo IN ('ENTRADA','SAIDA')),
    quantidade  INTEGER NOT NULL CHECK (quantidade > 0),
    data_hora   TEXT NOT NULL,
    usuario_id  INTEGER NOT NULL,
    FOREIGN KEY (produto_id) REFERENCES produto(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuario(id)
);
