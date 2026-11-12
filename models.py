"""MODEL - acesso ao banco de dados e regras de negócio (validação e armazenamento)."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

PASTA = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PASTA, "estoque.db")

# Ordenações permitidas na listagem (lista fechada evita SQL injection no ORDER BY)
ORDENACOES = {
    "nome": "nome COLLATE NOCASE",
    "qtd_asc": "quantidade ASC, nome COLLATE NOCASE",
    "qtd_desc": "quantidade DESC, nome COLLATE NOCASE",
    "preco": "preco DESC, nome COLLATE NOCASE",
}


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
        # Migração: bancos criados em versões anteriores ganham as colunas novas
        colunas = [c["name"] for c in con.execute("PRAGMA table_info(produto)")]
        if "ativo" not in colunas:
            con.execute("ALTER TABLE produto ADD COLUMN ativo INTEGER NOT NULL DEFAULT 1")
        if "codigo" not in colunas:
            con.execute("ALTER TABLE produto ADD COLUMN codigo TEXT")
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
def validar_produto(nome, categoria, preco, quantidade, minimo, codigo="", produto_id=None):
    """Regra de negócio: devolve (dados_limpos, erro).
    dados_limpos = (codigo, nome, categoria, preco, quantidade, minimo)"""
    nome, categoria, codigo = nome.strip(), categoria.strip(), (codigo or "").strip()
    faltando = [campo for campo, valor in (("Nome", nome), ("Categoria", categoria)) if not valor]
    if faltando:
        return None, "Preencha o(s) campo(s) obrigatório(s): " + ", ".join(faltando) + "."
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
    if codigo:
        with conectar() as con:
            repetido = con.execute(
                "SELECT nome FROM produto WHERE codigo = ? AND ativo = 1 AND id != ?",
                (codigo, produto_id or 0),
            ).fetchone()
        if repetido:
            return None, f"O código {codigo} já está em uso no produto \"{repetido['nome']}\"."
    return (codigo or None, nome, categoria, preco, quantidade, minimo), None


def listar_produtos(busca="", categoria="", ordem="nome"):
    """Lista produtos ativos, com busca (nome, categoria ou código), filtro por categoria e ordenação."""
    sql = ("SELECT * FROM produto WHERE ativo = 1 "
           "AND (nome LIKE ? OR categoria LIKE ? OR IFNULL(codigo,'') LIKE ?)")
    params = [f"%{busca}%"] * 3
    if categoria:
        sql += " AND categoria = ?"
        params.append(categoria)
    sql += " ORDER BY " + ORDENACOES.get(ordem, ORDENACOES["nome"])
    with conectar() as con:
        return con.execute(sql, params).fetchall()


def listar_categorias():
    with conectar() as con:
        return [r["categoria"] for r in con.execute(
            "SELECT DISTINCT categoria FROM produto WHERE ativo = 1 ORDER BY categoria COLLATE NOCASE")]


def obter_produto(pid):
    """Devolve o produto ativo com esse id (ou None)."""
    with conectar() as con:
        return con.execute("SELECT * FROM produto WHERE id = ? AND ativo = 1", (pid,)).fetchone()


def criar_produto(dados):
    with conectar() as con:
        con.execute(
            "INSERT INTO produto (codigo, nome, categoria, preco, quantidade, estoque_minimo) VALUES (?,?,?,?,?,?)",
            dados,
        )


def atualizar_produto(pid, dados):
    with conectar() as con:
        con.execute(
            "UPDATE produto SET codigo=?, nome=?, categoria=?, preco=?, quantidade=?, estoque_minimo=? WHERE id=?",
            (*dados, pid),
        )


def excluir_produto(pid):
    """Exclusão lógica: o produto some das listas, mas o histórico de movimentações é mantido."""
    with conectar() as con:
        con.execute("UPDATE produto SET ativo = 0 WHERE id = ?", (pid,))


def situacao(produto):
    """Classifica o estoque: 'zerado', 'baixo' (<= mínimo), 'atencao' (até 50% acima do mínimo) ou 'ok'."""
    q, m = produto["quantidade"], produto["estoque_minimo"]
    if q == 0:
        return "zerado"
    if q <= m:
        return "baixo"
    if q <= m * 1.5:
        return "atencao"
    return "ok"


def produtos_estoque_baixo():
    with conectar() as con:
        return con.execute(
            "SELECT * FROM produto WHERE ativo = 1 AND quantidade <= estoque_minimo ORDER BY quantidade"
        ).fetchall()


def resumo():
    with conectar() as con:
        r = con.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(quantidade*preco),0) AS valor, "
            "COALESCE(SUM(quantidade <= estoque_minimo),0) AS baixos FROM produto WHERE ativo = 1"
        ).fetchone()
    return {"total_produtos": r["total"], "valor_estoque": r["valor"], "estoque_baixo": r["baixos"]}


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
            """SELECT m.*, p.nome AS produto, p.ativo AS produto_ativo, u.nome AS usuario
               FROM movimentacao m
               JOIN produto p ON p.id = m.produto_id
               JOIN usuario u ON u.id = m.usuario_id
               ORDER BY m.id DESC LIMIT 100"""
        ).fetchall()
