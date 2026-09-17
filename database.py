import os
import sqlite3
from datetime import datetime, date

PROJECT_DIR = r"C:\Users\Usuário\OneDrive\Documentos\minha_pasta\Projetos\cpd_form_project"
if os.path.exists(PROJECT_DIR):
    DB_PATH = os.path.join(PROJECT_DIR, "cpd.db")
else:
    DB_PATH = os.path.join(os.path.expanduser("~"), "cpd.db")


def get_connection():
    """Retorna uma conexão configurada com o SQLite"""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    # Habilita suporte a chaves estrangeiras e modo WAL para escalabilidade
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def obter_ou_criar_data_fk(conn, data_str):
    """
    Dada uma data no formato 'YYYY-MM-DD', insere ou busca na tabela dim_data
    e retorna o pk numérico no formato AAAAMMDD.
    """
    dt = datetime.strptime(data_str, "%Y-%m-%d").date()
    pk = int(dt.strftime("%Y%m%d"))
    
    cursor = conn.cursor()
    cursor.execute("SELECT pk FROM dim_data WHERE pk = ?", (pk,))
    row = cursor.fetchone()
    
    if row:
        return pk
        
    # Nomes em português para meses e dias
    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    dias_pt = {
        "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
        "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"
    }
    
    nome_mes = meses_pt.get(dt.month, "")
    nome_dia = dias_pt.get(dt.strftime("%A"), "")
    
    cursor.execute("""
        INSERT INTO dim_data (pk, data_completa, ano, mes, dia, nome_mes, nome_dia_da_semana, iso_ano, iso_semana)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pk,
        data_str,
        dt.year,
        dt.month,
        dt.day,
        nome_mes,
        nome_dia,
        dt.year,
        dt.isocalendar()[1]
    ))
    conn.commit()
    return pk

def init_db():
    """Inicializa as tabelas do banco de dados SQLite e insere os dados iniciais (seed)"""
    print(f"Inicializando banco de dados em: {DB_PATH}")
    
    # Cria o diretório se não existir (embora Desktop sempre exista)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Drops preventivos para garantir a exclusão de dados antigos incoerentes
    cursor.execute("DROP TABLE IF EXISTS fact_recebimento;")
    cursor.execute("DROP TABLE IF EXISTS dim_resolucao;")
    cursor.execute("DROP TABLE IF EXISTS dim_status;")
    cursor.execute("DROP TABLE IF EXISTS dim_ocorrencia;")
    cursor.execute("DROP TABLE IF EXISTS dim_setor;")
    cursor.execute("DROP TABLE IF EXISTS dim_recebedor;")
    cursor.execute("DROP TABLE IF EXISTS dim_comprador;")
    cursor.execute("DROP TABLE IF EXISTS dim_loja;")
    
    # Ativa transações
    cursor.execute("BEGIN TRANSACTION;")
    
    try:
        # 0. dim_usuario_cpd
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_usuario_cpd (
                pk         INTEGER PRIMARY KEY AUTOINCREMENT,
                nome       TEXT NOT NULL,
                email      TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                cargo      TEXT DEFAULT 'OPERADOR',
                ativo      INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 1. dim_comprador
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_comprador (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_comprador TEXT UNIQUE NOT NULL
            );
        """)

        # 1b. dim_recebedor
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_recebedor (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_recebedor TEXT UNIQUE NOT NULL
            );
        """)
        
        # 2. dim_loja
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_loja (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_loja TEXT UNIQUE NOT NULL
            );
        """)
        
        # 3. dim_fornecedor
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_fornecedor (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                razao_social TEXT UNIQUE NOT NULL,
                nome_fantasia TEXT,
                cnpj_cpf TEXT UNIQUE
            );
        """)
        
        # 4. dim_setor
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_setor (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_setor TEXT UNIQUE NOT NULL
            );
        """)
        
        # 5. dim_ocorrencia
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_ocorrencia (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao_ocorrencia TEXT UNIQUE NOT NULL
            );
        """)
        
        # 6. dim_status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_status (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_status TEXT UNIQUE NOT NULL
            );
        """)
        
        # 7. dim_data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_data (
                pk INTEGER PRIMARY KEY, -- formato AAAAMMDD
                data_completa TEXT UNIQUE NOT NULL,
                ano INTEGER NOT NULL,
                mes INTEGER NOT NULL,
                dia INTEGER NOT NULL,
                nome_mes TEXT NOT NULL,
                nome_dia_da_semana TEXT NOT NULL,
                iso_ano INTEGER NOT NULL,
                iso_semana INTEGER NOT NULL
            );
        """)
        
        # 8. dim_resolucao (Mapeia as resoluções vinculadas ao setor e ocorrência)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dim_resolucao (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                setor_fk INTEGER NOT NULL,
                ocorrencia_fk INTEGER NOT NULL,
                descricao_resolucao TEXT NOT NULL,
                FOREIGN KEY(setor_fk) REFERENCES dim_setor(pk) ON DELETE CASCADE,
                FOREIGN KEY(ocorrencia_fk) REFERENCES dim_ocorrencia(pk) ON DELETE CASCADE,
                UNIQUE(setor_fk, ocorrencia_fk, descricao_resolucao)
            );
        """)
        
        # 9. fact_recebimento
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fact_recebimento (
                fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                nota TEXT NOT NULL,
                obs TEXT,
                tipo_entrega TEXT CHECK(tipo_entrega IN ('Mix', 'Volume') OR tipo_entrega IS NULL),
                tipo_carga TEXT,
                sucesso_flag INTEGER NOT NULL DEFAULT 0 CHECK(sucesso_flag IN (0, 1, 2, 9)),
                resolucao TEXT,

                -- Chaves estrangeiras
                data_fk INTEGER NOT NULL,
                loja_fk INTEGER NOT NULL,
                fornecedor_fk INTEGER NOT NULL,
                comprador_fk INTEGER,
                recebedor_fk INTEGER,
                usuario_fk INTEGER,
                setor_fk INTEGER,
                status_fk INTEGER,
                ocorrencia_fk INTEGER,

                -- Horários
                hora_chegada TEXT,
                hora_liberado TEXT,
                hora_inicio_rec TEXT,
                hora_final_rec TEXT,

                -- Métricas calculadas
                minutos_para_liberar_nfe INTEGER CHECK(minutos_para_liberar_nfe >= 0 OR minutos_para_liberar_nfe IS NULL),
                minutos_espera INTEGER CHECK(minutos_espera >= 0 OR minutos_espera IS NULL),
                minutos_recebimento INTEGER CHECK(minutos_recebimento >= 0 OR minutos_recebimento IS NULL),

                -- Auditoria
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(data_fk)       REFERENCES dim_data(pk),
                FOREIGN KEY(loja_fk)       REFERENCES dim_loja(pk),
                FOREIGN KEY(fornecedor_fk) REFERENCES dim_fornecedor(pk),
                FOREIGN KEY(comprador_fk)  REFERENCES dim_comprador(pk),
                FOREIGN KEY(recebedor_fk)  REFERENCES dim_recebedor(pk),
                FOREIGN KEY(usuario_fk)    REFERENCES dim_usuario_cpd(pk),
                FOREIGN KEY(setor_fk)      REFERENCES dim_setor(pk),
                FOREIGN KEY(status_fk)     REFERENCES dim_status(pk),
                FOREIGN KEY(ocorrencia_fk) REFERENCES dim_ocorrencia(pk)
            );
        """)
        
        # Índices de performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_data ON fact_recebimento(data_fk);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_loja ON fact_recebimento(loja_fk);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_fornecedor ON fact_recebimento(fornecedor_fk);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_comprador ON fact_recebimento(comprador_fk);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_setor ON fact_recebimento(setor_fk);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_status ON fact_recebimento(status_fk);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_ocorrencia ON fact_recebimento(ocorrencia_fk);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_nota ON fact_recebimento(nota);")
        
        # -------------------------------------------------------------
        # INSERÇÃO DE DADOS SEMENTE (SEED)
        # -------------------------------------------------------------
        
        # Lojas
        lojas = ["LOJA SUL", "LOJA CENTRAL", "LOJA OESTE", "LOJA SHOPPING"]
        for loja in lojas:
            cursor.execute("INSERT OR IGNORE INTO dim_loja (nome_loja) VALUES (?)", (loja,))

        # Compradores (setor comercial)
        compradores = ["Bruno", "Carla", "Andresa", "Elaine", "Diego", "Fabio"]
        for c in compradores:
            cursor.execute("INSERT OR IGNORE INTO dim_comprador (nome_comprador) VALUES (?)", (c,))

        # Recebedores (nomes fictícios de demonstração)
        recebedores = [
            "Alexandre", "Gustavo", "Rafael", "Tiago",
            "Vinicius", "Leonardo", "Marcelo", "Rodrigo"
        ]
        for r in recebedores:
            cursor.execute("INSERT OR IGNORE INTO dim_recebedor (nome_recebedor) VALUES (?)", (r,))
            
        # Setores (Somente os usados no mapeamento do script)
        setores = ["Comercial", "Fornecedor", "CPD"]
        for s in setores:
            cursor.execute("INSERT OR IGNORE INTO dim_setor (nome_setor) VALUES (?)", (s,))

        # Status
        statuses = ["Não recebeu", "Recebeu"]
        for st in statuses:
            cursor.execute("INSERT OR IGNORE INTO dim_status (nome_status) VALUES (?)", (st,))

        # Usuário admin de DEMONSTRAÇÃO (troque a senha em produção; use o .env/hash próprio)
        from passlib.hash import sha256_crypt
        cursor.execute("SELECT COUNT(*) FROM dim_usuario_cpd WHERE email = ?", ("admin@exemplo.com",))
        if cursor.fetchone()[0] == 0:
            admin_hash = sha256_crypt.hash("admin123")
            cursor.execute("""
                INSERT INTO dim_usuario_cpd (nome, email, senha_hash, cargo, ativo)
                VALUES (?, ?, ?, ?, 1)
            """, ("Administrador", "admin@exemplo.com", admin_hash, "ADMIN"))
            
        # Ocorrências (Somente as 14 usadas no mapeamento do script)
        ocorrencias = [
            "Divergência de Custo", "Divergência na Quantidade", "Sem XML",
            "Sem Associação", "Divergência no Vencimento", "Divergência no Lançamento",
            "Divergência no Cadastro", "Sem Pedido", "Sem Agendamento",
            "Produto sem Pedido", "Sem Reagendamento", "Sem Troca",
            "Seguiu Rota", "Não Finalizado"
        ]
        for oc in ocorrencias:
            cursor.execute("INSERT OR IGNORE INTO dim_ocorrencia (descricao_ocorrencia) VALUES (?)", (oc,))
            
        # Fornecedores fictícios de demonstração (CNPJs de exemplo)
        fornecedores = [
            ("DISTRIBUIDORA ALFA LTDA", "Alfa", "11.111.111/0001-11"),
            ("FORNECEDOR BETA S.A.", "Beta", "22.222.222/0001-22"),
            ("COMERCIAL GAMA LTDA", "Gama", "33.333.333/0001-33"),
            ("INDUSTRIA DELTA S.A.", "Delta", "44.444.444/0001-44"),
            ("ATACADO EPSILON LTDA", "Epsilon", "55.555.555/0001-55"),
            ("OUTROS / DIVERSOS", "Outros Fornecedores", "00.000.000/0000-00")
        ]
        for razao, fantasia, cnpj in fornecedores:
            cursor.execute("""
                INSERT OR IGNORE INTO dim_fornecedor (razao_social, nome_fantasia, cnpj_cpf)
                VALUES (?, ?, ?)
            """, (razao, fantasia, cnpj))
            
        # Commit intermediário para obter ids das sementes de resoluções
        conn.commit()
        
        # Sementes de Resoluções vinculadas (Setor + Ocorrência)
        cursor.execute("SELECT pk, nome_setor FROM dim_setor")
        setores_map = {row["nome_setor"]: row["pk"] for row in cursor.fetchall()}
        
        cursor.execute("SELECT pk, descricao_ocorrencia FROM dim_ocorrencia")
        ocorrencias_map = {row["descricao_ocorrencia"]: row["pk"] for row in cursor.fetchall()}
        
        # Mapeamento exato do script
        resolucoes_seed = [
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
        
        # Reinicia transação para resoluções
        cursor.execute("BEGIN TRANSACTION;")
        for set_nome, oc_desc, res_desc in resolucoes_seed:
            s_id = setores_map.get(set_nome)
            o_id = ocorrencias_map.get(oc_desc)
            if s_id and o_id:
                cursor.execute("""
                    INSERT OR IGNORE INTO dim_resolucao (setor_fk, ocorrencia_fk, descricao_resolucao)
                    VALUES (?, ?, ?)
                """, (s_id, o_id, res_desc))
                
        # Insere a data de hoje na dim_data para iniciar
        obter_ou_criar_data_fk(conn, date.today().strftime("%Y-%m-%d"))
        
        conn.commit()
        print("Banco de dados CPD inicializado com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao inicializar o banco de dados: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
