# Sistema de Recebimento de NF-e / CPD

Aplicação full-stack para registrar e controlar o recebimento de notas fiscais eletrônicas (NF-e) no
Centro de Distribuição (CPD) de um supermercado — e, a partir desse registro, alimentar um modelo de
dados pronto para análise (BI). Back-end em FastAPI com autenticação JWT, banco SQLite em modo WAL
(com camada alternativa MySQL) e empacotamento em executável, para que as lojas usem o sistema sem
instalar um ambiente de desenvolvimento.

O projeto tem duas metades que se encaixam: um **app que joga no banco** (formulário web + API que
valida, calcula métricas e grava) e um **banco que vira análise** (modelo estrela, fato + dimensões,
o formato que ferramentas de BI consomem direto).

> **Nota de confidencialidade:** todos os dados presentes neste repositório (planilhas, seeds,
> exemplos) são fictícios, gerados aleatoriamente apenas para demonstração. Os dados reais da operação
> são confidenciais e estão protegidos — nenhum dado real, credencial ou informação de terceiros foi
> incluído aqui.

---

## Visão Geral

O sistema cobre o registro do recebimento de mercadoria no CPD: uma API REST lança e consulta as notas,
com autenticação por token e senhas protegidas por hash. O banco usa integridade referencial e um
modelo dimensional (esquema estrela) com uma dimensão de data pronta para análise. Um front-end simples
é servido pela própria API, e o projeto pode ser empacotado em um executável para distribuição nas lojas.

## Contexto de Negócio

O recebimento no CPD é um ponto crítico: é onde a mercadoria entra no estoque e onde divergências de
nota viram perda ou ruptura mais adiante. Controlar esse fluxo em papel ou planilha dificulta a
conferência e a rastreabilidade. Um sistema com autenticação e banco estruturado organiza o
recebimento, protege o acesso e cria a base para conferir entradas e apoiar auditorias.

## O Problema que Resolve

- **Recebimento sem rastreabilidade** confiável (papel/planilha).
- **Falta de controle de acesso** a um processo sensível de entrada de mercadoria.
- **Ausência de base estruturada** para consultar, conferir e analisar recebimentos.
- **Dificuldade de distribuir** a ferramenta em lojas sem ambiente técnico.

## Público e Decisões Apoiadas

- **Recebimento/CPD:** lança e consulta notas com rastreabilidade.
- **Fiscal e Auditoria:** conferem entradas a partir de uma base estruturada.
- **Gestão de loja:** acompanha o fluxo e os tempos de recebimento.

## Impacto e Valor Gerado

- Estrutura o recebimento de NF-e com registro rastreável e acesso controlado (JWT).
- Protege credenciais (hash de senha, sem segredos no código).
- Entrega um banco com integridade referencial e modelo estrela pronto para análise.
- Calcula métricas de tempo do processo (liberação da NF-e, espera na doca, recebimento).
- Permite distribuição como executável, sem instalar Python nas lojas.

---

## Da Captura à Análise (pipeline)

```text
 index.html            FastAPI (main.py)              Banco (esquema estrela)
 formulário   --HTTP-->  auth JWT + validação  --SQL-->  fact_recebimento + dim_*
 (navegador)  <-JSON--   cálculo de métricas   <-----    (fato + dimensões)
                                                              |
                                                              v
                                                    Análise / BI (dashboards
                                                    leem o modelo estrela)
```

1. **Captura:** o operador preenche o recebimento no navegador; a API grava um registro no **fato**.
2. **Modelagem:** cada linha do fato aponta por chaves para as **dimensões** (loja, fornecedor, data,
   ocorrência…), mantendo o dado limpo, sem repetição e fácil de cruzar.
3. **Análise:** como o banco já nasce em esquema estrela, o BI conecta direto e responde perguntas
   de negócio sem transformação adicional.

## Arquitetura e Abordagem Técnica

- **API REST em FastAPI** para lançar e consultar recebimentos de NF-e.
- **Autenticação JWT** com hash de senha (`sha256_crypt`, pure-Python — sem senha em texto).
- **Cálculo automático de métricas de tempo** a partir dos horários informados no formulário.
- **Modelo estrela** (fato + dimensões) com `dim_data` (chave AAAAMMDD) para inteligência temporal.
- **Dois back-ends intercambiáveis:** MySQL (produção) e SQLite em modo WAL (fallback local, sem
  servidor). A mesma API atende os dois, abstraindo o placeholder de SQL (`%s` no MySQL, `?` no SQLite).
- **Front-end em HTML/JS** servido pela própria API (formulário + histórico com busca/filtro).
- **Empacotamento em executável** com PyInstaller (`build_exe.py`), para uso nas lojas sem instalação.
- **Configuração segura:** a `SECRET_KEY` é lida de variável de ambiente (`.env`), sem segredos no código.

## Modelo de Dados (esquema estrela)

Uma tabela **fato** no centro, cercada por **dimensões**.

### Fato — `fact_recebimento`
Grão: um recebimento de NF-e. Guarda as chaves para as dimensões, atributos do próprio recebimento e as
medidas (o que se agrega na análise).

| Grupo | Colunas | Função |
|---|---|---|
| Chaves (FK) | `data_fk`, `loja_fk`, `fornecedor_fk`, `comprador_fk`, `recebedor_fk`, `usuario_fk`, `setor_fk`, `status_fk`, `ocorrencia_fk` | Ligam o fato às dimensões (quem/onde/quando/por quê). |
| Atributos | `nota`, `tipo_entrega`, `tipo_carga`, `resolucao`, `obs`, `sucesso_flag` | Detalhes do recebimento. |
| Horários | `hora_chegada`, `hora_liberado`, `hora_inicio_rec`, `hora_final_rec` | Marcos de tempo capturados no formulário. |
| Medidas | `minutos_para_liberar_nfe`, `minutos_espera`, `minutos_recebimento` | Calculadas pela API — são o que a análise agrega. |

As medidas derivam dos horários:
- `minutos_para_liberar_nfe` = chegada -> liberação (tempo para liberar a NF-e);
- `minutos_espera` = chegada -> início da descarga (espera na doca);
- `minutos_recebimento` = início -> fim (descarga/conferência).

### Dimensões (`dim_*`)
| Dimensão | Descreve |
|---|---|
| `dim_data` | Calendário (chave AAAAMMDD, data, ano, mês, dia, nome do mês/dia, ano/semana ISO). |
| `dim_loja` | Loja/unidade que recebeu. |
| `dim_fornecedor` | Fornecedor (razão social, nome fantasia, CNPJ/CPF). |
| `dim_comprador` | Comprador responsável (setor comercial). |
| `dim_recebedor` | Quem recebeu/conferiu a carga. |
| `dim_usuario_cpd` | Usuário do sistema que lançou o registro (nome, cargo, status). |
| `dim_setor` | Setor responsável pela ocorrência (ex.: Comercial, Fornecedor, CPD). |
| `dim_ocorrencia` | Tipo de divergência/ocorrência. |
| `dim_status` | Situação (ex.: Recebeu / Não recebeu). |
| `dim_resolucao` | Regras de resolução válidas por setor + ocorrência. |

O esquema estrela separa **medida** (fato) de **contexto** (dimensões): a escrita fica barata e sem
dados repetidos, e a leitura analítica fica simples — um dashboard cruza o fato com qualquer dimensão.

## Fluxo de um Recebimento

1. **Login** -> a API valida e devolve um JWT (o front envia em cada chamada).
2. O front chama `GET /api/opcoes` e preenche os selects (lojas, fornecedores, setores…).
3. O operador preenche o formulário (NF, fornecedor, horários, ocorrência…).
4. Ao salvar, o front envia `POST /api/recebimentos`.
5. A API garante a data na `dim_data`, calcula as métricas de tempo e faz o `INSERT` no
   `fact_recebimento` com todas as chaves resolvidas.
6. O histórico (`GET /api/recebimentos`) devolve os registros já cruzados com as dimensões (JOIN
   estrela), com busca por NF/fornecedor e filtro por status.

## Do Banco à Análise

Como o dado já está em esquema estrela, a camada de BI conecta direto ao fato + dimensões e responde,
por exemplo:

- Tempo médio de liberação de NF-e por fornecedor, loja ou dia da semana.
- Espera média na doca e horários de gargalo.
- Produtividade de recebimento por recebedor.
- Percentual de recebimentos com ocorrência e ocorrências mais frequentes por setor.
- Taxa de sucesso (Recebeu x Não recebeu) por período.
- Volume de NF-e por comprador, loja ou mês.

A `dim_data` com chave AAAAMMDD habilita inteligência temporal (mês a mês, semana ISO, dia da semana)
sem cálculo extra no relatório.

## API (endpoints)

| Método e rota | Função |
|---|---|
| `GET /` | Serve o formulário (`index.html`). |
| `POST /api/auth/cadastro` | Cria usuário (senha com hash). |
| `POST /api/auth/login` | Autentica e devolve o JWT. |
| `GET /api/auth/me` | Valida o token atual. |
| `GET /api/opcoes` | Devolve as dimensões para preencher os selects. |
| `GET /api/recebimentos` | Histórico (JOIN estrela) com busca e filtro por status. |
| `POST /api/recebimentos` | Grava um recebimento e calcula as métricas de tempo. |
| `POST /api/admin/cadastro` | Cadastra nova loja / comprador / recebedor. |
| `POST /api/admin/fornecedor` | Cadastra novo fornecedor. |
| `POST /api/admin/resolucao` | Cadastra uma regra de resolução (setor + ocorrência). |

## Stack

Python - FastAPI - JWT - SQLite (WAL) - MySQL - Modelagem dimensional (estrela) - HTML/JS -
PyInstaller - API REST.

## Como Rodar

```bash
pip install fastapi uvicorn passlib python-jose
copy .env.example .env       # defina SECRET_KEY
python main.py               # sobe a API e abre o formulário
```

**Login de demonstração** (criado no primeiro boot): `admin@exemplo.com` / `admin123` — credencial de
exemplo; troque em qualquer uso real. Sem MySQL disponível, a aplicação cai automaticamente no SQLite
(arquivo local, modo WAL), rodando em qualquer máquina sem configurar servidor.

## Estrutura do Projeto

```text
main.py        -> API FastAPI: auth JWT, rotas (opções/recebimentos/admin), cálculo das métricas de
                  tempo, escolha MySQL/SQLite e entrega do index.html. Ponto de entrada (sobe o uvicorn).
database.py    -> Camada SQLite (fallback): cria o esquema estrela (CREATE TABLE IF NOT EXISTS), índices,
                  PRAGMA foreign_keys + WAL, a dim_data e os dados-semente de demonstração.
cpd_mysql.py   -> Camada MySQL (produção): o mesmo esquema estrela em InnoDB, dim_data e seed.
index.html     -> Front-end (login + formulário + histórico); consome a API via fetch, com autocomplete
                  de fornecedor e cálculo dos tempos no cliente.
build_exe.py   -> Empacota tudo em um único .exe (PyInstaller), para rodar sem instalar Python.
test_db.py     -> Teste rápido da camada de banco.
data_exemplo/  -> Dados fictícios de demonstração (seed_nfe_exemplo.json).
.env.example   -> Modelo das variáveis de ambiente (SECRET_KEY, MYSQL_URL).
```

## Segurança e Boas Práticas

- **JWT** para sessão e **hash de senha** (`sha256_crypt`) — nada de senha em texto.
- **Segredo fora do código:** `SECRET_KEY` vem do ambiente (`.env`), com `.env` no `.gitignore`.
- **Sem dados/credenciais reais** no repositório: `.db`, `.env`, `dist/` e `*.exe` são ignorados; o
  usuário admin semeado é apenas de demonstração.
- **Consultas parametrizadas** (placeholders) — a mesma camada abstrai `%s` (MySQL) e `?` (SQLite).

## Autor

José Vitor Santos Pinheiro — Análise de Dados e Inteligência Comercial (Varejo e Supply Chain).
Contato: vytorsantt@gmail.com
