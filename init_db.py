import os
import bcrypt
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não configurada.")


def get_db():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha_hash BYTEA NOT NULL,
            cargo TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS macros (
            id SERIAL PRIMARY KEY,
            nome TEXT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS congregacoes (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            macro_id INTEGER REFERENCES macros(id) ON DELETE CASCADE,
            UNIQUE(nome, macro_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participantes (
            id SERIAL PRIMARY KEY,
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
            valor_alvo NUMERIC(10,2),
            status TEXT DEFAULT 'Em arrecadação',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS arrecadacoes (
            id SERIAL PRIMARY KEY,
            participante_id INTEGER NOT NULL REFERENCES participantes(id) ON DELETE CASCADE,
            valor NUMERIC(10,2) NOT NULL,
            data_lancamento TEXT NOT NULL,
            observacao TEXT,
            comprovante TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_alteracoes (
            id SERIAL PRIMARY KEY,
            participante_id INTEGER REFERENCES participantes(id) ON DELETE CASCADE,
            campo_alterado TEXT,
            valor_antigo TEXT,
            valor_novo TEXT,
            alterado_por TEXT,
            data_alteracao TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS caixa_movimentacoes (
            id SERIAL PRIMARY KEY,
            tipo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            descricao TEXT NOT NULL,
            valor NUMERIC(10,2) NOT NULL,
            data_movimento TEXT NOT NULL,
            observacao TEXT,
            criado_por TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    macros = [
        "MACRO 1",
        "MACRO 2",
        "MACRO 3",
        "MACRO 4",
        "MACRO 5",
        "MACRO 6",
        "MACRO MISSª"
    ]

    for macro in macros:
        cursor.execute("""
            INSERT INTO macros (nome)
            VALUES (%s)
            ON CONFLICT (nome) DO NOTHING
        """, (macro,))

    cursor.execute("SELECT id, nome FROM macros")
    macro_map = {row["nome"]: row["id"] for row in cursor.fetchall()}

    dados_congregacoes = {
        "MACRO 1": ["Betesda", "El-Raah", "E. do Altíssimo", "Morada do Altíssimo", "Hebrom", "Shalom"],
        "MACRO 2": ["Alto Refúgio", "Jardim de Deus", "Jardim Celeste", "Manancial de Vida", "Monte Carmelo", "Orvalho de Hermon", "Rosa de Sarom", "Cafarnaum", "Ebenezer", "Monte Ararate"],
        "MACRO 3": ["Betânia", "Deus Forte", "Monte Hermon", "Monte Santo", "Monte Sinai", "Rio Jordão"],
        "MACRO 4": ["Adonai", "Fonte de Luz", "Gileade", "Rocha Eterna", "Vitória da Fé", "Monte Horebe", "Nova Jerusalém"],
        "MACRO 5": ["Monte das Oliveiras", "Monte Sião", "Nova Canaã", "Porta do Céu", "Nova Aliança", "Filadélfia", "Fonte de Águas Vivas"],
        "MACRO 6": ["Betel", "Monte Tabor", "Nova Sião", "Pioneira", "Monte Moriá", "Getsêmani", "Joia de Cristo", "Maranata", "Nova Vida", "Porta Formosa"],
        "MACRO MISSª": ["Luz do Mundo", "Vale de Benção", "Lírio dos Vales"]
    }

    for macro_nome, congregacoes in dados_congregacoes.items():
        macro_id = macro_map.get(macro_nome)

        if macro_id:
            for nome in congregacoes:
                cursor.execute("""
                    INSERT INTO congregacoes (nome, macro_id)
                    VALUES (%s, %s)
                    ON CONFLICT (nome, macro_id) DO NOTHING
                """, (nome, macro_id))

    default_admin_user = os.environ.get("DEFAULT_ADMIN_USER")
    default_admin_password = os.environ.get("DEFAULT_ADMIN_PASSWORD")
    default_admin_name = os.environ.get("DEFAULT_ADMIN_NAME", "Administrador")
    default_admin_role = os.environ.get("DEFAULT_ADMIN_ROLE", "admin")

    if default_admin_user and default_admin_password:
        cursor.execute("""
            SELECT id FROM usuarios
            WHERE usuario = %s
        """, (default_admin_user,))

        user = cursor.fetchone()

        if not user:
            senha_hash = bcrypt.hashpw(default_admin_password.encode("utf-8"), bcrypt.gensalt())

            cursor.execute("""
                INSERT INTO usuarios (nome, usuario, senha_hash, cargo)
                VALUES (%s, %s, %s, %s)
            """, (default_admin_name, default_admin_user, senha_hash, default_admin_role))

    conn.commit()
    cursor.close()
    conn.close()

    print("Banco PostgreSQL criado com sucesso!")


if __name__ == "__main__":
    init_db()