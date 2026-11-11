# Manual de Uso - Sistema de Controle de Estoque

## Para que serve
Ajuda pequenos comércios a controlar produtos, registrar entradas e saídas e ser avisados quando o estoque está acabando.

## Como instalar e executar
1. Instale o Python 3 (python.org). No Windows, marque "Add Python to PATH" na instalação.
2. Abra o terminal na pasta do projeto e execute:
   ```
   pip install flask
   python app.py
   ```
3. Abra o navegador em **http://127.0.0.1:5000**
4. Login: **admin** | Senha: **admin123**

## Telas
- **Login:** só entra quem tem usuário e senha.
- **Painel:** total de produtos, valor total em estoque e lista de produtos com estoque baixo.
- **Produtos:** lista, busca por nome/categoria, cadastro (+ Novo), edição e exclusão.
- **Movimentações:** registra ENTRADA (compra/reposição) ou SAÍDA (venda). O estoque é atualizado automaticamente e o histórico mostra data, hora e usuário.
- **Sair:** encerra a sessão.

## Regras do sistema
- Só usuários logados acessam as telas.
- Nome e categoria são obrigatórios; preço, quantidade e estoque mínimo não podem ser negativos.
- Não é possível dar saída maior do que o estoque disponível.
- Produto com quantidade menor ou igual ao estoque mínimo aparece em vermelho e no painel.

## Testes automatizados
`python -m unittest -v` (7 testes).

## Estrutura (padrão MVC)
- **Model:** `models.py` + `banco.sql` (banco e regras)
- **View:** pasta `templates/` + `static/style.css` (HTML/CSS)
- **Controller:** `app.py` (rotas)
