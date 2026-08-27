# Sistema de Recebimento de NF-e / CPD

Aplicação full-stack para registrar e controlar o recebimento de notas fiscais eletrônicas (NF-e) no
Centro de Distribuição (CPD) de um supermercado. Back-end em FastAPI com autenticação JWT, banco SQLite
em modo WAL e empacotamento em executável, para que as lojas usem o sistema sem instalar um ambiente de
desenvolvimento.

> **Nota de confidencialidade:** todos os dados presentes neste repositório (planilhas, seeds,
> exemplos) são fictícios, gerados aleatoriamente apenas para demonstração. Os dados reais da operação
> são confidenciais e estão protegidos — nenhum dado real, credencial ou informação de terceiros foi
> incluído aqui.

---

## Visão Geral

O sistema cobre o registro do recebimento de mercadoria no CPD: uma API REST lança e consulta as notas,
com autenticação por token e senhas protegidas por hash. O banco SQLite usa integridade referencial e
uma dimensão de data pronta para análise. Um front-end simples é servido pela própria API, e o projeto
pode ser empacotado em um executável para distribuição nas lojas.

## Contexto de Negócio

O recebimento no CPD é um ponto crítico: é onde a mercadoria entra no estoque e onde divergências de
nota viram perda ou ruptura mais adiante. Controlar esse fluxo em papel ou planilha dificulta a
conferência e a rastreabilidade. Um sistema com autenticação e banco estruturado organiza o
recebimento, protege o acesso e cria a base para conferir entradas e apoiar auditorias.

## O Problema que Resolve

- **Recebimento sem rastreabilidade** confiável (papel/planilha).
- **Falta de controle de acesso** a um processo sensível de entrada de mercadoria.
- **Ausência de base estruturada** para consultar e conferir recebimentos.
- **Dificuldade de distribuir** a ferramenta em lojas sem ambiente técnico.

## Público e Decisões Apoiadas

- **Recebimento/CPD:** lança e consulta notas com rastreabilidade.
- **Fiscal e Auditoria:** conferem entradas a partir de uma base estruturada.
- **Gestão de loja:** acompanha o fluxo de recebimento.

## Impacto e Valor Gerado

- Estrutura o recebimento de NF-e com registro rastreável e acesso controlado (JWT).
- Protege credenciais (hash de senha, sem segredos no código).
- Entrega um banco com integridade referencial e dimensão de data pronta para análise.
- Permite distribuição como executável, sem instalar Python nas lojas.

---

## Arquitetura e Abordagem Técnica

- **API REST em FastAPI** para lançar e consultar recebimentos de NF-e.
- **Autenticação JWT** com hash de senha (nenhuma senha em texto).
- **Banco SQLite** com `PRAGMA foreign_keys`, modo WAL e tabela `dim_data` (chave AAAAMMDD).
- **Front-end em HTML** servido pela própria API.
- **Camada alternativa para MySQL** (`cpd_mysql.py`).
- **Empacotamento em executável** com PyInstaller (`build_exe.py`), para uso nas lojas sem instalação.
- **Configuração segura:** a `SECRET_KEY` é lida de variável de ambiente (`.env`), sem segredos no código.

## Stack

Python - FastAPI - JWT - SQLite - MySQL - HTML - PyInstaller - API REST.

## Como Rodar

```bash
pip install fastapi uvicorn passlib python-jose
copy .env.example .env       # defina SECRET_KEY
python main.py               # sobe a API e abre o formulário
```

## Estrutura do Projeto

```text
main.py       -> API FastAPI + autenticação + rotas
database.py   -> Camada SQLite (WAL, FK, dim_data)
cpd_mysql.py  -> Camada alternativa MySQL
index.html    -> Formulário (front-end)
build_exe.py  -> Empacotamento em .exe
```

## Autor

José Vitor Santos Pinheiro — Análise de Dados e Inteligência Comercial (Varejo e Supply Chain).
Contato: vytorsantt@gmail.com
