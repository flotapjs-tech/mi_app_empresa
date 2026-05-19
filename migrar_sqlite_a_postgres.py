import sqlite3
import psycopg2

# =========================
# SQLITE
# =========================

sqlite_conn = sqlite3.connect("empresa.db")
sqlite_conn.row_factory = sqlite3.Row

sqlite_cursor = sqlite_conn.cursor()

# =========================
# POSTGRES
# =========================

DATABASE_URL = "postgresql://empresa_3cu1_user:XV5AVy6PHS4KPU2cqRjqv6Y1zjr8WauW@dpg-d8661bb7uimc73c0s6bg-a.virginia-postgres.render.com/empresa_3cu1"

pg_conn = psycopg2.connect(DATABASE_URL)

pg_cursor = pg_conn.cursor()

# =========================
# TABLAS
# =========================

tablas = [
    "conductores",
    "adelantos",
    "usuarios",
    "vehiculos",
    "gastos",
    "gastos_mensuales",
    "mecanica",
    "asignaciones",
    "infracciones"
]

# =========================
# MIGRACION
# =========================

for tabla in tablas:

    print(f"Migrando {tabla}...")

    sqlite_cursor.execute(f"SELECT * FROM {tabla}")

    filas = sqlite_cursor.fetchall()

    for fila in filas:

        columnas = fila.keys()

        valores = [fila[col] for col in columnas]

        placeholders = ", ".join(["%s"] * len(valores))

        columnas_sql = ", ".join(columnas)

        query = f"""
            INSERT INTO {tabla}
            ({columnas_sql})
            VALUES ({placeholders})
        """

        try:

            pg_cursor.execute(query, valores)

        except Exception as e:

            print(f"ERROR en {tabla}:", e)

            pg_conn.rollback()

    pg_conn.commit()

    print(f"{tabla} OK")

# =========================

sqlite_conn.close()

pg_conn.close()

print("MIGRACION COMPLETA OK")