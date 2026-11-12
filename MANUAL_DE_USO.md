# Manual de Uso - Sistema de Controle de Estoque

## Para que serve
Ajuda pequenos comércios a controlar produtos, registrar entradas e saídas e ser avisados quando o estoque está acabando.

Endereço: https://arthurrodrigues.pythonanywhere.com
Login: **admin** | Senha: **admin123**

## Como rodar no próprio computador
1. Instale o Python 3 (python.org). No Windows, marque "Add Python to PATH".
2. No terminal, dentro da pasta do projeto:
   ```
   pip install flask
   python app.py
   ```
3. Abra http://127.0.0.1:5000

## Telas
- **Login:** informe usuário e senha. A caixa "Mostrar senha" exibe o que foi digitado. Se errar, os campos ficam em vermelho e aparece uma mensagem explicando.
- **Painel:** total de produtos, valor total em estoque, quantidade de produtos com estoque baixo e a lista desses produtos. O botão **Baixar relatório (CSV)** gera uma planilha que abre no Excel.
- **Produtos:**
  - **Buscar** por nome, categoria ou código de barras;
  - **Filtrar** por categoria;
  - **Ordenar** por nome, menor ou maior quantidade, ou maior preço;
  - **+ Novo produto**, **Editar** e **Excluir**.
  - A coluna **Situação** mostra: OK (normal), Atenção (próximo do mínimo), Estoque baixo (no mínimo ou abaixo) e Zerado.
- **Cadastro/edição de produto:** os campos com * são obrigatórios. O código de barras é opcional, mas não pode repetir.
- **Movimentações:** registre ENTRADA (reposição) ou SAÍDA (venda/uso). Se uma saída deixar o produto no estoque mínimo, aparece um aviso amarelo. O histórico mostra data, hora, tipo e usuário.

## Regras do sistema
- Só usuários logados acessam as telas.
- Nome e categoria são obrigatórios; preço, quantidade e estoque mínimo não podem ser negativos.
- Não é possível dar saída maior do que o estoque disponível.
- Código de barras não pode se repetir entre produtos.
- Ao excluir um produto, ele some das listas, mas o histórico é mantido (aparece como "(excluído)").

## Testes automatizados
`python -m unittest -v` (14 testes).
