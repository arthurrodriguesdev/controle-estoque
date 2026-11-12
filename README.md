# Sistema de Controle de Estoque (PIT-II)

Sistema web para pequenos comércios controlarem produtos, entradas e saídas e receberem alerta de estoque baixo.
Desenvolvido em Python + Flask, banco SQLite, front-end em HTML/CSS, no padrão **MVC**.

## Como executar
```
pip install -r requirements.txt
python app.py
```
Acesse http://127.0.0.1:5000. Login: `admin` / Senha: `admin123`.

## Testes
```
python -m unittest -v
```

## Estrutura MVC
| Camada | Arquivos |
|---|---|
| Model | `models.py`, `banco.sql` |
| View | `templates/`, `static/style.css` |
| Controller | `app.py` |

Autor: Arthur Rodrigues Borges (RGM 40673278)
