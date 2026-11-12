"""CONTROLLER - recebe as ações do usuário, chama o Model e escolhe a View (template)."""
import csv
import io
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import models

app = Flask(__name__)
app.secret_key = "troque-esta-chave-em-producao"


@app.template_filter("brl")
def formato_real(valor):
    """Formata número no padrão brasileiro: 1234.5 -> 1.234,50"""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


app.jinja_env.globals["situacao"] = models.situacao
models.criar_banco()   # garante que o banco existe (também ao rodar em hospedagem)


def login_obrigatorio(f):
    @wraps(f)
    def interno(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return interno


@app.route("/login", methods=["GET", "POST"])
def login():
    erro = False
    if request.method == "POST":
        u = models.autenticar(request.form["login"], request.form["senha"])
        if u:
            session["usuario_id"], session["usuario_nome"] = u["id"], u["nome"]
            return redirect(url_for("painel"))
        erro = True
        flash("Usuário ou senha incorretos. Confira os dados e tente novamente.", "erro")
    return render_template("login.html", erro=erro, login_digitado=request.form.get("login", ""))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_obrigatorio
def painel():
    return render_template("painel.html", resumo=models.resumo(), baixo=models.produtos_estoque_baixo())


@app.route("/produtos")
@login_obrigatorio
def produtos():
    busca = request.args.get("busca", "")
    categoria = request.args.get("categoria", "")
    ordem = request.args.get("ordem", "nome")
    return render_template("produtos.html", produtos=models.listar_produtos(busca, categoria, ordem),
                           busca=busca, categoria=categoria, ordem=ordem,
                           categorias=models.listar_categorias())


CAMPOS = ("nome", "categoria", "preco", "quantidade", "minimo", "codigo")


@app.route("/produtos/novo", methods=["GET", "POST"])
@login_obrigatorio
def novo_produto():
    if request.method == "POST":
        dados, erro = models.validar_produto(*(request.form.get(c, "") for c in CAMPOS))
        if erro:
            flash(erro, "erro")
        else:
            models.criar_produto(dados)
            flash(f"Produto \"{dados[1]}\" cadastrado com sucesso!", "ok")
            return redirect(url_for("produtos"))
    return render_template("produto_form.html", produto=None)


@app.route("/produtos/<int:pid>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_produto(pid):
    produto = models.obter_produto(pid)
    if not produto:
        flash("Produto não encontrado.", "erro")
        return redirect(url_for("produtos"))
    if request.method == "POST":
        dados, erro = models.validar_produto(*(request.form.get(c, "") for c in CAMPOS), produto_id=pid)
        if erro:
            flash(erro, "erro")
        else:
            models.atualizar_produto(pid, dados)
            flash(f"Produto \"{dados[1]}\" atualizado!", "ok")
            return redirect(url_for("produtos"))
    return render_template("produto_form.html", produto=produto)


@app.route("/produtos/<int:pid>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_produto(pid):
    models.excluir_produto(pid)
    flash("Produto excluído. O histórico de movimentações foi mantido.", "ok")
    return redirect(url_for("produtos"))


@app.route("/movimentacoes", methods=["GET", "POST"])
@login_obrigatorio
def movimentacoes():
    if request.method == "POST":
        pid = request.form["produto_id"]
        erro = models.movimentar(pid, request.form["tipo"], request.form["quantidade"], session["usuario_id"])
        if erro:
            flash(erro, "erro")
        else:
            flash("Movimentação registrada!", "ok")
            p = models.obter_produto(pid)
            if p and p["quantidade"] <= p["estoque_minimo"]:   # alerta automático de estoque baixo
                flash(f"Atenção: \"{p['nome']}\" ficou com estoque baixo ({p['quantidade']} unidade(s); "
                      f"mínimo {p['estoque_minimo']}). Programe a reposição.", "aviso")
        return redirect(url_for("movimentacoes"))
    return render_template("movimentacoes.html", produtos=models.listar_produtos(),
                           historico=models.listar_movimentacoes())


@app.route("/relatorio.csv")
@login_obrigatorio
def relatorio():
    """Relatório de produtos em CSV (abre no Excel)."""
    rotulos = {"zerado": "Zerado", "baixo": "Estoque baixo", "atencao": "Atenção", "ok": "OK"}
    saida = io.StringIO()
    w = csv.writer(saida, delimiter=";")
    w.writerow(["Código", "Produto", "Categoria", "Preço (R$)", "Quantidade", "Estoque mínimo",
                "Valor em estoque (R$)", "Situação"])
    for p in models.listar_produtos():
        w.writerow([p["codigo"] or "", p["nome"], p["categoria"], formato_real(p["preco"]), p["quantidade"],
                    p["estoque_minimo"], formato_real(p["preco"] * p["quantidade"]), rotulos[models.situacao(p)]])
    nome = f"relatorio_estoque_{datetime.now():%Y-%m-%d}.csv"
    return Response("﻿" + saida.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={nome}"})


if __name__ == "__main__":
    app.run(debug=True)
