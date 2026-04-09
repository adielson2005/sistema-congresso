import sqlite3

conn = sqlite3.connect("database/banco.db")
cursor = conn.cursor()

# MACROS
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
    cursor.execute("INSERT OR IGNORE INTO macros (nome) VALUES (?)", (macro,))

# Buscar os IDs das macros
cursor.execute("SELECT id, nome FROM macros")
macros_maps = {nome: id for id, nome in cursor.fetchall()}

# CONGREGAÇÕES
dados = {
    "MACRO 1": ["Betesda", "El-Raah", "E. do Altissimo", "Morada do Altissimo", "Hebrom", "Shalom"],

    "MACRO 2": ["Alto Refúgio", "Jardim de Deus", "Jardim Celeste", "Manancial de Vida", "Monte Carmelo",
                "Orvalho de Hermon", "Rosa de Sarom", "Cafarnaum", "Ebenezer", "Monte Ararate"],

    "MACRO 3": ["Betânia", "Deus Forte", "Monte Hermon", "Monte Santo", "Monte Sinai", "Rio Jordão"],

    "MACRO 4": ["Adonai", "Fonte de Luz", "Gileade", "Rocha Eterna", "Vitória da Fé", "Monte Horebe", "Nova Jerusalém"],

    "MACRO 5": ["Monte das Oliveiras", "Monte Sião", "Nova Canaã", "Porta do Céu",
                "Nova Aliança", "Filadélfia", "Fonte de Águas Vivas"],

    "MACRO 6": ["Betel", "Monte Tabor", "Nova Sião", "Pioneira", "Monte Moriá",
                "Getsêmani", "Joia de Cristo", "Maranata", "Nova Vida", "Porta Formosa"],

    "MACRO MISSª": ["Luz do Mundo", "Vale de Benção", "Lírio dos Vales"]
}

for macro_nome, congregacoes in dados.items():
    macro_id = macros_maps[macro_nome]

    for c in congregacoes:
        cursor.execute("""
            INSERT OR IGNORE INTO congregacoes (nome, macro_id)
            VALUES (?, ?)
        """, (c, macro_id))

conn.commit()
conn.close()

print("Macros e congregações cadastradas com sucesso!")