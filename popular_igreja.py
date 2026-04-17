import sqlite3

conn = sqlite3.connect("database/banco.db")
cursor = conn.cursor()

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

cursor.execute("SELECT id, nome FROM macros")
macro_map = {nome: id for id, nome in cursor.fetchall()}

dados = {
    "MACRO 1": ["Betesda", "El-Raah", "E. do Altíssimo", "Morada do Altíssimo", "Hebrom", "Shalom"],
    "MACRO 2": ["Alto Refúgio", "Jardim de Deus", "Jardim Celeste", "Manancial de Vida", "Monte Carmelo", "Orvalho de Hermon", "Rosa de Sarom", "Cafarnaum", "Ebenezer", "Monte Ararate"],
    "MACRO 3": ["Betânia", "Deus Forte", "Monte Hermon", "Monte Santo", "Monte Sinai", "Rio Jordão"],
    "MACRO 4": ["Adonai", "Fonte de Luz", "Gileade", "Rocha Eterna", "Vitória da Fé", "Monte Horebe", "Nova Jerusalém"],
    "MACRO 5": ["Monte das Oliveiras", "Monte Sião", "Nova Canaã", "Porta do Céu", "Nova Aliança", "Filadélfia", "Fonte de Águas Vivas"],
    "MACRO 6": ["Betel", "Monte Tabor", "Nova Sião", "Pioneira", "Monte Moriá", "Getsêmani", "Joia de Cristo", "Maranata", "Nova Vida", "Porta Formosa"],
    "MACRO MISSª": ["Luz do Mundo", "Vale de Benção", "Lírio dos Vales"]
}

for macro_nome, congregacoes in dados.items():
    macro_id = macro_map[macro_nome]

    for c in congregacoes:
        cursor.execute("""
            INSERT INTO congregacoes (nome, macro_id)
            VALUES (?, ?)
        """, (c, macro_id))

conn.commit()
conn.close()

print("Macros e congregações cadastradas com sucesso!")