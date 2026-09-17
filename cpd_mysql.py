"""
cpd_mysql.py — Camada de Banco de Dados MySQL para o Sistema CPD
Banco: cpd_trabalho | Servidor: localhost | Sem senha (root)
"""

import mysql.connector
from mysql.connector import Error
from datetime import datetime, date

# ─── Configuração de Conexão ─────────────────────────────────────────────────
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "cpd_trabalho",
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
    "autocommit": False,
    "connection_timeout": 10,
}

MYSQL_INIT_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "charset": "utf8mb4",
    "connection_timeout": 10,
}

def get_connection():
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    return conn


def obter_ou_criar_data_fk(conn, data_str: str) -> int:
    dt = datetime.strptime(data_str, "%Y-%m-%d").date()
    pk = int(dt.strftime("%Y%m%d"))

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT pk FROM dim_data WHERE pk = %s", (pk,))
    if cursor.fetchone():
        cursor.close()
        return pk

    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio",
        6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro",
        11: "Novembro", 12: "Dezembro"
    }
    dias_pt = {
        "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
        "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"
    }
    iso = dt.isocalendar()

    cursor.execute("""
        INSERT IGNORE INTO dim_data
            (pk, data_completa, ano, mes, dia, nome_mes, nome_dia_da_semana, iso_ano, iso_semana)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        pk, data_str, dt.year, dt.month, dt.day,
        meses_pt.get(dt.month, ""),
        dias_pt.get(dt.strftime("%A"), ""),
        iso[0], iso[1]
    ))
    conn.commit()
    cursor.close()
    return pk


def init_mysql():
    print("Inicializando banco MySQL: cpd_trabalho...")
    try:
        conn_init = mysql.connector.connect(**MYSQL_INIT_CONFIG)
        cur = conn_init.cursor()
        cur.execute("CREATE DATABASE IF NOT EXISTS cpd_trabalho CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn_init.commit()
        cur.close()
        conn_init.close()
        print("  Banco 'cpd_trabalho' pronto.")
    except Error as e:
        print(f"  Erro ao criar banco: {e}")
        raise

    conn = get_connection()
    cur = conn.cursor()

    # Desativa chaves estrangeiras temporariamente para fazer a limpeza sem erros
    cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
    cur.execute("DROP TABLE IF EXISTS fact_recebimento;")
    cur.execute("DROP TABLE IF EXISTS dim_resolucao;")
    cur.execute("DROP TABLE IF EXISTS dim_status;")
    cur.execute("DROP TABLE IF EXISTS dim_ocorrencia;")
    cur.execute("DROP TABLE IF EXISTS dim_setor;")
    cur.execute("DROP TABLE IF EXISTS dim_recebedor;")
    cur.execute("DROP TABLE IF EXISTS dim_comprador;")
    cur.execute("DROP TABLE IF EXISTS dim_loja;")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1;")

    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS dim_usuario_cpd (
            pk         INT AUTO_INCREMENT PRIMARY KEY,
            nome       VARCHAR(120) NOT NULL,
            email      VARCHAR(120) UNIQUE NOT NULL,
            senha_hash VARCHAR(256) NOT NULL,
            cargo      VARCHAR(80)  DEFAULT 'OPERADOR',
            ativo      TINYINT(1)   NOT NULL DEFAULT 1,
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_loja (
            pk        INT AUTO_INCREMENT PRIMARY KEY,
            nome_loja VARCHAR(120) UNIQUE NOT NULL
        ) ENGINE=InnoDB;
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_comprador (
            pk              INT AUTO_INCREMENT PRIMARY KEY,
            nome_comprador  VARCHAR(120) UNIQUE NOT NULL
        ) ENGINE=InnoDB;
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_recebedor (
            pk              INT AUTO_INCREMENT PRIMARY KEY,
            nome_recebedor  VARCHAR(120) UNIQUE NOT NULL
        ) ENGINE=InnoDB;
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_fornecedor (
            pk            INT AUTO_INCREMENT PRIMARY KEY,
            razao_social  VARCHAR(200) UNIQUE NOT NULL,
            nome_fantasia VARCHAR(200),
            cnpj_cpf      VARCHAR(20) UNIQUE
        ) ENGINE=InnoDB;
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_setor (
            pk         INT AUTO_INCREMENT PRIMARY KEY,
            nome_setor VARCHAR(80) UNIQUE NOT NULL
        ) ENGINE=InnoDB;
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_ocorrencia (
            pk                   INT AUTO_INCREMENT PRIMARY KEY,
            descricao_ocorrencia VARCHAR(200) UNIQUE NOT NULL
        ) ENGINE=InnoDB;
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_status (
            pk          INT AUTO_INCREMENT PRIMARY KEY,
            nome_status VARCHAR(80) UNIQUE NOT NULL
        ) ENGINE=InnoDB;
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_data (
            pk                 INT PRIMARY KEY COMMENT 'Formato AAAAMMDD',
            data_completa      DATE        NOT NULL,
            ano                SMALLINT    NOT NULL,
            mes                TINYINT     NOT NULL,
            dia                TINYINT     NOT NULL,
            nome_mes           VARCHAR(20) NOT NULL,
            nome_dia_da_semana VARCHAR(20) NOT NULL,
            iso_ano            SMALLINT    NOT NULL,
            iso_semana         TINYINT     NOT NULL
        ) ENGINE=InnoDB;
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_resolucao (
            pk                  INT AUTO_INCREMENT PRIMARY KEY,
            setor_fk            INT NOT NULL,
            ocorrencia_fk       INT NOT NULL,
            descricao_resolucao VARCHAR(300) NOT NULL,
            UNIQUE KEY uq_resolucao (setor_fk, ocorrencia_fk, descricao_resolucao(150)),
            FOREIGN KEY (setor_fk)      REFERENCES dim_setor(pk)      ON DELETE CASCADE,
            FOREIGN KEY (ocorrencia_fk) REFERENCES dim_ocorrencia(pk) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """,
        """
        CREATE TABLE IF NOT EXISTS fact_recebimento (
            fact_id       INT AUTO_INCREMENT PRIMARY KEY,
            nota          VARCHAR(50)  NOT NULL,
            obs           TEXT,
            tipo_entrega  ENUM('Mix','Volume') DEFAULT NULL,
            tipo_carga    VARCHAR(50),
            sucesso_flag  TINYINT NOT NULL DEFAULT 0,
            resolucao     VARCHAR(300),

            data_fk       INT NOT NULL,
            loja_fk       INT NOT NULL,
            fornecedor_fk INT NOT NULL,
            comprador_fk  INT DEFAULT NULL,
            recebedor_fk  INT DEFAULT NULL,
            usuario_fk    INT DEFAULT NULL,
            setor_fk      INT DEFAULT NULL,
            status_fk     INT NOT NULL,
            ocorrencia_fk INT DEFAULT NULL,

            hora_chegada    TIME DEFAULT NULL,
            hora_liberado   TIME DEFAULT NULL,
            hora_inicio_rec TIME DEFAULT NULL,
            hora_final_rec  TIME DEFAULT NULL,

            minutos_para_liberar_nfe  SMALLINT UNSIGNED DEFAULT NULL,
            minutos_espera            SMALLINT UNSIGNED DEFAULT NULL,
            minutos_recebimento       SMALLINT UNSIGNED DEFAULT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

            FOREIGN KEY (data_fk)       REFERENCES dim_data(pk),
            FOREIGN KEY (loja_fk)       REFERENCES dim_loja(pk),
            FOREIGN KEY (fornecedor_fk) REFERENCES dim_fornecedor(pk),
            FOREIGN KEY (comprador_fk)  REFERENCES dim_comprador(pk),
            FOREIGN KEY (recebedor_fk)  REFERENCES dim_recebedor(pk),
            FOREIGN KEY (usuario_fk)    REFERENCES dim_usuario_cpd(pk),
            FOREIGN KEY (setor_fk)      REFERENCES dim_setor(pk),
            FOREIGN KEY (status_fk)     REFERENCES dim_status(pk),
            FOREIGN KEY (ocorrencia_fk) REFERENCES dim_ocorrencia(pk),

            INDEX idx_data      (data_fk),
            INDEX idx_loja      (loja_fk),
            INDEX idx_fornecedor(fornecedor_fk),
            INDEX idx_nota      (nota)
        ) ENGINE=InnoDB;
        """
    ]

    for ddl in ddl_statements:
        cur.execute(ddl)
    conn.commit()
    print("  Tabelas criadas/verificadas.")
    _seed(conn, cur)

    cur.close()
    conn.close()
    print("Banco MySQL 'cpd_trabalho' inicializado com sucesso!\n")


def _seed(conn, cur):
    lojas = ["LOJA SUL", "LOJA CENTRAL", "LOJA OESTE", "LOJA SHOPPING"]
    for l in lojas:
        cur.execute("INSERT IGNORE INTO dim_loja (nome_loja) VALUES (%s)", (l,))

    compradores = ["Bruno", "Carla", "Andresa", "Elaine", "Diego", "Fabio"]
    for c in compradores:
        cur.execute("INSERT IGNORE INTO dim_comprador (nome_comprador) VALUES (%s)", (c,))

    recebedores = [
        "Alexandre", "Gustavo", "Rafael", "Tiago",
        "Vinicius", "Leonardo", "Marcelo", "Rodrigo"
    ]
    for r in recebedores:
        cur.execute("INSERT IGNORE INTO dim_recebedor (nome_recebedor) VALUES (%s)", (r,))

    setores = ["Comercial", "Fornecedor", "CPD"]
    for s in setores:
        cur.execute("INSERT IGNORE INTO dim_setor (nome_setor) VALUES (%s)", (s,))

    statuses = ["Não recebeu", "Recebeu"]
    for st in statuses:
        cur.execute("INSERT IGNORE INTO dim_status (nome_status) VALUES (%s)", (st,))

    # Usuário admin de DEMONSTRAÇÃO (troque a senha em produção; use o .env/hash próprio)
    from passlib.hash import sha256_crypt
    cur.execute("SELECT COUNT(*) FROM dim_usuario_cpd WHERE email = %s", ("admin@exemplo.com",))
    if cur.fetchone()[0] == 0:
        admin_hash = sha256_crypt.hash("admin123")
        cur.execute("""
            INSERT INTO dim_usuario_cpd (nome, email, senha_hash, cargo, ativo)
            VALUES (%s, %s, %s, %s, 1)
        """, ("Administrador", "admin@exemplo.com", admin_hash, "ADMIN"))

    ocorrencias = [
        "Divergência de Custo", "Divergência na Quantidade", "Sem XML",
        "Sem Associação", "Divergência no Vencimento", "Divergência no Lançamento",
        "Divergência no Cadastro", "Sem Pedido", "Sem Agendamento",
        "Produto sem Pedido", "Sem Reagendamento", "Sem Troca",
        "Seguiu Rota", "Não Finalizado"
    ]
    for oc in ocorrencias:
        cur.execute("INSERT IGNORE INTO dim_ocorrencia (descricao_ocorrencia) VALUES (%s)", (oc,))

    conn.commit()

    cur.execute("SELECT pk, nome_setor FROM dim_setor")
    setores_inv = {r[1]: r[0] for r in cur.fetchall()}
    cur.execute("SELECT pk, descricao_ocorrencia FROM dim_ocorrencia")
    oc_map = {r[1]: r[0] for r in cur.fetchall()}

    resolucoes = [
        # comercial_Divergencia_de_custo
        ("Comercial", "Divergência de Custo", "Copiar o pedido com o preco correto"),
        ("Comercial", "Divergência de Custo", "Aceitou receber com divergencia"),

        # fornecedor_Divergencia_de_custo
        ("Fornecedor", "Divergência de Custo", "Refaturamento Nfe"),
        ("Fornecedor", "Divergência de Custo", "Pago com acordo"),
        ("Fornecedor", "Divergência de Custo", "Pago no caixa"),
        ("Fornecedor", "Divergência de Custo", "NFd parcial"),
        ("Fornecedor", "Divergência de Custo", "Comercial aceitou receber com divergencia"),
        ("Fornecedor", "Divergência de Custo", "NFe devolvida"),

        # comercial_Divergencia_na_quantidade
        ("Comercial", "Divergência na Quantidade", "Copiar o pedido com o preco correto"),
        ("Comercial", "Divergência na Quantidade", "Aceitou receber com divergencia"),
        ("Comercial", "Divergência na Quantidade", "Criou um pedido para a quantidade excedente"),

        # fornecedor_Divergencia_na_quantidade
        ("Fornecedor", "Divergência na Quantidade", "Refaturamento Nfe"),
        ("Fornecedor", "Divergência na Quantidade", "Pago com acordo"),
        ("Fornecedor", "Divergência na Quantidade", "Pago no caixa"),
        ("Fornecedor", "Divergência na Quantidade", "NFd parcial"),
        ("Fornecedor", "Divergência na Quantidade", "Comercial aceitou receber com divergencia"),
        ("Fornecedor", "Divergência na Quantidade", "NFe devolvida"),

        # fornecedor_Sem_Xml
        ("Fornecedor", "Sem XML", "Pegar a info na sefaz"),

        # comercial_Sem_associacao
        ("Comercial", "Sem Associação", "Não foi informado o código"),

        # cpd_Sem_associacao
        ("CPD", "Sem Associação", "Atualizou código"),
        ("CPD", "Sem Associação", "Não foi atualizado o código"),

        # fornecedor_Sem_associacao
        ("Fornecedor", "Sem Associação", "Não foi informado o código"),
        ("Fornecedor", "Sem Associação", "NFe devolvida"),

        # comercial_Divergencia_no_vencimento
        ("Comercial", "Divergência no Vencimento", "Aceitou receber com divergencia"),

        # fornecedor_Divergencia_no_vencimento
        ("Fornecedor", "Divergência no Vencimento", "Refaturamento do boleto"),
        ("Fornecedor", "Divergência no Vencimento", "Comercial aceitou receber com divergencia"),
        ("Fornecedor", "Divergência no Vencimento", "NFe devolvida"),

        # cpd_Divergencia_no_lançamento
        ("CPD", "Divergência no Lançamento", "Correção do lançamento"),

        # comercial_Divergencia_no_cadastro
        ("Comercial", "Divergência no Cadastro", "Não foi passado o cadastro"),

        # cpd_Divergencia_no_cadastro
        ("CPD", "Divergência no Cadastro", "Não foi cadastrado"),
        ("CPD", "Divergência no Cadastro", "Foi cadastrado no ato da entrega"),

        # fornecedor_Divergencia_no_cadastro
        ("Fornecedor", "Divergência no Cadastro", "Não foi passado o cadastro"),
        ("Fornecedor", "Divergência no Cadastro", "NFe devolvida"),

        # comercial_Sem_pedido
        ("Comercial", "Sem Pedido", "Digitado no ato da entrega"),

        # fornecedor_Sem_pedido
        ("Fornecedor", "Sem Pedido", "NFe devolvida"),

        # comercial_Sem_agendamento
        ("Comercial", "Sem Agendamento", "Não foi solicitado"),
        ("Comercial", "Sem Agendamento", "Chegou antes do agendamento"),

        # cpd_Sem_agendamento
        ("CPD", "Sem Agendamento", "Foi solicitado, mas não agendado"),
        ("CPD", "Sem Agendamento", "Não agendou"),

        # fornecedor_Sem_agendamento
        ("Fornecedor", "Sem Agendamento", "Não foi solicitado"),
        ("Fornecedor", "Sem Agendamento", "Chegou antes do agendamento"),
        ("Fornecedor", "Sem Agendamento", "NFe devolvida"),

        # comercial_Produto_sem_pedido
        ("Comercial", "Produto sem Pedido", "Copiar o pedido com o preco correto"),
        ("Comercial", "Produto sem Pedido", "Aceitou receber com divergencia"),
        ("Comercial", "Produto sem Pedido", "Criou um pedido para o item sem pedido"),
        ("Comercial", "Produto sem Pedido", "Sem associação"),

        # fornecedor_Produto_sem_pedido
        ("Fornecedor", "Produto sem Pedido", "Refaturamento Nfe"),
        ("Fornecedor", "Produto sem Pedido", "Pago no caixa"),
        ("Fornecedor", "Produto sem Pedido", "NFd parcial"),
        ("Fornecedor", "Produto sem Pedido", "Comercial aceitou receber com divergencia"),
        ("Fornecedor", "Produto sem Pedido", "NFe devolvida"),

        # comercial_Sem_reagendamento
        ("Comercial", "Sem Reagendamento", "Não solicitou"),

        # cpd_Sem_reagendamento
        ("CPD", "Sem Reagendamento", "Não foi reagendamento"),

        # fornecedor_Sem_reagendamento
        ("Fornecedor", "Sem Reagendamento", "Não solicitou"),

        # comercial_Sem_troca
        ("Comercial", "Sem Troca", "Aceitou receber com divergencia"),

        # fornecedor_Sem_troca
        ("Fornecedor", "Sem Troca", "Pago com acordo"),
        ("Fornecedor", "Sem Troca", "NFd parcial"),
        ("Fornecedor", "Sem Troca", "NFe devolvida"),

        # comercial_Seguiu_rota
        ("Comercial", "Seguiu Rota", "Sem doca/espaço suficiente para receber"),
        ("Comercial", "Seguiu Rota", "Sem conferente suficiente para receber"),

        # fornecedor_Seguiu_rota
        ("Fornecedor", "Seguiu Rota", "Deixou a Nfe e foi embora"),
        ("Fornecedor", "Seguiu Rota", "Deixou a Nfe e voltou depois"),

        # comercial_Nao_finalizado
        ("Comercial", "Não Finalizado", "Finalizou no ato do recebimento")
    ]
    for set_nome, oc_desc, res_desc in resolucoes:
        s_id = setores_inv.get(set_nome)
        o_id = oc_map.get(oc_desc)
        if s_id and o_id:
            cur.execute("""
                INSERT IGNORE INTO dim_resolucao (setor_fk, ocorrencia_fk, descricao_resolucao)
                VALUES (%s, %s, %s)
            """, (s_id, o_id, res_desc))

    conn.commit()
    print("  Dados semente inseridos.")


if __name__ == "__main__":
    init_mysql()

