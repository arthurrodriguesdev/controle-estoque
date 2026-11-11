"""MODEL - acesso ao banco de dados e regras de negócio (validação e armazenamento)."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

PASTA = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PASTA, "estoque.db")


@contextmanager
def conectar():
    """Abre a conexão, confirma (commit) as alterações e SEMPRE fecha a conexão."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def criar_banco():
    """Cria as tabelas (banco.sql) e o usuário admin padrão na primeira execução."""
    with conectar() as con:
        with open(os.path.join(PASTA, "banco.sql"), encoding="utf-8") as f:
            con.executescript(f.read())
        if not con.execute("SELECT 1 FROM usuario").fetchone():
            con.execute(
                "INSERT INTO usuario (nome, login, senha) VALUES (?,?,?)",
                ("Administrador", "admin", generate_password_hash("admin123")),
            )


# ---------- Usuário ----------
def autenticar(login, senha):
    with conectar() as con:
        u = con.execute("SELECT * FROM usuario WHERE login = ?", (login,)).fetchone()
    if u and check_password_hash(u["senha"], senha):
        return u
    return None


# ---------- Produto ----------
def validar_produto(nome, categoria, preco, quantidade, minimo):
    """Regra de negócio: devolve (dados_limpos, erro)."""
    nome, categoria = nome.strip(), categoria.strip()
    if not nome or not categoria:
        return None, "Nome e categoria são obrigatórios."
    try:
        texto = str(preco).strip()
        if "," in texto:                      # formato brasileiro: 1.234,50
            texto = texto.replace(".", "").replace(",", ".")
        preco = float(texto)
        quantidade = int(quantidade)
        minimo = int(minimo)
    except ValueError:
        return None, "Preço, quantidade e estoque mínimo devem ser números."
    if preco < 0 or quantidade < 0 or minimo < 0:
        return None, "Valores não podem ser negativos."
    return (nome, categoria, preco, quantidade, minimo), None


def listar_produtos(busca=""):
    with conectar() as con:
        return con.execute(
            "SELECT * FROM produto WHERE nome LIKE ? OR categoria LIKE ? ORDER BY nome",
            (f"%{busca}%", f"%{busca}%"),
        ).fetchall()


def obter_produto(pid):
    with conectar() as con:
        return con.execute("SELECT * FROM produto WHERE id = ?", (pid,)).fetchone()


def criar_produto(dados):
    with conectar() as con:
        con.execute(
            "INSERT INTO produto (nome, categoria, preco, quantidade, estoque_minimo) VALUES (?,?,?,?,?)",
            dados,
        )


def atualizar_produto(pid, dados):
    with conectar() as con:
        con.execute(
            "UPDATE produto SET nome=?, categoria=?, preco=?, quantidade=?, estoque_minimo=? WHERE id=?",
            (*dados, pid),
        )


def excluir_produto(pid):
    with conectar() as con:
        con.execute("DELETE FROM produto WHERE id = ?", (pid,))


def produtos_estoque_baixo():
    with conectar() as con:
        return con.execute(
            "SELECT * FROM produto WHERE quantidade <= estoque_minimo ORDER BY quantidade"
        ).fetchall()


def resumo():
    with conectar() as con:
        r = con.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(quantidade*preco),0) AS valor FROM produto"
        ).fetchone()
    return {"total_produtos": r["total"], "valor_estoque": r["valor"]}


# ---------- Movimentação ----------
def movimentar(produto_id, tipo, quantidade, usuario_id):
    """Registra entrada/saída e atualiza o estoque. Devolve mensagem de erro ou None."""
    try:
        quantidade = int(quantidade)
    except ValueError:
        return "Quantidade inválida."
    if quantidade <= 0:
        return "A quantidade deve ser maior que zero."
    if tipo not in ("ENTRADA", "SAIDA"):
        return "Tipo de movimentação inválido."
    produto = obter_produto(produto_id)
    if not produto:
        return "Produto não encontrado."
    if tipo == "SAIDA" and quantidade > produto["quantidade"]:
        return f"Estoque insuficiente. Disponível: {produto['quantidade']}."
    delta = quantidade if tipo == "ENTRADA" else -quantidade
    with conectar() as con:
        con.execute("UPDATE produto SET quantidade = quantidade + ? WHERE id = ?", (delta, produto_id))
        con.execute(
            "INSERT INTO movimentacao (produto_id, tipo, quantidade, data_hora, usuario_id) VALUES (?,?,?,?,?)",
            (produto_id, tipo, quantidade, datetime.now().strftime("%d/%m/%Y %H:%M"), usuario_id),
        )
    return None


def listar_movimentacoes():
    with conectar() as con:
        return con.execute(
            """SELECT m.*, p.nome AS produto, u.nome AS usuario
               FROM movimentacao m
               JOIN produto p ON p.id = m.produto_id
               JOIN usuario u ON u.id = m.usuario_id
               ORDER BY m.id DESC LIMIT 100"""
        ).fetchall()
