"""Testes automatizados (unitários + integração das rotas). Rodar: python -m unittest -v"""
import os, unittest
import models
models.DB_PATH = os.path.join(models.PASTA, "teste.db")
import app as appmod


def banco_limpo():
    if os.path.exists(models.DB_PATH):
        os.remove(models.DB_PATH)
    models.criar_banco()


class TesteModel(unittest.TestCase):
    def setUp(self):
        banco_limpo()

    def test_login_valido_e_invalido(self):
        self.assertIsNotNone(models.autenticar("admin", "admin123"))
        self.assertIsNone(models.autenticar("admin", "errada"))

    def test_validacao_produto(self):
        self.assertIsNotNone(models.validar_produto("", "x", 1, 1, 1)[1])
        self.assertIsNotNone(models.validar_produto("A", "B", "abc", 1, 1)[1])
        self.assertIsNotNone(models.validar_produto("A", "B", -1, 1, 1)[1])
        self.assertIsNone(models.validar_produto("A", "B", "9,90", 1, 1)[1])
        self.assertEqual(models.validar_produto("A", "B", "1.234,50", 1, 1)[0][2], 1234.5)
        self.assertEqual(models.validar_produto("A", "B", "24.9", 1, 1)[0][2], 24.9)

    def test_entrada_saida_e_estoque_insuficiente(self):
        models.criar_produto(("Caneta", "Papelaria", 2.5, 10, 3))
        pid = models.listar_produtos()[0]["id"]
        self.assertIsNone(models.movimentar(pid, "ENTRADA", 5, 1))
        self.assertEqual(models.obter_produto(pid)["quantidade"], 15)
        self.assertIsNone(models.movimentar(pid, "SAIDA", 15, 1))
        self.assertIn("insuficiente", models.movimentar(pid, "SAIDA", 1, 1))
        self.assertEqual(models.obter_produto(pid)["quantidade"], 0)

    def test_formato_real(self):
        self.assertEqual(appmod.formato_real(1234.5), "1.234,50")

    def test_estoque_baixo(self):
        models.criar_produto(("Lápis", "Papelaria", 1, 2, 5))
        self.assertEqual(len(models.produtos_estoque_baixo()), 1)


class TesteRotas(unittest.TestCase):
    def setUp(self):
        banco_limpo()
        self.c = appmod.app.test_client()

    def logar(self):
        return self.c.post("/login", data={"login": "admin", "senha": "admin123"}, follow_redirects=True)

    def test_rota_protegida(self):
        self.assertEqual(self.c.get("/produtos").status_code, 302)

    def test_fluxo_completo(self):
        self.assertIn(b"Painel", self.logar().data)
        r = self.c.post("/produtos/novo", data={"nome": "Café", "categoria": "Mercearia", "preco": "12,50",
                                                 "quantidade": "10", "minimo": "3"}, follow_redirects=True)
        self.assertIn(b"cadastrado com sucesso", r.data)
        r = self.c.post("/movimentacoes", data={"produto_id": "1", "tipo": "SAIDA", "quantidade": "99"}, follow_redirects=True)
        self.assertIn(b"Estoque insuficiente", r.data)
        r = self.c.post("/movimentacoes", data={"produto_id": "1", "tipo": "SAIDA", "quantidade": "4"}, follow_redirects=True)
        self.assertIn(b"Movimenta", r.data)
        self.assertIn(b"Caf", self.c.get("/produtos").data)


if __name__ == "__main__":
    unittest.main()
