import os
DB_PATH = os.environ.get("DB_PATH", "database/banco.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    usuario TEXT UNIQUE NOT NULL,
    senha_hash BLOB NOT NULL,
    cargo TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS participantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_completo TEXT NOT NULL,
    data_nascimento TEXT,
    cpf TEXT UNIQUE NOT NULL,
    email TEXT,
    numero TEXT,
    nome_mae TEXT,
    congregacao TEXT NOT NULL,
    sexo TEXT,
    cargo_funcao TEXT,
    observacoes TEXT,
    valor_alvo REAL,
    status TEXT DEFAULT 'Em arrecadação',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

conn.execute("""
    CREATE TABLE IF NOT EXISTS historico_alteracoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        participante_id INTEGER NOT NULL,
        campo_alterado TEXT NOT NULL,
        valor_antigo TEXT,
        valor_novo TEXT,
        alterado_por TEXT,
        data_alteracao TEXT NOT NULL,
        FOREIGN KEY (participante_id) REFERENCES participantes(id)
    )
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS arrecadacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participante_id INTEGER NOT NULL,
    valor REAL NOT NULL,
    data_lancamento TEXT NOT NULL,
    observacao TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (participante_id) REFERENCES participantes(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS macros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS congregacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    macro_id INTEGER NOT NULL,
    FOREIGN KEY (macro_id) REFERENCES macros(id)
)
""")

conn.execute("""
    CREATE TABLE IF NOT EXISTS historico_alteracoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        participante_id INTEGER,
        campo_alterado TEXT,
        valor_antigo TEXT,
        valor_novo TEXT,
        alterado_por TEXT,
        data_alteracao TEXT
    )
""")


conn.commit()
conn.close()

print("Banco criado com sucesso!")