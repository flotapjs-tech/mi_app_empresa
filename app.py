from flask import session, request
from datetime import datetime, timedelta, date
from flask import redirect, url_for, flash
from flask import Flask, render_template, request
import sqlite3
import psycopg2
import os
from functools import wraps
from flask import session, redirect
from werkzeug.security import check_password_hash
import os
from werkzeug.utils import secure_filename
import re
import hashlib
from psycopg2.extras import RealDictCursor


app = Flask(__name__)

app.secret_key = "080980110980060681"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://empresa_3cu1_user:XV5AVy6PHS4KPU2cqRjqv6Y1zjr8WauW@dpg-d8661bb7uimc73c0s6bg-a.virginia-postgres.render.com/empresa_3cu1"
)


def get_connection():

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )

try:
    conn = get_connection()
    print("POSTGRES CONECTADO OK")
    conn.close()

except Exception as e:
    print("ERROR POSTGRES:", e)

def obtener_turno_y_fecha(fecha_str, hora_str):

    fecha = datetime.strptime(
        fecha_str,
        "%Y-%m-%d"
    ).date()

    hora = datetime.strptime(
        hora_str,
        "%H:%M"
    ).time()

    # =========================
    # TURNO MAÑANA
    # =========================
    if 6 <= hora.hour < 18:

        turno = "dia"
        fecha_busqueda = fecha

    # =========================
    # TURNO NOCHE
    # =========================
    else:

        turno = "noche"

        # madrugada → pertenece al día anterior
        if hora.hour < 6:

            fecha_busqueda = fecha - timedelta(days=1)

        else:

            fecha_busqueda = fecha

    return turno, fecha_busqueda.isoformat()

def buscar_conductor_automatico(
    cursor,
    vehiculo_id,
    fecha,
    hora
):

    turno, fecha_busqueda = obtener_turno_y_fecha(
        fecha,
        hora
    )

    cursor.execute("""
        SELECT conductor_id
        FROM asignaciones
        WHERE vehiculo_id = %s
        AND fecha = %s
        AND turno = %s
    """, (
        vehiculo_id,
        fecha_busqueda,
        turno
    ))

    res = cursor.fetchone()

    return res["conductor_id"] if res else None


def login_requerido(f):
    @wraps(f)
    def funcion_protegida(*args, **kwargs):
        if "usuario" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return funcion_protegida



# Crear base de datos si no existe
'''def crear_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conductores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS adelantos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conductor_id INTEGER,
            monto REAL,
            fecha TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           usuario TEXT UNIQUE,
           password TEXT 
        )
    """)

    usuarios = [
                ("fumon1", "frpijos"),
                ("Gerente Moncho", "lbpijos"),
                ("fumon3", "jbpijos"),
                ("socio4", "1234"),
    ] 

    cursor.execute("""
         CREATE TABLE IF NOT EXISTS vehiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auto TEXT,
            patente TEXT,
            modelo TEXT,
            vtv TEXT,
            remis TEXT,  
            gnc TEXT,
            tubo TEXT                          
        )
    """)             
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehiculo_id INTEGER,
            mes TEXT,       
            seguro REAL,
            patente REAL,
            vtv REAL,
            satelital REAL       
        )
    """)

    cursor.execute("""               
        CREATE TABLE IF NOT EXISTS gastos_mensuales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehiculo_id INTEGER,
            mes TEXT,
            seguro REAL,
            patente REAL,
            vtv REAL,
            satelital REAL,
            mecanica REAL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mecanica (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehiculo_id INTEGER,
            fecha TEXT,
            descripcion TEXT,
            monto REAL,
            kilometros REAL
        )      
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asignaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conductor_id INTEGER,
            vehiculo_id INTEGER,
            fecha TEXT,
            turno TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS infracciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT,
            vehiculo_id INTEGER,
            conductor_id INTEGER,
            fecha TEXT,
            hora TEXT,
            jurisdiccion TEXT, -- capital / provincia
            monto REAL,
            fecha_vencimiento TEXT,
            estado TEXT,
            hash_unico TEXT,
            fecha_carga TEXT,
            pagada INTEGER DEFAULT 0,   
            FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id),
            FOREIGN KEY (conductor_id) REFERENCES conductores(id)
        );     
    """)

    from werkzeug.security import generate_password_hash  

    for u, p in usuarios:
        try:
            cursor.execute(
            "INSERT INTO usuarios (usuario, password) VALUES (%s, %s)",
            (u, generate_password_hash(p))
        )
        except:
         pass


    conn.commit()
    conn.close()

crear_db()
'''
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM usuarios WHERE usuario = %s", (usuario,))
        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session["usuario"] = user["usuario"]
            return redirect("/")
        else:
            return "Usuario o contraseña incorrectos"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
@login_requerido
def inicio():
    return render_template("index.html")


@app.route("/conductores", methods=["GET", "POST"])
@login_requerido
def conductores():

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"]
        dni = request.form["dni"]
        licencia_vencimiento = request.form["licencia_vencimiento"]
        cbu = request.form["cbu"]

        # 📁 ARCHIVOS
        carpeta = "static/uploads/"

        licencia_frente = request.files["licencia_frente"]
        licencia_dorso = request.files["licencia_dorso"]
        dni_frente = request.files["dni_frente"]
        dni_dorso = request.files["dni_dorso"]
        contrato = request.files["contrato"]

        def guardar_archivo(archivo):
            if archivo and archivo.filename != "":
                nombre = secure_filename(archivo.filename)
                ruta = os.path.join(carpeta, nombre)
                archivo.save(ruta)
                return nombre
            return ""

        nombre_lic_frente = guardar_archivo(licencia_frente)
        nombre_lic_dorso = guardar_archivo(licencia_dorso)
        nombre_dni_frente = guardar_archivo(dni_frente)
        nombre_dni_dorso = guardar_archivo(dni_dorso)
        nombre_contrato = guardar_archivo(contrato)

        # guardar en DB
        cursor.execute("""
            INSERT INTO conductores 
            (nombre, dni, licencia_vencimiento, cbu, licencia_frente, licencia_dorso, dni_frente, dni_dorso, contrato)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            nombre,
            dni,
            licencia_vencimiento,
            cbu,
            nombre_lic_frente,
            nombre_lic_dorso,
            nombre_dni_frente,
            nombre_dni_dorso,
            nombre_contrato
        ))

        conn.commit()

    # traer datos
    cursor.execute("SELECT * FROM conductores")
    datos = cursor.fetchall()

    

    conn.close()

    datos_procesados = []

    for d in datos:

        alerta = ""

        if d["licencia_vencimiento"]:

            fecha_vto = d["licencia_vencimiento"]

            # si viene como string
            if isinstance(fecha_vto, str):
                fecha_vto = datetime.strptime(fecha_vto, "%Y-%m-%d")

            hoy = datetime.now().date()

            if fecha_vto < hoy:
                alerta = "vencido"

            elif fecha_vto <= hoy + timedelta(days=30):
                alerta = "por_vencer"

        datos_procesados.append({
            "id": d["id"],
            "nombre": d["nombre"],
            "dni": d["dni"],
            "vto": d["licencia_vencimiento"],
            "cbu": d["cbu"],
            "lic_frente": d["licencia_frente"],
            "lic_dorso": d["licencia_dorso"],
            "dni_frente": d["dni_frente"],
            "dni_dorso": d["dni_dorso"],
            "contrato": d["contrato"],
            "alerta": alerta
        })

    return render_template(
        "conductores.html",
        datos=datos_procesados
    )



@app.route("/eliminar_conductor/<int:id>")
@login_requerido
def eliminar_conductor(id):

    conn = get_connection()
    cursor = conn.cursor()

    # 👉 traer archivos antes de borrar
    cursor.execute("""
        SELECT licencia_frente, licencia_dorso, dni_frente, dni_dorso, contrato
        FROM conductores
        WHERE id = %s
    """, (id,))
    
    archivos = cursor.fetchone()

    carpeta = "static/uploads/"

    # 👉 borrar archivos del disco
    if archivos:
        for archivo in archivos:
            if archivo:
                ruta = os.path.join(carpeta, archivo)
                if os.path.exists(ruta):
                    os.remove(ruta)

    # 👉 borrar de la DB
    cursor.execute("DELETE FROM conductores WHERE id = %s", (id,))
    conn.commit()
    conn.close()

    return redirect("/conductores")

@app.route("/editar_conductor/<int:id>", methods=["GET", "POST"])
@login_requerido
def editar_conductor(id):

    conn = get_connection()
    cursor = conn.cursor()

    carpeta = "static/uploads/"

    if request.method == "POST":
        nombre = request.form["nombre"]
        dni = request.form["dni"]
        licencia_vencimiento = request.form["licencia_vencimiento"]
        cbu = request.form["cbu"]

        # 👉 traer archivos actuales
        cursor.execute("""
            SELECT licencia_frente, licencia_dorso, dni_frente, dni_dorso, contrato
            FROM conductores WHERE id = %s
        """, (id,))
        actuales = cursor.fetchone()

        def reemplazar_archivo(nuevo, actual):
            if nuevo and nuevo.filename != "":
                # borrar viejo
                if actual:
                    ruta = os.path.join(carpeta, actual)
                    if os.path.exists(ruta):
                        os.remove(ruta)

                # guardar nuevo
                nombre_archivo = secure_filename(nuevo.filename)
                nuevo.save(os.path.join(carpeta, nombre_archivo))
                return nombre_archivo

            return actual

        licencia_frente = reemplazar_archivo(request.files["licencia_frente"], actuales[0])
        licencia_dorso = reemplazar_archivo(request.files["licencia_dorso"], actuales[1])
        dni_frente = reemplazar_archivo(request.files["dni_frente"], actuales[2])
        dni_dorso = reemplazar_archivo(request.files["dni_dorso"], actuales[3])
        contrato = reemplazar_archivo(request.files["contrato"], actuales[4])

        cursor.execute("""
            UPDATE conductores SET
            nombre=%s, dni=%s, licencia_vencimiento=%s, cbu=%s,
            licencia_frente=%s, licencia_dorso=%s,
            dni_frente=%s, dni_dorso=%s, contrato=%s
            WHERE id=%s
        """, (
            nombre, dni, licencia_vencimiento, cbu,
            licencia_frente, licencia_dorso,
            dni_frente, dni_dorso, contrato, id
        ))

        conn.commit()
        conn.close()
        return redirect("/conductores")

    cursor.execute("SELECT * FROM conductores WHERE id = %s", (id,))
    conductor = cursor.fetchone()

    conn.close()

    return render_template("editar_conductor.html", conductor=conductor)

@app.route('/asignaciones', methods=['GET', 'POST'])
@login_requerido
def asignaciones():

    conn = get_connection()
    cursor = conn.cursor()

    hoy = date.today().isoformat()

    # ======================
    # POST
    # ======================
    if request.method == 'POST':

        conductor_id = request.form.get('conductor_id')
        vehiculo_id = request.form.get('vehiculo_id')
        fecha = request.form.get('fecha') or hoy
        turno = request.form.get('turno')

        # ======================
        # VALIDACIÓN
        # ======================
        if not all([
            conductor_id,
            vehiculo_id,
            fecha,
            turno
        ]):
            return "Faltan datos"

        # ======================
        # VEHÍCULO DUPLICADO
        # ======================
        cursor.execute("""
            SELECT 1
            FROM asignaciones
            WHERE fecha = %s
            AND turno = %s
            AND vehiculo_id = %s
            LIMIT 1
        """, (
            fecha,
            turno,
            vehiculo_id
        ))

        if cursor.fetchone():
            return "Ese vehículo ya está asignado en ese turno"

        # ======================
        # CONDUCTOR DUPLICADO
        # ======================
        cursor.execute("""
            SELECT 1
            FROM asignaciones
            WHERE fecha = %s
            AND turno = %s
            AND conductor_id = %s
            LIMIT 1
        """, (
            fecha,
            turno,
            conductor_id
        ))

        if cursor.fetchone():
            return "Ese conductor ya tiene un vehículo en ese turno"

        # ======================
        # INSERT
        # ======================
        cursor.execute("""
            INSERT INTO asignaciones
            (
                conductor_id,
                vehiculo_id,
                fecha,
                turno
            )
            VALUES (%s, %s, %s, %s)
        """, (
            conductor_id,
            vehiculo_id,
            fecha,
            turno
        ))

        conn.commit()

        return redirect(
            f'/asignaciones%sfecha={fecha}'
        )

    # ======================
    # FILTROS
    # ======================
    historial = request.args.get('historial')
    hoy_filtro = request.args.get('hoy')
    fecha = request.args.get('fecha')
    turno = request.args.get('turno')
    vehiculo_id = request.args.get('vehiculo_id')

    # ======================
    # LÓGICA FECHA
    # ======================
    if historial:
        fecha = None

    elif hoy_filtro:
        fecha = hoy

    # ======================
    # QUERY BASE
    # ======================
    query = """
        SELECT

            a.*,
            c.nombre,
            v.auto,
            v.patente

        FROM asignaciones a

        JOIN conductores c
            ON a.conductor_id = c.id

        JOIN vehiculos v
            ON a.vehiculo_id = v.id

        WHERE 1=1
    """

    params = []

    # ======================
    # FILTROS
    # ======================
    if fecha:
        query += " AND a.fecha = %s"
        params.append(fecha)

    if turno:
        query += " AND a.turno = %s"
        params.append(turno)

    if vehiculo_id:
        query += " AND a.vehiculo_id = %s"
        params.append(vehiculo_id)

    # ======================
    # ORDEN
    # ======================
    query += """
        ORDER BY
            a.fecha DESC,
            a.turno
    """

    cursor.execute(query, params)

    asignaciones = cursor.fetchall()

    # ======================
    # SELECTS
    # ======================
    cursor.execute("""
        SELECT *
        FROM conductores
        ORDER BY nombre
    """)

    conductores = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM vehiculos
        ORDER BY patente
    """)

    vehiculos = cursor.fetchall()

    conn.close()

    return render_template(
        'asignaciones.html',
        asignaciones=asignaciones,
        conductores=conductores,
        vehiculos=vehiculos,
        fecha=fecha
    )


@app.route('/eliminar_asignacion/<int:id>', methods=['POST'])
@login_requerido
def eliminar_asignacion(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM asignaciones WHERE id = %s", (id,))

    conn.commit()
    conn.close()

    return redirect('/asignaciones')

@app.route('/adelantos')
@login_requerido
def adelantos():

    conn = get_connection()
    cursor = conn.cursor()

    conductor_id = request.args.get('conductor_id')
    fecha_desde = request.args.get('desde')
    fecha_hasta = request.args.get('hasta')

    params = []

    # 🔹 MODO RESUMEN (TODOS)
    if not conductor_id or conductor_id == "todos":

        modo = "resumen"

        query = """
            SELECT 
                c.nombre as conductor,
                c.id as conductor_id,
                COUNT(a.id) as cantidad,
                COALESCE(SUM(a.monto), 0) as total            
            FROM conductores c
            LEFT JOIN adelantos a ON c.id = a.conductor_id
            WHERE 1=1
        """

        if fecha_desde:
            query += " AND a.fecha >= %s"
            params.append(fecha_desde)

        if fecha_hasta:
            query += " AND a.fecha <= %s"
            params.append(fecha_hasta)

        query += """
            GROUP BY c.id
            ORDER BY total DESC
        """

        cursor.execute(query, params)
        adelantos = cursor.fetchall()

        # total general del resumen
        total = sum([a["total"] for a in adelantos]) if adelantos else 0

    # 🔹 MODO DETALLE (UN CONDUCTOR)
    else:

        modo = "detalle"

        query = """
            SELECT a.*, c.nombre as conductor,
            c.id as conductor_id
            FROM adelantos a
            JOIN conductores c ON a.conductor_id = c.id
            WHERE a.conductor_id = %s
        """

        params.append(conductor_id)

        if fecha_desde:
            query += " AND a.fecha >= %s"
            params.append(fecha_desde)

        if fecha_hasta:
            query += " AND a.fecha <= %s"
            params.append(fecha_hasta)

        query += " ORDER BY a.fecha DESC"

        cursor.execute(query, params)
        adelantos = cursor.fetchall()

        total = sum([a["monto"] for a in adelantos]) if adelantos else 0

    # 🔹 conductores para el select
    cursor.execute("SELECT * FROM conductores")
    conductores = cursor.fetchall()

    conn.close()

    return render_template(
        "adelantos.html",
        adelantos=adelantos,
        total=total,
        modo=modo,
        conductores=conductores
    )

@app.route('/guardar_adelanto', methods=['POST'])
@login_requerido
def guardar_adelanto():

    conn = get_connection()
    cursor = conn.cursor()

    conductor_id = request.form.get('conductor_id')
    monto = request.form.get('monto')
    fecha = request.form.get('fecha')

    # 🔴 validación básica
    if not conductor_id or not monto or not fecha:
        return "Error: faltan datos"

    cursor.execute("""
        INSERT INTO adelantos (conductor_id, monto, fecha)
        VALUES (%s, %s, %s)
    """, (conductor_id, monto, fecha))

    conn.commit()
    conn.close()

    return redirect('/adelantos')

@app.route('/eliminar_adelanto/<int:id>', methods=['POST'])
@login_requerido
def eliminar_adelanto(id):
    conn = get_connection()
    cursor = conn.cursor()

    
    cursor.execute("DELETE FROM adelantos WHERE id = %s", (id,))
    conn.commit()
    conn.close()

    return redirect('/adelantos')

@app.route("/vehiculos", methods=["GET", "POST"])
@login_requerido
def vehiculos():

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        auto = request.form["auto"]
        patente = request.form["patente"]
        modelo = request.form["modelo"]
        vtv = request.form["vtv"]
        remis = request.form["remis"]
        gnc = request.form["gnc"]
        tubo = request.form["tubo"]

        cursor.execute("""
            INSERT INTO vehiculos (auto, patente, modelo, vtv, remis, gnc, tubo)
            VALUES ( %s, %s, %s, %s, %s, %s, %s)
        """, (auto, patente, modelo, vtv, remis, gnc, tubo))

        conn.commit()

    cursor.execute("SELECT * FROM vehiculos")
    lista = cursor.fetchall()

    conn.close()

    return render_template("vehiculos.html", vehiculos=lista)

@app.route('/editar_vehiculo/<int:id>', methods=['GET', 'POST'])
def editar_vehiculo(id):
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        vtv = request.form['vtv']
        remis = request.form['remis']
        gnc = request.form['gnc']
        tubo = request.form['tubo']

        cursor.execute("""
            UPDATE vehiculos
            SET vtv = %s, remis = %s, gnc = %s, tubo = %s
            WHERE id = %s
        """, (vtv, remis, gnc, tubo, id))

        conn.commit()
        conn.close()
        return redirect('/vehiculos')

    cursor.execute("SELECT * FROM vehiculos WHERE id = %s", (id,))
    vehiculo = cursor.fetchone()

    conn.close()

    return render_template('editar_vehiculo.html', vehiculo=vehiculo)


@app.route('/eliminar_vehiculo/<int:id>', methods=['POST'])
@login_requerido
def eliminar_vehiculo(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM vehiculos WHERE id = %s", (id,))

    conn.commit()
    conn.close()

    return redirect('/vehiculos')

@app.route("/vencimientos")
@login_requerido
def vencimientos():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT v.id, ve.auto, ve.patente, v.vtv, v.remis, v.gnc, v.tubo
        FROM vencimientos v
        JOIN vehiculos ve ON v.vehiculo_id = ve.id
    """)

    datos = cursor.fetchall()
    conn.close()

    return render_template("vencimientos.html", datos=datos)

@app.route("/gastos", methods=["GET", "POST"])
@login_requerido
def gastos():
    conn = get_connection()
    cursor = conn.cursor()

    # 📌 Obtener mes (por defecto el actual)
    mes = request.args.get("mes")
    if not mes:
        from datetime import date
        mes = date.today().strftime("%Y-%m")

    # 📌 GUARDAR / ACTUALIZAR GASTOS
    if request.method == "POST":
        vehiculo_id = request.form["vehiculo_id"]
        mes_form = request.form["mes"]

        seguro = float(request.form.get("seguro") or 0)
        patente = float(request.form.get("patente") or 0)
        vtv = float(request.form.get("vtv") or 0)
        satelital = float(request.form.get("satelital") or 0)

        # 👉 Ver si ya existe gasto para ese vehículo y mes
        cursor.execute("""
            SELECT id FROM gastos
            WHERE vehiculo_id = %s AND mes = %s
        """, (vehiculo_id, mes_form))

        existe = cursor.fetchone()

        if existe:
            # UPDATE
            cursor.execute("""
                UPDATE gastos
                SET seguro=%s, patente=%s, vtv=%s, satelital=%s
                WHERE vehiculo_id=%s AND mes=%s
            """, (seguro, patente, vtv, satelital, vehiculo_id, mes_form))
        else:
            # INSERT
            cursor.execute("""
                INSERT INTO gastos (vehiculo_id, mes, seguro, patente, vtv, satelital)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (vehiculo_id, mes_form, seguro, patente, vtv, satelital))

        conn.commit()

    # 📌 TRAER DATOS (vehículos + gastos del mes)
    cursor.execute("""
    SELECT 
        v.id,
        v.auto,
        v.patente,

        COALESCE(g.seguro, 0) AS seguro,
        COALESCE(g.patente, 0) AS patente_gasto,
        COALESCE(g.vtv, 0) AS vtv,
        COALESCE(g.satelital, 0) AS satelital,

        COALESCE(SUM(m.monto), 0) AS mecanica

    FROM vehiculos v

    LEFT JOIN gastos g 
        ON v.id = g.vehiculo_id AND g.mes = %s

    LEFT JOIN mecanica m 
        ON v.id = m.vehiculo_id 
        AND strftime('%Y-%m', m.fecha) = %s

    GROUP BY v.id
""", (mes, mes))

    datos = cursor.fetchall()

    conn.close()

    return render_template(
        "gastos.html",
        datos=datos,
        mes=mes
    )

@app.route("/vehiculo/<int:id>")
@login_requerido
def vehiculo_detalle(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT fecha, descripcion, monto
        FROM mantenimiento_detalle
        WHERE vehiculo_id = %s
        ORDER BY fecha DESC
    """, (id,))

    detalle = cursor.fetchall()

    conn.close()

    return render_template("vehiculo_detalle.html", detalle=detalle)

@app.route("/mecanica", methods=["GET", "POST"])
@login_requerido
def mecanica():
    conn = get_connection()
    cursor = conn.cursor()

    # 👉 GUARDAR NUEVO REGISTRO
    if request.method == "POST":
        vehiculo_id = request.form["vehiculo_id"]
        fecha = request.form["fecha"]
        descripcion = request.form["descripcion"]
        monto = request.form["monto"]
        kilometros = request.form["kilometros"]

        cursor.execute("""
            INSERT INTO mecanica (vehiculo_id, fecha, descripcion, monto, kilometros)
            VALUES (%s, %s, %s, %s, %s)
        """, (vehiculo_id, fecha, descripcion, monto, kilometros))

        conn.commit()

    # 👉 TRAER VEHÍCULOS (para el select)
    cursor.execute("SELECT id, auto, patente FROM vehiculos")
    vehiculos = cursor.fetchall()

    # 👉 TRAER REGISTROS DE MECÁNICA
    vehiculo_id = request.args.get("vehiculo_id")
    mes = request.args.get("mes")
    
    query ="""
        SELECT m.id, v.auto, v.patente, m.fecha, m.descripcion, m.monto, m.kilometros
        FROM mecanica m
        JOIN vehiculos v ON m.vehiculo_id = v.id
        WHERE 1=1
        """
    params = []

    if vehiculo_id:
        query += "AND m.vehiculo_id = %s"
        params.append(vehiculo_id)

    if mes:
        query += "AND strftime('%Y-%m', m.fecha) = %s"
        params.append(mes)

    query += " ORDER BY m.fecha DESC"
    cursor.execute(query, params)        
    registros = cursor.fetchall()
    total = sum([r[5] for r in registros])

    cursor.execute("""
        SELECT v.auto, v.patente, SUM(m.monto)
        FROM mecanica m
        JOIN vehiculos v ON m.vehiculo_id = v.id
        GROUP BY m.vehiculo_id
     """)
    totales_vehiculo = cursor.fetchall()

    cursor.execute("""
        SELECT strftime('%Y-%m', fecha) as mes, SUM(monto)
        FROM mecanica
        GROUP BY mes
        ORDER BY mes DESC
    """)
    resumen_mensual = cursor.fetchall()

    conn.close()

    return render_template("mecanica.html",
        vehiculos=vehiculos, 
        registros=registros,
        total=total, vehiculo_id=vehiculo_id, 
        mes=mes, totales_vehiculo=totales_vehiculo, resumen_mensual=resumen_mensual)


@app.route('/infracciones', methods=['GET', 'POST'])
@login_requerido
def infracciones():

    conn = get_connection()
    cursor = conn.cursor()

    modo = request.args.get('modo', 'detalle')

    # =========================
    # POST
    # =========================
    if request.method == 'POST':

        numero = request.form.get('numero')
        fecha = request.form.get('fecha')
        hora = request.form.get('hora')
        jurisdiccion = request.form.get('jurisdiccion')
        monto = request.form.get('monto')
        fecha_vencimiento = request.form.get('fecha_vencimiento')
        vehiculo_id = request.form.get('vehiculo_id')

        if not vehiculo_id:
            return "Error: tenes que seleccionar un vehiculo"

        vehiculo_id = int(vehiculo_id)

        # =========================
        # ASIGNACIÓN AUTOMÁTICA
        # =========================
        conductor_id = buscar_conductor_automatico(
            cursor,
            vehiculo_id,
            fecha,
            hora
        )

        # =========================
        # INSERT
        # =========================
        cursor.execute("""
            INSERT INTO infracciones
            (
                numero,
                vehiculo_id,
                conductor_id,
                fecha,
                hora,
                jurisdiccion,
                monto,
                fecha_vencimiento
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            numero,
            vehiculo_id,
            conductor_id,
            fecha,
            hora,
            jurisdiccion,
            monto,
            fecha_vencimiento
        ))

        conn.commit()

        return redirect('/infracciones')

    # =========================
    # DETALLE
    # =========================
    if modo == 'detalle':

        cursor.execute("""
            SELECT
                i.*,
                v.patente,
                c.nombre,
                CASE 
                    WHEN datetime(i.fecha_carga) >= datetime('now', '-8 hours')
                    THEN 1
                     ELSE 0
                END as nueva
            FROM infracciones i
            LEFT JOIN vehiculos v
                ON i.vehiculo_id = v.id
            LEFT JOIN conductores c
                ON i.conductor_id = c.id
            ORDER BY i.fecha DESC, i.hora DESC
        """)

        infracciones = cursor.fetchall()

    # =========================
    # RESUMEN
    # =========================
    else:

        cursor.execute("""
            SELECT

                v.id,
                v.patente,

                COUNT(i.id) as cantidad_total,

                SUM(
                    CASE
                        WHEN i.jurisdiccion = 'CABA'
                        THEN 1
                        ELSE 0
                    END
                ) as cantidad_caba,

                SUM(
                    CASE
                        WHEN i.jurisdiccion = 'PROVINCIA'
                        THEN 1
                        ELSE 0
                    END
                ) as cantidad_provincia,

                SUM(
                    CASE
                        WHEN i.jurisdiccion = 'CABA'
                        THEN CAST(i.monto as REAL)
                        ELSE 0
                    END
                ) as monto_caba,

                SUM(
                    CASE
                        WHEN i.jurisdiccion = 'PROVINCIA'
                        THEN CAST(i.monto as REAL)
                        ELSE 0
                    END
                ) as monto_provincia,

                SUM(
                    CAST(i.monto as REAL)
                ) as monto_total

            FROM vehiculos v

            LEFT JOIN infracciones i
                ON v.id = i.vehiculo_id

            GROUP BY v.id

            ORDER BY cantidad_total DESC
        """)

        infracciones = cursor.fetchall()

    # =========================
    # VEHÍCULOS
    # =========================
    cursor.execute("""
        SELECT *
        FROM vehiculos
        ORDER BY patente
    """)

    vehiculos = cursor.fetchall()

    conn.close()

    from datetime import date

    hoy = date.today().isoformat()

    return render_template(
        "infracciones.html",
        infracciones=infracciones,
        hoy=hoy,
        vehiculos=vehiculos,
        modo=modo
   )

'''@app.route('/importar_infracciones', methods=['POST'])
@login_requerido
def importar_infracciones():

    conn = get_connection()
    cursor = conn.cursor()

    texto = request.form['texto']
    vehiculo_id = int(request.form['vehiculo_id'])
    jurisdiccion = request.form['jurisdiccion']

    lineas = [
        l.strip()
        for l in texto.split("\n")
        if l.strip()
    ]

    nuevas = 0
    duplicadas = 0
    errores = 0
    controlador = 0

    # =========================
    # TRAER DUPLICADOS UNA SOLA VEZ
    # =========================
    cursor.execute("""
        SELECT numero
        FROM infracciones
    """)

    numeros_existentes = {
        row["numero"]
        for row in cursor.fetchall()
    }

    # =========================
    # CACHE DE ASIGNACIONES
    # =========================
    cache_asignaciones = {}

    i = 0

    while i < len(lineas):

        try:

            linea1 = lineas[i]

            # =========================
            # NUMERO + FECHA + HORA
            # =========================
            match = re.search(
                r'Acta N[°º]([A-Z0-9]+)\s*-\s*(\d{4}-\d{2}-\d{2})\s*(\d{2}:\d{2})',
                linea1
            )

            if not match:
                i += 1
                continue

            numero = match.group(1)
            fecha = match.group(2)
            hora = match.group(3)

            # =========================
            # DUPLICADOS
            # =========================
            if numero in numeros_existentes:

                duplicadas += 1
                i += 3
                continue

            # =========================
            # MONTO + VENCIMIENTO
            # =========================
            # =========================
            monto = None
            fecha_vencimiento = None
            estado = "normal"

            j = i + 1

            while j < len(lineas):

                texto_linea = lineas[j].lower()

                # 🔴 CONTROLADOR
                if "controlador" in texto_linea:

                    estado = "controlador"
                    controlador += 1
                    break

                # 💲 MONTO
                if "$" in lineas[j]:

                    # 🟢 NORMAL
                    m2 = re.search(
                        r'\$[\d\.,]+\s+\$([\d\.,]+).*%s(\d{2}-\d{2}-\d{4})',
                        lineas[j]
                    )

                    if m2:

                        monto = (
                            m2.group(1)
                            .replace('.', '')
                            .replace(',', '.')
                        )

                        fecha_vencimiento = datetime.strptime(
                            m2.group(2),
                            "%d-%m-%Y"
                        ).date()

                        estado = "normal"

                        break

                    # 🔴 VENCIDA
                    m3 = re.search(
                        r'\$([\d\.,]+)',
                        lineas[j]
                    )

                    if m3:

                        monto = (
                            m3.group(1)
                            .replace('.', '')
                            .replace(',', '.')
                        )

                        estado = "vencida"

                        break

                j += 1

            # =========================
            # TURNO + FECHA REAL
            # =========================
            turno, fecha_busqueda = obtener_turno_y_fecha(
                fecha,
                hora
            )

            # =========================
            # CACHE KEY
            # =========================
            clave = (
                vehiculo_id,
                fecha_busqueda,
                turno
            )

            # =========================
            # BUSCAR CONDUCTOR
            # =========================
            if clave not in cache_asignaciones:

                cursor.execute("""
                    SELECT conductor_id
                    FROM asignaciones
                    WHERE vehiculo_id = %s
                    AND fecha = %s
                    AND turno = %s
                """, clave)

                res = cursor.fetchone()

                cache_asignaciones[clave] = (
                    res["conductor_id"]
                    if res else None
                )

            conductor_id = cache_asignaciones[clave]

            # =========================
            # INSERT
            # =========================
            cursor.execute("""
                INSERT INTO infracciones
                (
                    numero,
                    vehiculo_id,
                    conductor_id,
                    fecha,
                    hora,
                    jurisdiccion,
                    monto,
                    fecha_vencimiento,
                    estado
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                numero,
                vehiculo_id,
                conductor_id,
                fecha,
                hora,
                jurisdiccion,
                monto,
                fecha_vencimiento,
                estado
            ))

            numeros_existentes.add(numero)

            nuevas += 1
            i += 3

        except Exception as e:

            print("ERROR IMPORTANDO:", e)

            errores += 1
            i += 1

    conn.commit()
    conn.close()

    flash(
        f"""
        Importadas: {nuevas}
        | Duplicadas: {duplicadas}
        | Errores: {errores}
        | Controlador: {controlador}
        """
    )

    return redirect(url_for('infracciones'))
'''
@app.route('/infracciones_resumen')
@login_requerido
def infracciones_resumen():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.id, c.nombre, COUNT(i.id) as total
        FROM conductores c
        LEFT JOIN infracciones i ON c.id = i.conductor_id
        GROUP BY c.id
        ORDER BY total DESC
    """)

    resumen = cursor.fetchall()

    cursor.execute("SELECT * FROM vehiculos")
    vehiculos = cursor.fetchall()

    conn.close()

    return render_template("infracciones_resumen.html", resumen=resumen)

'''@app.route('/importar_infracciones', methods=['POST'])
@login_requerido
def importar_infracciones():

    conn = get_connection()
    cursor = conn.cursor()

    texto = request.form['texto']
    vehiculo_id = int(request.form['vehiculo_id'])
    jurisdiccion = request.form['jurisdiccion']

    bloques = texto.split("Esta es la foto de la infracción:")

    nuevas = 0
    duplicadas = 0
    errores = 0
    controlador = 0

    asignadas_por_conductor = {}

    for bloque in bloques:

        try:

            bloque = bloque.strip()

            # =========================
            # NÚMERO DE ACTA (opcional)
            # =========================
            acta = re.search(
                r'Acta\s*N[°º]%s\s*([A-Z0-9\-]+)',
                bloque,
                re.IGNORECASE
            )
            numero = None

            if acta:
                numero = (
                    acta.group(1)
                    .strip()
                    .replace("-", "")
                )

            numero = acta.group(1) if acta else None

            if not bloque:
                continue

            # =========================
            # FECHA Y HORA
            # =========================

            fecha = None
            hora = None

            # FORMATO NUEVO
            nuevo = re.search(
                r'(\d{2}-\d{2}-\d{4})\s+a las\s+(\d{2}:\d{2})',
                bloque
            )

            if nuevo:

                fecha = datetime.strptime(
                    nuevo.group(1),
                    "%d-%m-%Y"
                ).date().isoformat()

                hora = nuevo.group(2)

            else:

                # FORMATO VIEJO
                viejo = re.search(
                    r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})',
                    bloque
                )

                if viejo:

                    fecha = viejo.group(1)
                    hora = viejo.group(2)

            if not fecha or not hora:

                errores += 1
                continue
            
            # =========================
            # CONTROLADOR
            # =========================
            if "controlador" in bloque.lower():

                monto = None
                fecha_vencimiento = None
                estado = "controlador"

                controlador += 1

            else:

                # =========================
                # DESCUENTO + VENCIMIENTO
                # =========================
                descuento = re.search(
                    r'\\$([\d\.\,]+).%shasta el (\d{2}-\d{2}-\d{4})',
                    bloque,
                    re.IGNORECASE | re.DOTALL
                )

                if descuento:

                    monto = (
                        descuento.group(1)
                        .replace('.', '')
                        .replace(',', '.')
                    )

                    fecha_vencimiento = datetime.strptime(
                        descuento.group(2),
                        "%d-%m-%Y"
                    ).date()

                    estado = "normal"

                else:

                    # =========================
                    # BUSCAR CUALQUIER MONTO
                    # =========================
                    montos = re.findall(
                        r'\$([\d\.\,]+)',
                        bloque
                    )

                    if montos:

                        monto = (
                            montos[-1]
                            .replace('.', '')
                            .replace(',', '.')
                        )

                        fecha_vencimiento = None
                        estado = "vencida"

                    else:

                        errores += 1
                        continue

            # =========================
            # HASH ÚNICO
            # =========================
            texto_hash = f"""
                {numero}
                {vehiculo_id}
                {fecha}
                {hora}
                {monto}
            """

            hash_unico = hashlib.md5(
                texto_hash.encode()
            ).hexdigest()

            # =========================
            # DUPLICADOS
            # =========================
            if numero:

                cursor.execute("""
                    SELECT 1
                    FROM infracciones
                    WHERE numero = %s
                    LIMIT 1""", (numero,))

            else:    
                
                cursor.execute("""
                    SELECT 1
                    FROM infracciones
                    WHERE hash_unico = %s
                    LIMIT 1
                """, (hash_unico,))

            if cursor.fetchone():

                duplicadas += 1
                continue

            # =========================
            # ASIGNACIÓN AUTOMÁTICA
            # =========================
            conductor_id = buscar_conductor_automatico(
                cursor,
                vehiculo_id,
                fecha,
                hora
            )

            # =========================
            # INSERT
            # =========================


            cursor.execute("""
                INSERT INTO infracciones
                (
                    numero,
                    hash_unico,
                    vehiculo_id,
                    conductor_id,
                    fecha,
                    hora,
                    jurisdiccion,
                    monto,
                    fecha_vencimiento,
                    estado,
                    fecha_carga
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                numero,
                hash_unico,
                vehiculo_id,
                conductor_id,
                fecha,
                hora,
                jurisdiccion,
                monto,
                fecha_vencimiento,
                estado,
                datetime.now().isoformat()
            ))

            nuevas += 1

            # =========================
            # RESUMEN POR CONDUCTOR
            # =========================
            if conductor_id:

                cursor.execute("""
                    SELECT nombre
                    FROM conductores
                    WHERE id = %s
                """, (conductor_id,))

                conductor = cursor.fetchone()

                nombre = conductor["nombre"]

            else:
                nombre = "Sin asignar"

            asignadas_por_conductor[nombre] = (
                asignadas_por_conductor.get(nombre, 0) + 1
            )

        except:
            errores += 1

    conn.commit()
    conn.close()

    # =========================
    # FLASH FINAL
    # =========================
    detalle = " | ".join([
        f"{k}: {v}"
        for k, v in asignadas_por_conductor.items()
    ])

    flash(
        f"""
        Importadas: {nuevas}
        | Duplicadas: {duplicadas}
        | Errores: {errores}
        | Controlador: {controlador}

        | {detalle}
        """
    )

    return redirect(url_for('infracciones'))
'''

@app.route('/importar_infracciones', methods=['POST'])
@login_requerido
def importar_infracciones():

    conn = get_connection()
    cursor = conn.cursor()

    texto = request.form['texto']
    vehiculo_id = int(request.form['vehiculo_id'])
    jurisdiccion = request.form['jurisdiccion']

    # =========================
    # SEPARAR BLOQUES
    # =========================

    # 🔹 FORMATO NUEVO
    if "📄" in texto:

        bloques = re.findall(
            r'(📄.*%s)(%s=📄|\Z)',
            texto,
            re.DOTALL
        )

    # 🔹 FORMATO VIEJO
    else:

        bloques = re.split(
            r'(%s=Acta N[°º])',
            texto
        )

    bloques = [
        b.strip()
        for b in bloques
        if b.strip()
        and "Acta N" in b
    ]

    nuevas = 0
    duplicadas = 0
    errores = 0
    controlador = 0

    asignadas_por_conductor = {}

    # =========================
    # CACHE DUPLICADOS
    # =========================
    cursor.execute("""
        SELECT numero, hash_unico
        FROM infracciones
    """)

    infracciones_existentes = cursor.fetchall()

    numeros_existentes = {
        row["numero"]
        for row in infracciones_existentes
        if row["numero"]
    }

    hashes_existentes = {
        row["hash_unico"]
        for row in infracciones_existentes
        if row["hash_unico"]
    }

    # =========================
    # CACHE ASIGNACIONES
    # =========================
    cache_asignaciones = {}

    # =========================
    # RECORRER BLOQUES
    # =========================
    for bloque in bloques:

        try:

            bloque = bloque.strip()

            if not bloque:
                continue

            # =========================
            # NUMERO ACTA (OPCIONAL)
            # =========================
            acta = re.search(
                r'Acta\s*N[°º]%s\s*([A-Z0-9\-]+)',
                bloque,
                re.IGNORECASE
            )

            numero = None

            if acta:

                numero = (
                    acta.group(1)
                    .strip()
                    .replace("-", "")
                )

            # =========================
            # FECHA Y HORA
            # =========================
            fecha = None
            hora = None

            # =========================
            # FORMATO NUEVO
            # 03-04-2026 a las 05:07
            # =========================
            nuevo = re.search(
                r'(\d{2}-\d{2}-\d{4})\s+a las\s+(\d{2}:\d{2})',
                bloque,
                re.IGNORECASE
            )

            if nuevo:

                fecha = datetime.strptime(
                    nuevo.group(1),
                    "%d-%m-%Y"
                ).date().isoformat()

                hora = nuevo.group(2)

            else:

                # =========================
                # FORMATO VIEJO
                # 2025-04-03 05:07
                # =========================
                viejo = re.search(
                    r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})',
                    bloque,
                    re.IGNORECASE
                )

                if viejo:

                    fecha = viejo.group(1).strip()
                    hora = viejo.group(2).strip()

            # =========================
            # VALIDAR
            # =========================
            if not fecha or not hora:

                print("NO SE PUDO PARSEAR FECHA:")
                print(bloque)

                errores += 1
                continue

            # =========================
            # CONTROLADOR
            # =========================
            if "controlador" in bloque.lower():

                monto = None
                fecha_vencimiento = None
                estado = "controlador"

                controlador += 1

            else:

                # =========================
                # DESCUENTO + VENCIMIENTO
                # =========================
                descuento = re.search(
                    r'\$([\d\.\,]+).*%shasta el (\d{2}-\d{2}-\d{4})',
                    bloque,
                    re.IGNORECASE | re.DOTALL
                )

                if descuento:

                    monto = (
                        descuento.group(1)
                        .replace('.', '')
                        .replace(',', '.')
                    )

                    fecha_vencimiento = datetime.strptime(
                        descuento.group(2),
                        "%d-%m-%Y"
                    ).date()

                    estado = "normal"

                else:

                    # =========================
                    # MONTO VENCIDA
                    # =========================
                    montos = re.findall(
                        r'\$([\d\.\,]+)',
                        bloque
                    )

                    if montos:

                        monto = (
                            montos[-1]
                            .replace('.', '')
                            .replace(',', '.')
                        )

                        fecha_vencimiento = None
                        estado = "vencida"

                    else:

                        errores += 1
                        continue

            # =========================
            # HASH UNICO
            # =========================
            texto_hash = f"""
                {numero}
                {vehiculo_id}
                {fecha}
                {hora}
                {monto}
            """

            hash_unico = hashlib.md5(
                texto_hash.encode()
            ).hexdigest()

            # =========================
            # DUPLICADOS
            # =========================
            if numero:

                if numero in numeros_existentes:

                    duplicadas += 1
                    continue

            else:

                if hash_unico in hashes_existentes:

                    duplicadas += 1
                    continue

            # =========================
            # TURNO + FECHA BUSQUEDA
            # =========================
            turno, fecha_busqueda = obtener_turno_y_fecha(
                fecha,
                hora
            )

            # =========================
            # CACHE KEY
            # =========================
            clave = (
                vehiculo_id,
                fecha_busqueda,
                turno
            )

            # =========================
            # BUSCAR CONDUCTOR
            # =========================
            if clave not in cache_asignaciones:

                cursor.execute("""
                    SELECT conductor_id
                    FROM asignaciones
                    WHERE vehiculo_id = %s
                    AND fecha = %s
                    AND turno = %s
                """, clave)

                res = cursor.fetchone()

                cache_asignaciones[clave] = (
                    res["conductor_id"]
                    if res else None
                )

            conductor_id = cache_asignaciones[clave]

            # =========================
            # INSERT
            # =========================
            cursor.execute("""
                INSERT INTO infracciones
                (
                    numero,
                    hash_unico,
                    vehiculo_id,
                    conductor_id,
                    fecha,
                    hora,
                    jurisdiccion,
                    monto,
                    fecha_vencimiento,
                    estado,
                    fecha_carga
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                numero,
                hash_unico,
                vehiculo_id,
                conductor_id,
                fecha,
                hora,
                jurisdiccion,
                monto,
                fecha_vencimiento,
                estado,
                datetime.now().isoformat()
            ))

            # =========================
            # ACTUALIZAR CACHE
            # =========================
            if numero:
                numeros_existentes.add(numero)

            hashes_existentes.add(hash_unico)

            nuevas += 1

            # =========================
            # RESUMEN CONDUCTOR
            # =========================
            if conductor_id:

                cursor.execute("""
                    SELECT nombre
                    FROM conductores
                    WHERE id = %s
                """, (conductor_id,))

                conductor = cursor.fetchone()

                nombre = (
                    conductor["nombre"]
                    if conductor
                    else "Sin asignar"
                )

            else:

                nombre = "Sin asignar"

            asignadas_por_conductor[nombre] = (
                asignadas_por_conductor.get(nombre, 0) + 1
            )

        except Exception as e:

            print("ERROR IMPORTANDO:", e)

            errores += 1

    conn.commit()
    conn.close()

    # =========================
    # DETALLE FINAL
    # =========================
    detalle = " | ".join([
        f"{k}: {v}"
        for k, v in asignadas_por_conductor.items()
    ])

    # =========================
    # FLASH
    # =========================
    flash(
        f"""
        Importadas: {nuevas}
        | Duplicadas: {duplicadas}
        | Errores: {errores}
        | Controlador: {controlador}

        | {detalle}
        """
    )

    return redirect(url_for('infracciones'))

@app.route('/eliminar_infraccion/<int:id>')
@login_requerido
def eliminar_infraccion(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM infracciones WHERE id = %s", (id,))
    conn.commit()
    conn.close()

    return redirect(request.referrer)


@app.route('/infracciones_conductor/<int:conductor_id>')
@login_requerido
def infracciones_conductor(conductor_id):

    conn = get_connection()
    cursor = conn.cursor()

    conductor = None

    if conductor_id != 0:

        cursor.execute("""
            SELECT nombre FROM conductores 
            WHERE id = %s""", (conductor_id,))
        conductor = cursor.fetchone()


    # 🔹 CASO SIN ASIGNAR
    if conductor_id == 0:

        cursor.execute("""
            SELECT 
                i.id,
                i.fecha,
                i.hora,
                i.monto,
                i.fecha_vencimiento,
                i.pagada,
                v.patente,
                i.numero,
                i.vehiculo_id
            FROM infracciones i
            JOIN vehiculos v ON i.vehiculo_id = v.id
            WHERE i.conductor_id IS NULL
            ORDER BY i.fecha DESC, i.hora DESC
        """)

        nombre = "Sin asignar"

    # 🔹 CASO NORMAL
    else:

        cursor.execute("""
            SELECT 
                i.id,
                i.fecha,
                i.hora,
                i.monto,
                i.fecha_vencimiento,
                i.pagada,
                v.patente,
                i.numero,
                i.vehiculo_id
            FROM infracciones i
            JOIN vehiculos v ON i.vehiculo_id = v.id
            WHERE i.conductor_id = %s
            ORDER BY i.fecha DESC, i.hora DESC
        """, (conductor_id,))

        nombre = conductor["nombre"] if conductor else "Sin asignar"

    infracciones = cursor.fetchall()

    infracciones_final = []

    for i in infracciones:

        i = dict(i)

        if conductor_id == 0:

            # 🔹 turno real de la infracción
            turno, fecha_busqueda = obtener_turno_y_fecha(
                i["fecha"],
                i["hora"]
            )

            fecha_obj = datetime.strptime(
                fecha_busqueda,
                "%Y-%m-%d"
            ).date()

            # =========================
            # INFRACCIÓN EN TURNO DÍA
            # =========================
            if turno == "dia":

                # anterior = noche día anterior
                fecha_anterior = (
                    fecha_obj - timedelta(days=1)
                ).isoformat()

                turno_anterior = "noche"

                # siguiente = noche mismo día
                fecha_siguiente = fecha_obj.isoformat()

                turno_siguiente = "noche"

            # =========================
            # INFRACCIÓN EN TURNO NOCHE
            # =========================
            else:

                # anterior = día mismo día
                fecha_anterior = fecha_obj.isoformat()

                turno_anterior = "dia"

                # siguiente = día día siguiente
                fecha_siguiente = (
                    fecha_obj + timedelta(days=1)
                ).isoformat()

                turno_siguiente = "dia"

            # =========================
            # BUSCAR ANTERIOR
            # =========================
            cursor.execute("""
                SELECT c.nombre
                FROM asignaciones a
                JOIN conductores c
                    ON a.conductor_id = c.id
                WHERE a.vehiculo_id = %s
                AND a.fecha = %s
                AND a.turno = %s
            """, (
                i["vehiculo_id"],
                fecha_anterior,
                turno_anterior
            ))

            ant = cursor.fetchone()

            # =========================
            # BUSCAR SIGUIENTE
            # =========================
            cursor.execute("""
                SELECT c.nombre
                FROM asignaciones a
                JOIN conductores c
                    ON a.conductor_id = c.id
                WHERE a.vehiculo_id = %s
                AND a.fecha = %s
                AND a.turno = %s
            """, (
                i["vehiculo_id"],
                fecha_siguiente,
                turno_siguiente
            ))

            sig = cursor.fetchone()

            i["anterior"] = ant["nombre"] if ant else "-"
            i["siguiente"] = sig["nombre"] if sig else "-"
        
        infracciones_final.append(i)

    cursor.execute("""
        SELECT id, nombre
        FROM conductores
        ORDER BY nombre    
""")
    conductores = cursor.fetchall()

    conn.close()

    return render_template(
        "infracciones_detalle.html",
        infracciones=infracciones_final,
        conductor_id=conductor_id,
        nombre=nombre,
        es_sin_asignar=(conductor_id == 0),
        conductores=conductores
    )

@app.route('/infracciones_asignadas', methods=['GET'])
@login_requerido
def infracciones_asignadas():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT

        COALESCE(c.id, 0) as conductor_id,

        COALESCE(
            c.nombre,
            'Sin asignar'
        ) as nombre,

        COUNT(i.id) as total_infracciones,

        COUNT(
            CASE
                WHEN i.pagada = 1
                THEN 1
            END
        ) as total_pagadas,

        COUNT(
            CASE
                WHEN i.pagada = 0
                     OR i.pagada IS NULL
                THEN 1
            END
        ) as total_pendientes,

        SUM(
            CASE
                WHEN i.pagada = 0
                     OR i.pagada IS NULL
                THEN CAST(i.monto as REAL)

                ELSE 0
            END
        ) as monto_pendiente,

        SUM(
            CAST(i.monto as REAL)
        ) as monto_total,

        -- 🔥 NUEVAS
        SUM(
            CASE
                WHEN datetime(i.fecha_carga)
                     >= datetime('now', '-2 hours')

                THEN 1

                ELSE 0
            END
        ) as nuevas

        FROM infracciones i

        LEFT JOIN conductores c
            ON i.conductor_id = c.id

        GROUP BY COALESCE(c.id, 0)

        ORDER BY nuevas DESC,
                total_pendientes DESC
    """)

    resumen = cursor.fetchall()
    conn.close()

    return render_template("infracciones_asignadas.html", resumen=resumen)

@app.route('/asignar_infraccion/<int:id>', methods=['POST'])
@login_requerido
def asignar_infraccion(id):

    conductor_id = request.form.get('conductor_id')

    conn = get_connection()
    cursor = conn.cursor()

    if not conductor_id:
        flash("Tenes que seleccionar un conductor para asingar")
        return redirect(
            url_for(
                'infracciones_conductor', conductor_id=0
            )
        )

    cursor.execute("""
        UPDATE infracciones
        SET conductor_id = %s
        WHERE id = %s
    """, (conductor_id, id))

    conn.commit()
    conn.close()

    flash("Infracción asignada")
    return redirect(request.referrer)

@app.route("/marcar_pagada/<int:id>", methods=['GET',  'POST'])
@login_requerido
def marcar_pagada(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE infracciones
        SET pagada = 1
        WHERE id = %s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(request.referrer)

@app.route('/alertas')
@login_requerido
def alertas():

    from datetime import datetime, timedelta
    import sqlite3

    conn = get_connection()
    cursor = conn.cursor()

    hoy = datetime.today().date()
    limite = hoy + timedelta(days=7)

    # 🔴 LICENCIAS (conductores)
    cursor.execute("""
        SELECT nombre, licencia_vencimiento AS fecha
        FROM conductores
        WHERE licencia_vencimiento IS NOT NULL
        AND date(licencia_vencimiento) <= %s
        ORDER BY licencia_vencimiento
    """, (limite,))
    licencias_raw = cursor.fetchall()

    licencias = []
    for l in licencias_raw:
        l = dict(l)
        fecha = datetime.strptime(l["fecha"], "%Y-%m-%d").date()
        l["vencido"] = fecha <= hoy
        licencias.append(l)

    # 🔴 VEHÍCULOS (VTV / REMIS / GNC / TUBO)
    cursor.execute("""
        SELECT patente, 'VTV' as tipo, vtv as fecha
        FROM vehiculos
        WHERE vtv IS NOT NULL AND date(vtv) <= %s

        UNION ALL

        SELECT patente, 'REMIS', remis
        FROM vehiculos
        WHERE remis IS NOT NULL AND date(remis) <= %s

        UNION ALL

        SELECT patente, 'GNC', gnc
        FROM vehiculos
        WHERE gnc IS NOT NULL AND date(gnc) <= %s

        UNION ALL

        SELECT patente, 'TUBO', tubo
        FROM vehiculos
        WHERE tubo IS NOT NULL AND date(tubo) <= %s

        ORDER BY fecha
    """, (limite, limite, limite, limite))

    vehiculos_raw = cursor.fetchall()

    vehiculos = []
    for v in vehiculos_raw:
        v = dict(v)
        fecha = datetime.strptime(v["fecha"], "%Y-%m-%d").date()
        v["vencido"] = fecha <= hoy
        vehiculos.append(v)

    # 🔴 INFRACCIONES
    cursor.execute("""
        SELECT numero, monto, fecha_vencimiento AS fecha
        FROM infracciones
        WHERE fecha_vencimiento IS NOT NULL
        AND date(fecha_vencimiento) <= %s
        ORDER BY fecha_vencimiento
    """, (limite,))
    infracciones_raw = cursor.fetchall()

    infracciones = []
    for i in infracciones_raw:
        i = dict(i)
        fecha = datetime.strptime(i["fecha"], "%Y-%m-%d").date()
        i["vencido"] = fecha <= hoy
        infracciones.append(i)

        if i["fecha"]:
            fecha = datetime.strptime(i["fecha"], "%Y-%m-%d").date()
            i["vencido"] = fecha <= hoy
        else:
            i["vencido"] = False

    conn.close()

    total = len(licencias) + len(vehiculos) + len(infracciones)

    return render_template(
        'alertas.html',
        licencias=licencias,
        vehiculos=vehiculos,
        infracciones=infracciones,
        total=total,
        hoy=hoy
    )

@app.context_processor
def alertas_global():

    from datetime import datetime, timedelta
    import sqlite3

    conn = get_connection()
    cursor = conn.cursor()

    hoy = datetime.today().date()
    limite = hoy + timedelta(days=14)

    # conductores
    cursor.execute("""
        SELECT COUNT(*) as total
        FROM conductores
        WHERE licencia_vencimiento IS NOT NULL
        AND licencia_vencimiento != ''
        AND date(licencia_vencimiento) <= %s
    """, (limite,))
    lic = cursor.fetchone()["total"]

    # vehículos
    cursor.execute("""
        SELECT 
            (
                SELECT COUNT(*)
                FROM vehiculos
                WHERE vtv IS NOT NULL
                AND vtv != ''
                AND date(vtv) <= %s
            )
            +
            (
                SELECT COUNT(*)
                FROM vehiculos
                WHERE remis IS NOT NULL
                AND remis != ''
                AND date(remis) <= %s
            )
            +
            (
                SELECT COUNT(*)
                FROM vehiculos
                WHERE gnc IS NOT NULL
                AND gnc != ''
                AND date(gnc) <= %s
            )
            +
            (
                SELECT COUNT(*)
                FROM vehiculos
                WHERE tubo IS NOT NULL
                AND tubo != ''
                AND date(tubo) <= %s
            )
        AS total
    """, (limite, limite, limite, limite))

    veh = cursor.fetchone()["total"]

    # infracciones
    cursor.execute("""
        SELECT COUNT(*) as total
        FROM infracciones
        WHERE fecha_vencimiento IS NOT NULL
        AND fecha_vencimiento != ''
        AND date(fecha_vencimiento) <= %s
    """, (limite,))

    inf = cursor.fetchone()["total"]

    conn.close()

    return {
        "alertas_total": lic + veh + inf
    }

@app.route("/")
@login_requerido
def dashboard():
    conn = get_connection()
    cursor = conn.cursor()

    # Total conductores
    cursor.execute("SELECT COUNT(*) FROM conductores")
    total_conductores = cursor.fetchone()[0]

    # Total sueldos
    cursor.execute("SELECT SUM(sueldo) FROM conductores")
    total_sueldos = cursor.fetchone()[0] or 0

    # Total adelantos
    cursor.execute("SELECT SUM(monto) FROM adelantos")
    total_adelantos = cursor.fetchone()[0] or 0

    # Deuda total
    deuda_total = total_adelantos

    conn.close()

    return render_template("dashboard.html",
        total_conductores=total_conductores,
        total_sueldos=total_sueldos,
        total_adelantos=total_adelantos,
        deuda_total=deuda_total
    )




if __name__ == "__main__":
    app.run()