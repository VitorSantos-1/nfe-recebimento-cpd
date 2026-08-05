import os
import sqlite3
from database import init_db, get_connection, DB_PATH

def test_db_setup():
    print("--- Testando Inicialização do Banco ---")
    
    # 1. Apaga banco anterior se houver para teste limpo
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("Banco de teste antigo removido.")
        except OSError as e:
            print(f"Aviso ao remover banco de teste antigo: {e}")
            
    # 2. Inicializa o banco
    init_db()
    
    # 3. Valida a estrutura
    conn = get_connection()
    cursor = conn.cursor()
    
    # Verifica tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r["name"] for r in cursor.fetchall()]
    print("Tabelas criadas:", tables)
    
    # Validamos tabelas fundamentais
    required_tables = ["dim_loja", "dim_comprador", "dim_fornecedor", "dim_setor", "dim_ocorrencia", "dim_status", "dim_data", "dim_resolucao", "fact_recebimento"]
    for t in required_tables:
        assert t in tables, f"Erro: Tabela {t} não encontrada!"
    print("✓ Todas as tabelas necessárias foram encontradas.")

    # Verifica se os dados de semente foram populados
    cursor.execute("SELECT COUNT(*) as count FROM dim_loja")
    assert cursor.fetchone()["count"] > 0, "Erro: Lojas não foram inseridas!"
    
    cursor.execute("SELECT COUNT(*) as count FROM dim_setor")
    assert cursor.fetchone()["count"] > 0, "Erro: Setores não foram inseridos!"
    
    cursor.execute("SELECT COUNT(*) as count FROM dim_status")
    assert cursor.fetchone()["count"] > 0, "Erro: Status não foram inseridos!"

    cursor.execute("SELECT COUNT(*) as count FROM dim_resolucao")
    assert cursor.fetchone()["count"] > 0, "Erro: Regras de resolução não foram inseridas!"
    
    print("✓ Todos os dados de semente (seed) foram populados corretamente.")
    
    # Teste de chave estrangeira
    try:
        # Tenta inserir na fato com chaves inválidas (deve falhar se chaves estrangeiras estiverem ativas)
        cursor.execute("""
            INSERT INTO fact_recebimento (nota, data_fk, loja_fk, fornecedor_fk, status_fk)
            VALUES ('TEST-NF', 99999999, 999, 999, 999)
        """)
        conn.commit()
        print("❌ Erro: Chaves estrangeiras não estão ativas (permitiu FK inválido)!")
    except sqlite3.IntegrityError as e:
        print("✓ Validação de Chave Estrangeira funcionando com sucesso (falhou ao usar FK inválida):", e)
        
    conn.close()
    print("--- Teste do Banco Concluído com Sucesso! ---\n")

if __name__ == "__main__":
    test_db_setup()
