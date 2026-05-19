import psycopg2

DATABASE_URL = "postgresql://empresa_3cu1_user:XV5AVy6PHS4KPU2cqRjqv6Y1zjr8WauW@dpg-d8661bb7uimc73c0s6bg-a.virginia-postgres.render.com/empresa_3cu1"

conn = psycopg2.connect(DATABASE_URL)

cursor = conn.cursor()

# =========================
# CONDUCTORES
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS conductores (
    id SERIAL PRIMARY KEY,
    nombre TEXT,
    dni TEXT,
    licencia_vencimiento TEXT,
    cbu TEXT,
    licencia_frente TEXT,
    licencia_dorso TEXT,
    dni_frente TEXT,
    dni_dorso TEXT,
    contrato TEXT
)
""")

# =========================
# ADELANTOS
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS adelantos (
    id SERIAL PRIMARY KEY,
    conductor_id INTEGER,
    monto REAL,
    fecha TEXT
)
""")

# =========================
# USUARIOS
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    usuario TEXT UNIQUE,
    password TEXT
)
""")

# =========================
# VEHICULOS
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS vehiculos (
    id SERIAL PRIMARY KEY,
    auto TEXT,
    patente TEXT,
    modelo TEXT,
    vtv TEXT,
    remis TEXT,
    gnc TEXT,
    tubo TEXT
)
""")

# =========================
# GASTOS
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS gastos (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER,
    mes TEXT,
    seguro REAL,
    patente REAL,
    vtv REAL,
    satelital REAL
)
""")

# =========================
# GASTOS MENSUALES
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS gastos_mensuales (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER,
    mes TEXT,
    seguro REAL,
    patente REAL,
    vtv REAL,
    satelital REAL,
    mecanica REAL
)
""")

# =========================
# MECANICA
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS mecanica (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER,
    fecha TEXT,
    descripcion TEXT,
    monto REAL,
    kilometros REAL
)
""")

# =========================
# ASIGNACIONES
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS asignaciones (
    id SERIAL PRIMARY KEY,
    conductor_id INTEGER,
    vehiculo_id INTEGER,
    fecha TEXT,
    turno TEXT
)
""")

# =========================
# INFRACCIONES
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS infracciones (
    id SERIAL PRIMARY KEY,
    numero TEXT,
    vehiculo_id INTEGER,
    conductor_id INTEGER,
    fecha TEXT,
    hora TEXT,
    jurisdiccion TEXT,
    monto REAL,
    fecha_vencimiento TEXT,
    estado TEXT,
    hash_unico TEXT,
    fecha_carga TEXT,
    pagada INTEGER DEFAULT 0
)
""")

conn.commit()

print("TABLAS POSTGRES CREADAS OK")

conn.close()