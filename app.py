"""CONTROLLER - recebe as ações do usuário, chama o Model e escolhe a View (template)."""
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
import models

app = Flask(__name__)
app.secret_key = "troque-esta-chave-em-producao"
@app.template_filter("brl")
def formato_real(valor):
    """Formata número no padrão brasileiro: 1234.5 -> 1.234,50"""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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
    if request.method == "POST":
        u = models.autenticar(request.form["login"], request.form["senha"])
        if u:
            session["usuario_id"], session["usuario_nome"] = u["id"], u["nome"]
            return redirect(url_for("painel"))
        flash("Login ou senha inválidos.", "erro")
    return render_template("login.html")


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
    return render_template("produtos.html", produtos=models.listar_produtos(busca), busca=busca)


CAMPOS = ("nome", "categoria", "preco", "quantidade", "minimo")


@app.route("/produtos/novo", methods=["GET", "POST"])
@login_obrigatorio
def novo_produto():
    if request.method == "POST":
        dados, erro = models.validar_produto(*(request.form[c] for c in CAMPOS))
        if erro:
            flash(erro, "erro")
        else:
            models.criar_produto(dados)
            flash("Produto cadastrado com sucesso!", "ok")
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
        dados, erro = models.validar_produto(*(request.form[c] for c in CAMPOS))
        if erro:
            flash(erro, "erro")
        else:
            models.atualizar_produto(pid, dados)
            flash("Produto atualizado!", "ok")
            return redirect(url_for("produtos"))
    return render_template("produto_form.html", produto=produto)


@app.route("/produtos/<int:pid>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_produto(pid):
    models.excluir_produto(pid)
    flash("Produto excluído.", "ok")
    return redirect(url_for("produtos"))


@app.route("/movimentacoes", methods=["GET", "POST"])
@login_obrigatorio
def movimentacoes():
    if request.method == "POST":
        erro = models.movimentar(request.form["produto_id"], request.form["tipo"],
                                 request.form["quantidade"], session["usuario_id"])
        flash(erro or "Movimentação registrada!", "erro" if erro else "ok")
        return redirect(url_for("movimentacoes"))
    return render_template("movimentacoes.html", produtos=models.listar_produtos(),
                           historico=models.listar_movimentacoes())


if __name__ == "__main__":
    app.run(debug=True)
