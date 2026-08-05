# 🧾 Sistema de Recebimento de NF-e / CPD

Aplicação **full-stack** para registrar e controlar o **recebimento de notas fiscais (NF-e)** no CPD de um supermercado.
Back-end em **FastAPI** com **autenticação JWT**, banco **SQLite** (modo WAL) e empacotamento em **executável** para uso sem instalação.

> ⚠️ **Aviso sobre os dados**
> Todos os dados presentes neste repositório (planilhas, seeds, exemplos) são **fictícios** e foram
> **gerados aleatoriamente apenas para demonstração**. Os dados reais da operação em que o projeto
> foi utilizado são **confidenciais e estão protegidos** — nenhum dado real, credencial ou informação
> de terceiros foi incluído aqui.

## 🎯 O que faz
- API REST em **FastAPI** para lançar e consultar recebimentos de NF-e.
- **Autenticação JWT** + hash de senha (sem senhas em texto).
- Banco **SQLite** com `PRAGMA foreign_keys`, **modo WAL** e tabela `dim_data` (chave AAAAMMDD).
- Front-end simples em **HTML** servido pela própria API.
- Camada alternativa para **MySQL** (`cpd_mysql.py`).
- **Empacotamento em `.exe`** com PyInstaller (`build_exe.py`) para rodar nas lojas sem instalar Python.

## 🧑‍💻 Stack
`Python` · `FastAPI` · `JWT` · `SQLite` · `MySQL` · `HTML` · `PyInstaller` · `API REST`

## ▶️ Como rodar
```bash
pip install fastapi uvicorn passlib python-jose
copy .env.example .env       # defina SECRET_KEY
python main.py               # sobe a API + abre o formulário
```
> 🔐 A `SECRET_KEY` agora é lida de variável de ambiente (`.env`) — não há segredos no código.

## 📁 Estrutura
```
main.py         # API FastAPI + autenticação + rotas
database.py     # camada SQLite (WAL, FK, dim_data)
cpd_mysql.py    # camada alternativa MySQL
index.html      # formulário (front-end)
build_exe.py    # empacotamento em .exe
```

---

### 🧰 Competências demonstradas
`FastAPI` · `Autenticação JWT` · `Modelagem de Banco` · `Full-Stack` · `Empacotamento de aplicações`

### 👤 Autor
**José Vitor Santos Pinheiro** — Analista de Dados / BI / Ciência de Dados
· vytorsantt@gmail.com
