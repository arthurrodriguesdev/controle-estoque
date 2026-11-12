"""Testes automatizados (unitários + integração das rotas). Rodar: python -m unittest -v"""
import os, sqlite3, unittest
import models
models.DB_PATH = os.path.join(models.PASTA, "teste.db")
import app as appmod


def banco_limpo():
    if os.path.exists(models.DB_PATH):
        os.remove(models.DB_PATH)
    models.criar_banco()


def novo(nome, cat, preco, qtd, minimo, codigo=""):
    dados, erro = models.validar_produto(nome, cat, preco, qtd, minimo, codigo)
    assert erro is None, erro
    models.criar_produto(dados)
    return models.listar_produtos(nome)[0]["id"]


class TesteModel(unittest.TestCase):
    def setUp(self):
        banco_limpo()

    def test_login_valido_e_invalido(self):
        self.assertIsNotNone(models.autenticar("admin", "admin123"))
        self.assertIsNone(models.autenticar("admin", "errada"))

    def test_validacao_produto(self):
        dados, erro = models.validar_produto("", "", 1, 1, 1)
        self.assertIn("Nome, Categoria", erro)                       # diz quais campos faltam
        self.assertIsNotNone(models.validar_produto("A", "B", "abc", 1, 1)[1])
        self.assertIsNotNone(models.validar_produto("A", "B", -1, 1, 1)[1])
        self.assertIsNone(models.validar_produto("A", "B", "9,90", 1, 1)[1])
        self.assertEqual(models.validar_produto("A", "B", "1.234,50", 1, 1)[0][3], 1234.5)
        self.assertEqual(models.validar_produto("A", "B", "24.9", 1, 1)[0][3], 24.9)

    def test_codigo_de_barras_unico(self):
        pid = novo("Arroz", "Mercearia", 20, 10, 2, "7891000100103")
        _, erro = models.validar_produto("Feijão", "Mercearia", 8, 5, 2, "7891000100103")
        self.assertIn("já está em uso", erro)
        # o próprio produto pode ser salvo de novo com o mesmo código (edição)
        self.assertIsNone(models.validar_produto("Arroz", "Mercearia", 21, 10, 2, "7891000100103", produto_id=pid)[1])

    def test_busca_filtro_e_ordenacao(self):
        novo("Arroz", "Mercearia", 20, 30, 2, "111")
        novo("Detergente", "Limpeza", 3, 5, 2)
        novo("Feijão", "Mercearia", 8, 12, 2)
        self.assertEqual(models.listar_produtos("111")[0]["nome"], "Arroz")            # busca por código
        self.assertEqual(len(models.listar_produtos(categoria="Mercearia")), 2)        # filtro por categoria
        nomes = [p["nome"] for p in models.listar_produtos(ordem="qtd_asc")]
        self.assertEqual(nomes, ["Detergente", "Feijão", "Arroz"])                       # ordenação por quantidade
        self.assertEqual(models.listar_categorias(), ["Limpeza", "Mercearia"])

    def test_situacao_do_estoque(self):
        p = lambda q, m: {"quantidade": q, "estoque_minimo": m}
        self.assertEqual(models.situacao(p(0, 5)), "zerado")
        self.assertEqual(models.situacao(p(5, 5)), "baixo")
        self.assertEqual(models.situacao(p(7, 5)), "atencao")
        self.assertEqual(models.situacao(p(20, 5)), "ok")

    def test_formato_real(self):
        self.assertEqual(appmod.formato_real(1234.5), "1.234,50")

    def test_entrada_saida_e_estoque_insuficiente(self):
        pid = novo("Caneta", "Papelaria", 2.5, 10, 3)
        self.assertIsNone(models.movimentar(pid, "ENTRADA", 5, 1))
        self.assertEqual(models.obter_produto(pid)["quantidade"], 15)
        self.assertIsNone(models.movimentar(pid, "SAIDA", 15, 1))
        self.assertIn("insuficiente", models.movimentar(pid, "SAIDA", 1, 1))
        self.assertEqual(models.obter_produto(pid)["quantidade"], 0)

    def test_exclusao_mantem_historico(self):
        pid = novo("Caderno", "Papelaria", 10, 5, 1)
        models.movimentar(pid, "SAIDA", 2, 1)
        models.excluir_produto(pid)
        self.assertEqual(len(models.listar_produtos()), 0)
        self.assertEqual(len(models.listar_movimentacoes()), 1)
        self.assertIsNotNone(models.movimentar(pid, "ENTRADA", 1, 1))

    def test_estoque_baixo_e_resumo(self):
        novo("Lápis", "Papelaria", 1, 2, 5)
        self.assertEqual(len(models.produtos_estoque_baixo()), 1)
        self.assertEqual(models.resumo()["estoque_baixo"], 1)

    def test_migracao_banco_antigo(self):
        os.remove(models.DB_PATH)
        con = sqlite3.connect(models.DB_PATH)
        con.execute("CREATE TABLE produto (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, categoria TEXT, "
                    "preco REAL, quantidade INTEGER, estoque_minimo INTEGER)")
        con.execute("INSERT INTO produto (nome, categoria, preco, quantidade, estoque_minimo) VALUES ('Velho','X',1,1,1)")
        con.commit(); con.close()
        models.criar_banco()
        with models.conectar() as c:
            cols = [r["name"] for r in c.execute("PRAGMA table_info(produto)")]
        self.assertIn("ativo", cols); self.assertIn("codigo", cols)
        self.assertEqual(models.listar_produtos()[0]["nome"], "Velho")                  # dado antigo preservado


class TesteRotas(unittest.TestCase):
    def setUp(self):
        banco_limpo()
        self.c = appmod.app.test_client()

    def logar(self):
        return self.c.post("/login", data={"login": "admin", "senha": "admin123"}, follow_redirects=True)

    def test_rota_protegida(self):
        self.assertEqual(self.c.get("/produtos").status_code, 302)

    def test_login_invalido_mostra_mensagem_e_destaca_campos(self):
        r = self.c.post("/login", data={"login": "admin", "senha": "x"})
        html = r.data.decode()
        self.assertIn("Usuário ou senha incorretos", html)
        self.assertIn('class="invalido"', html)
        self.assertIn('value="admin"', html)                                            # mantém o usuário digitado
        self.assertIn("Mostrar senha", html)

    def test_fluxo_completo_com_alerta(self):
        self.assertIn("Painel", self.logar().data.decode())
        r = self.c.post("/produtos/novo", data={"nome": "Café", "categoria": "Mercearia", "preco": "12,50",
                                                 "quantidade": "10", "minimo": "3", "codigo": "789"},
                        follow_redirects=True).data.decode()
        self.assertIn("cadastrado com sucesso", r)
        r = self.c.post("/movimentacoes", data={"produto_id": "1", "tipo": "SAIDA", "quantidade": "99"},
                        follow_redirects=True).data.decode()
        self.assertIn("Estoque insuficiente", r)
        r = self.c.post("/movimentacoes", data={"produto_id": "1", "tipo": "SAIDA", "quantidade": "8"},
                        follow_redirects=True).data.decode()
        self.assertIn("ficou com estoque baixo", r)                                     # alerta automático
        self.assertIn("Café", self.c.get("/produtos?ordem=qtd_asc&categoria=Mercearia").data.decode())

    def test_relatorio_csv(self):
        self.logar()
        self.c.post("/produtos/novo", data={"nome": "Arroz", "categoria": "Mercearia", "preco": "24,90",
                                             "quantidade": "2", "minimo": "5", "codigo": ""})
        r = self.c.get("/relatorio.csv")
        texto = r.data.decode("utf-8-sig")
        self.assertEqual(r.mimetype, "text/csv")
        self.assertIn("Arroz;Mercearia;24,90;2;5;49,80;Estoque baixo", texto)


if __name__ == "__main__":
    unittest.main()
