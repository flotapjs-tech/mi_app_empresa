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
import pandas as pd
from datetime import datetime, timedelta


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

def normalizar_hora(hora):

    hora = str(hora).strip()

    # excel suele agregar .0
    hora = hora.replace(".0", "")

    # si viene sin :
    if ":" not in hora:

        # completa ceros adelante
        hora = hora.zfill(6)

        return f"{hora[:2]}:{hora[2:4]}:{hora[4:6]}"

    return hora


def normalizar_tarifa(valor):

    valor = str(valor).strip()

    # formato tipo $4.177,59
    if "$" in valor or "," in valor:

        valor = valor.replace("$", "")
        valor = valor.replace(".", "")
        valor = valor.replace(",", ".")

    return float(valor)


def limpiar_patente(patente):

    return str(patente).strip().upper()

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
    cursor.execute("""
        SELECT *  
        FROM conductores
        ORDER BY activo DESC, nombre
                   """)
    datos = cursor.fetchall()

    

    conn.close()

    datos_procesados = []

    for d in datos:

        alerta = ""

        if d["licencia_vencimiento"]:

            fecha_vto = d["licencia_vencimiento"]

            # convertir si viene string
            if isinstance(fecha_vto, str):
                fecha_vto = datetime.strptime(
                    fecha_vto,
                    "%Y-%m-%d"
                ).date()

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
            "alerta": alerta,
            "activo": d["activo"]
        })

    return render_template(
        "conductores.html",
        datos=datos_procesados
    )

@app.route("/toggle_conductor/<int:id>", methods=["POST"])
@login_requerido
def toggle_conductor(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE conductores
        SET activo = NOT activo
        WHERE id = %s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/conductores")

@app.route("/eliminar_conductor/<int:id>")
@login_requerido
def eliminar_conductor(id):

    conn = get_connection()
    cursor = conn.cursor()

    # verificar si tiene infracciones asociadas
    cursor.execute("""
        SELECT COUNT(*)
        FROM infracciones
        WHERE conductor_id = %s
    """, (id,))
    
    fila = cursor.fetchone()
    total = fila["count"]

    # si tiene infracciones -> pedir confirmación
    if total > 0:
        conn.close()
        flash(
            f"No se puede eliminar porque este conductor tiene {total} infracciones asociadas. "
            f"Si continúa, quedarán como 'Sin asignar'. ¿Desea eliminar de todos modos?",
            "warning"
        )
        return redirect(url_for("conductores", confirmar_eliminar=id))

    # si no tiene -> borrar normal
    cursor.execute("""
        SELECT licencia_frente, licencia_dorso, dni_frente, dni_dorso, contrato
        FROM conductores
        WHERE id = %s
    """, (id,))
    
    archivos = cursor.fetchone()
    carpeta = "static/uploads/"

    # borrar archivos del disco
    if archivos:
        for archivo in archivos:
            if archivo:
                ruta = os.path.join(carpeta, archivo)
                if os.path.exists(ruta):
                    os.remove(ruta)

    # borrar conductor
    cursor.execute("""
        DELETE FROM conductores
        WHERE id = %s
    """, (id,))

    conn.commit()
    conn.close()

    flash("Conductor eliminado correctamente", "success")
    return redirect("/conductores")


@app.route("/confirmar_eliminar_conductor/<int:id>")
@login_requerido
def confirmar_eliminar_conductor(id):

    conn = get_connection()
    cursor = conn.cursor()

    # traer archivos antes de borrar
    cursor.execute("""
        SELECT licencia_frente, licencia_dorso, dni_frente, dni_dorso, contrato
        FROM conductores
        WHERE id = %s
    """, (id,))
    
    archivos = cursor.fetchone()
    carpeta = "static/uploads/"

    # borrar archivos físicos
    if archivos:
        for archivo in archivos:
            if archivo:
                ruta = os.path.join(carpeta, archivo)
                if os.path.exists(ruta):
                    os.remove(ruta)

    # dejar infracciones sin asignar
    cursor.execute("""
        UPDATE infracciones
        SET conductor_id = NULL
        WHERE conductor_id = %s
    """, (id,))

    # borrar conductor
    cursor.execute("""
        DELETE FROM conductores
        WHERE id = %s
    """, (id,))

    conn.commit()
    conn.close()

    flash(
        "Conductor eliminado. Las infracciones quedaron como 'Sin asignar'.",
        "success"
    )

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
        licencia_vencimiento = request.form["licencia_vencimiento"] or None
        cbu = request.form["cbu"]

        # traer archivos actuales
        cursor.execute("""
            SELECT 
                licencia_frente,
                licencia_dorso,
                dni_frente,
                dni_dorso,
                contrato
            FROM conductores
            WHERE id = %s
        """, (id,))

        actuales = cursor.fetchone()

        def reemplazar_archivo(nuevo, actual):

            if nuevo and nuevo.filename != "":

                # borrar archivo viejo
                if actual:
                    ruta_vieja = os.path.join(carpeta, actual)

                    if os.path.exists(ruta_vieja):
                        os.remove(ruta_vieja)

                # guardar nuevo
                nombre_archivo = secure_filename(nuevo.filename)
                ruta_nueva = os.path.join(carpeta, nombre_archivo)

                nuevo.save(ruta_nueva)

                return nombre_archivo

            return actual

        licencia_frente = reemplazar_archivo(
            request.files["licencia_frente"],
            actuales["licencia_frente"]
        )

        licencia_dorso = reemplazar_archivo(
            request.files["licencia_dorso"],
            actuales["licencia_dorso"]
        )

        dni_frente = reemplazar_archivo(
            request.files["dni_frente"],
            actuales["dni_frente"]
        )

        dni_dorso = reemplazar_archivo(
            request.files["dni_dorso"],
            actuales["dni_dorso"]
        )

        contrato = reemplazar_archivo(
            request.files["contrato"],
            actuales["contrato"]
        )

        cursor.execute("""
            UPDATE conductores
            SET
                nombre = %s,
                dni = %s,
                licencia_vencimiento = %s,
                cbu = %s,
                licencia_frente = %s,
                licencia_dorso = %s,
                dni_frente = %s,
                dni_dorso = %s,
                contrato = %s
            WHERE id = %s
        """, (
            nombre,
            dni,
            licencia_vencimiento,
            cbu,
            licencia_frente,
            licencia_dorso,
            dni_frente,
            dni_dorso,
            contrato,
            id
        ))

        conn.commit()
        conn.close()

        return redirect("/conductores")

    # GET
    cursor.execute("""
        SELECT *
        FROM conductores
        WHERE id = %s
    """, (id,))

    conductor = cursor.fetchone()

    conn.close()

    return render_template(
        "editar_conductor.html",
        conductor=conductor
    )


@app.route('/asignaciones', methods=['GET', 'POST'])
@login_requerido
def asignaciones():

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    hoy = date.today().isoformat()

    # ======================
    # POST
    # ======================
    if request.method == 'POST':
        try:
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
                flash("Faltan datos", "danger")
                return redirect('/asignaciones')

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
                flash(
                    "Ese vehículo ya está asignado en ese turno",
                    "warning"
                )
                return redirect(
                    f'/asignaciones?fecha={fecha}'
                )

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
                flash(
                    "Ese conductor ya tiene un vehículo en ese turno",
                    "warning"
                )
                return redirect(
                    f'/asignaciones?fecha={fecha}'
                )

            # ======================
            # REPARAR SECUENCIA
            # ======================
            cursor.execute("""
                SELECT setval(
                    pg_get_serial_sequence(
                        'asignaciones',
                        'id'
                    ),
                    COALESCE(
                        (
                            SELECT MAX(id)
                            FROM asignaciones
                        ),
                        1
                    )
                )
            """)

            # ======================
            # INSERT
            # ======================
            cursor.execute("""
                INSERT INTO asignaciones (
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

            flash(
                "Asignación creada correctamente",
                "success"
            )

            return redirect(
                f'/asignaciones?fecha={fecha}'
            )

        except Exception as e:
            conn.rollback()
            flash(
                f'Error al guardar asignación: {str(e)}',
                'danger'
            )

            return redirect('/asignaciones')

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
    # SELECT CONDUCTORES
    # ======================
    cursor.execute("""
        SELECT *
        FROM conductores
        WHERE activo = TRUE
        ORDER BY nombre
    """)
    conductores = cursor.fetchall()

    # ======================
    # SELECT VEHÍCULOS
    # ======================
    cursor.execute("""
        SELECT *
        FROM vehiculos
        ORDER BY patente
    """)
    vehiculos = cursor.fetchall()

    cursor.close()
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

    # =========================
    # MODO RESUMEN (TODOS)
    # =========================
    if not conductor_id or conductor_id == "todos":

        modo = "resumen"

        query = """
            SELECT
                c.nombre AS conductor,
                c.id AS conductor_id,
                COUNT(a.id) AS cantidad,
                COALESCE(SUM(a.monto), 0) AS total
            FROM conductores c
            LEFT JOIN adelantos a
                ON c.id = a.conductor_id
        """

        filtros = []

        if fecha_desde:
            filtros.append("a.fecha >= %s")
            params.append(fecha_desde)

        if fecha_hasta:
            filtros.append("a.fecha <= %s")
            params.append(fecha_hasta)

        if filtros:
            query += " WHERE " + " AND ".join(filtros)

        query += """
            GROUP BY c.id, c.nombre
            ORDER BY total DESC
        """

        cursor.execute(query, tuple(params))
        adelantos = cursor.fetchall()

        total = sum(a["total"] for a in adelantos) if adelantos else 0

    # =========================
    # MODO DETALLE (1 CONDUCTOR)
    # =========================
    else:

        modo = "detalle"

        query = """
            SELECT
                a.*,
                c.nombre AS conductor,
                c.id AS conductor_id
            FROM adelantos a
            JOIN conductores c
                ON a.conductor_id = c.id
            WHERE a.conductor_id = %s
        """

        params = [conductor_id]

        if fecha_desde:
            query += " AND a.fecha >= %s"
            params.append(fecha_desde)

        if fecha_hasta:
            query += " AND a.fecha <= %s"
            params.append(fecha_hasta)

        query += " ORDER BY a.fecha DESC"

        cursor.execute(query, tuple(params))
        adelantos = cursor.fetchall()

        total = sum(a["monto"] for a in adelantos) if adelantos else 0

    # conductores para el select
    cursor.execute("""
        SELECT id, nombre
        FROM conductores
        WHERE activo = TRUE
        ORDER BY nombre
    """)
    conductores = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "adelantos.html",
        adelantos=adelantos,
        total=total,
        modo=modo,
        conductores=conductores,
        conductor_id=conductor_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta
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


@app.route("/eliminar_adelanto/<int:id>", methods=["POST"])
@login_requerido
def eliminar_adelanto(id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM adelantos WHERE id = %s",
        (id,)
    )

    conn.commit()
    cursor.close()
    conn.close()

    flash("Adelanto eliminado correctamente")
    return redirect(url_for("adelantos"))


@app.route("/editar_adelanto/<int:id>", methods=["GET", "POST"])
@login_requerido
def editar_adelanto(id):

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        conductor_id = request.form["conductor_id"]
        monto = request.form["monto"]
        fecha = request.form["fecha"]
        

        cursor.execute("""
            UPDATE adelantos
            SET conductor_id=%s,
                monto=%s,
                fecha=%s               
            WHERE id=%s
        """, (
            conductor_id,
            monto,
            fecha,
            id
        ))

        conn.commit()
        conn.close()

        flash("Adelanto editado correctamente")
        return redirect(url_for("adelantos"))

    # GET
    cursor.execute("""
        SELECT *
        FROM adelantos
        WHERE id = %s
    """, (id,))

    adelanto = cursor.fetchone()

    cursor.execute("""
        SELECT id, nombre
        FROM conductores
        ORDER BY nombre
    """)

    conductores = cursor.fetchall()

    conn.close()

    return render_template(
        "editar_adelanto.html",
        adelanto=adelanto,
        conductores=conductores
    )


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

    # verificar si tiene infracciones asociadas
    cursor.execute("""
        SELECT COUNT(*)
        FROM infracciones
        WHERE vehiculo_id = %s
    """, (id,))

    fila = cursor.fetchone()
    total = fila["count"]

    # si tiene infracciones -> pedir confirmación
    if total > 0:
        conn.close()
        flash(
            f"Este vehículo tiene {total} infracciones asociadas. "
            f"Si lo eliminás, quedarán como 'Sin asignar'. ¿Desea eliminar igual?",
            "warning"
        )
        return redirect(url_for("vehiculos", confirmar_eliminar=id))

    # si no tiene -> borrar normal
    cursor.execute("""
        DELETE FROM vehiculos
        WHERE id = %s
    """, (id,))

    conn.commit()
    conn.close()

    flash("Vehículo eliminado correctamente", "success")
    return redirect('/vehiculos')


@app.route('/confirmar_eliminar_vehiculo/<int:id>')
@login_requerido
def confirmar_eliminar_vehiculo(id):

    conn = get_connection()
    cursor = conn.cursor()

    # dejar infracciones sin asignar
    cursor.execute("""
        UPDATE infracciones
        SET vehiculo_id = NULL
        WHERE vehiculo_id = %s
    """, (id,))

    # borrar vehículo
    cursor.execute("""
        DELETE FROM vehiculos
        WHERE id = %s
    """, (id,))

    conn.commit()
    conn.close()

    flash(
        "Vehículo eliminado. Las infracciones quedaron como 'Sin asignar'.",
        "success"
    )

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
            ON v.id = g.vehiculo_id
            AND g.mes = %s

        LEFT JOIN mecanica m
            ON v.id = m.vehiculo_id
            AND TO_CHAR(NULLIF(m.fecha, '')::date, 'YYYY-MM') = %s

        GROUP BY v.id, v.auto, v.patente,
                g.seguro, g.patente, g.vtv, g.satelital
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

    # =========================
    # GUARDAR NUEVO REGISTRO
    # =========================
    if request.method == "POST":
        vehiculo_id = request.form["vehiculo_id"]
        fecha = request.form["fecha"]  # formato: YYYY-MM-DD
        descripcion = request.form["descripcion"]
        monto = request.form["monto"]
        kilometros = request.form["kilometros"]

        cursor.execute("""
            INSERT INTO mecanica (vehiculo_id, fecha, descripcion, monto, kilometros)
            VALUES (%s, %s, %s, %s, %s)
        """, (vehiculo_id, fecha, descripcion, monto, kilometros))

        conn.commit()

    # =========================
    # VEHÍCULOS
    # =========================
    cursor.execute("SELECT id, auto, patente FROM vehiculos")
    vehiculos = cursor.fetchall()

    # =========================
    # FILTROS
    # =========================
    vehiculo_id = request.args.get("vehiculo_id")
    mes = request.args.get("mes")

    query = """
        SELECT
            m.id,
            v.auto,
            v.patente,
            m.fecha,
            m.descripcion,
            m.monto,
            m.kilometros
        FROM mecanica m
        JOIN vehiculos v ON m.vehiculo_id = v.id
        WHERE 1=1
    """

    params = []

    if vehiculo_id:
        query += " AND m.vehiculo_id = %s"
        params.append(vehiculo_id)

    # =========================
    # FILTRO MES (FIX SIN TO_CHAR)
    # =========================
    if mes:
        query += " AND m.fecha LIKE %s"
        params.append(f"{mes}%")

    query += " ORDER BY m.fecha DESC"

    cursor.execute(query, params)
    registros = cursor.fetchall()

    # =========================
    # TOTAL GENERAL
    # =========================
    total = sum(r["monto"] for r in registros)

    # =========================
    # TOTAL POR VEHÍCULO
    # =========================
    cursor.execute("""
        SELECT
            v.auto,
            v.patente,
            SUM(m.monto) AS total
        FROM mecanica m
        JOIN vehiculos v ON m.vehiculo_id = v.id
        GROUP BY v.auto, v.patente
    """)
    totales_vehiculo = cursor.fetchall()

    # =========================
    # RESUMEN MENSUAL (FIX SIN TO_CHAR)
    # =========================
    cursor.execute("""
        SELECT
            SUBSTRING(fecha, 1, 7) AS mes,
            SUM(monto) AS total
        FROM mecanica
        GROUP BY SUBSTRING(fecha, 1, 7)
        ORDER BY mes DESC
    """)
    resumen_mensual = cursor.fetchall()

    conn.close()

    return render_template(
        "mecanica.html",
        vehiculos=vehiculos,
        registros=registros,
        total=total,
        vehiculo_id=vehiculo_id,
        mes=mes,
        totales_vehiculo=totales_vehiculo,
        resumen_mensual=resumen_mensual
    )

@app.route('/eliminar_gasto_mecanica/<int:id>', methods=["POST"])
@login_requerido
def eliminar_gasto_mecanica(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM mecanica WHERE id = %s", (id,))
    conn.commit()
    conn.close()

    flash("reparacion eliminada")

    return redirect(request.referrer)

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
                    WHEN i.fecha_carga::timestamp >= NOW() - INTERVAL '8 hours'
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


@app.route('/infracciones_vehiculo/<int:vehiculo_id>')
@login_requerido
def infracciones_vehiculo(vehiculo_id):

    conn = get_connection()
    cursor = conn.cursor()

    # =========================
    # INFRACCIONES DEL VEHÍCULO
    # =========================
    cursor.execute("""
        SELECT
            i.*,
            v.patente,
            c.nombre,
            CASE
                WHEN i.fecha_carga::timestamp >= NOW() - INTERVAL '8 hours'
                THEN 1
                ELSE 0
            END AS nueva
        FROM infracciones i

        LEFT JOIN vehiculos v
            ON i.vehiculo_id = v.id

        LEFT JOIN conductores c
            ON i.conductor_id = c.id

        WHERE i.vehiculo_id = %s

        ORDER BY i.fecha DESC, i.hora DESC
    """, (vehiculo_id,))

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
        vehiculos=vehiculos,
        hoy=hoy,
        modo="detalle"
    )


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

    if "📄" in texto:

        bloques = re.findall(
            r'(📄.*?)(?=📄|\Z)',
            texto,
            re.DOTALL
        )

    else:

        bloques = re.split(
            r'(?=Acta N[°º])',
            texto
        )

    bloques = [
        b.strip()
        for b in bloques
        if b.strip() and "Acta N" in b
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
            # NUMERO ACTA
            # =========================

            acta = re.search(
                r'Acta\s*N[°º]\s*([A-Z0-9\-]+)',
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

            nuevo = re.search(
                r'(\d{2}-\d{2}-\d{4})\s+a las\s+(\d{2}:\d{2})',
                bloque,
                re.IGNORECASE
            )

            if nuevo:

                fecha = datetime.strptime(
                    nuevo.group(1),
                    "%d-%m-%Y"
                ).date()

                hora = nuevo.group(2)

            else:

                viejo = re.search(
                    r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})',
                    bloque,
                    re.IGNORECASE
                )

                if viejo:

                    fecha = datetime.strptime(
                        viejo.group(1),
                        "%Y-%m-%d"
                    ).date()

                    hora = viejo.group(2).strip()

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

                descuento = re.search(
                    r'\$([\d\.\,]+).*?hasta el (\d{2}-\d{2}-\d{4})',
                    bloque,
                    re.IGNORECASE | re.DOTALL
                )

                if descuento:

                    monto = float(
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

                    montos = re.findall(
                        r'\$([\d\.\,]+)',
                        bloque
                    )

                    if montos:

                        monto = float(
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
                fecha.isoformat(),
                hora
            )

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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
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
                estado
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


@app.route('/eliminar_infraccion/<int:id>')
@login_requerido
def eliminar_infraccion(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM infracciones WHERE id = %s", (id,))
    conn.commit()
    conn.close()

    flash("Infraccion Eliminada")

    return redirect(request.referrer)


@app.route('/infracciones_conductor/<int:conductor_id>')
@login_requerido
def infracciones_conductor(conductor_id):

    conn = get_connection()
    cursor = conn.cursor()

    conductor = None

    # =========================
    # TRAER CONDUCTOR
    # =========================
    if conductor_id != 0:

        cursor.execute("""
            SELECT nombre
            FROM conductores
            WHERE id = %s
        """, (conductor_id,))

        conductor = cursor.fetchone()

    # =========================
    # SIN ASIGNAR
    # =========================
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

            LEFT JOIN vehiculos v
                ON i.vehiculo_id = v.id

            LEFT JOIN conductores c
                ON i.conductor_id = c.id

            WHERE
                i.conductor_id IS NULL
                OR i.conductor_id = 0
                OR c.id IS NULL

            ORDER BY v.patente DESC, i.fecha DESC
        """)

        nombre = "Sin asignar"

    # =========================
    # CONDUCTOR NORMAL
    # =========================
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
            LEFT JOIN vehiculos v
                ON i.vehiculo_id = v.id
            WHERE i.conductor_id = %s
            ORDER BY i.fecha DESC, i.hora DESC
        """, (conductor_id,))

        nombre = conductor["nombre"] if conductor else "Sin asignar"

    infracciones = cursor.fetchall()

    infracciones_final = []

    # =========================
    # RECORRER INFRACCIONES
    # =========================
    for i in infracciones:

        i = dict(i)

        # =========================
        # SOLO PARA SIN ASIGNAR
        # =========================
        if conductor_id == 0:

            turno, fecha_busqueda = obtener_turno_y_fecha(
                str(i["fecha"]),
                i["hora"]
            )

            if isinstance(fecha_busqueda, str):

                fecha_obj = datetime.strptime(
                    fecha_busqueda,
                    "%Y-%m-%d"
                ).date()

            else:
                fecha_obj = fecha_busqueda

            # =========================
            # TURNO DIA
            # =========================
            if turno == "dia":

                fecha_anterior = fecha_obj - timedelta(days=1)
                turno_anterior = "noche"

                fecha_siguiente = fecha_obj
                turno_siguiente = "noche"

            # =========================
            # TURNO NOCHE
            # =========================
            else:

                fecha_anterior = fecha_obj
                turno_anterior = "dia"

                fecha_siguiente = fecha_obj + timedelta(days=1)
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
                AND a.fecha::date = %s
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
                AND a.fecha::date = %s
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

    # =========================
    # LISTA CONDUCTORES
    # =========================
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

            COALESCE(c.id, 0) AS conductor_id,
            COALESCE(c.nombre, 'Sin asignar') AS nombre,

            COUNT(i.id) AS total_infracciones,

            COUNT(*) FILTER (WHERE i.pagada = 1) AS total_pagadas,

            COUNT(*) FILTER (WHERE i.pagada = 0 OR i.pagada IS NULL) AS total_pendientes,

            COALESCE(
                SUM(i.monto::numeric) FILTER (
                    WHERE i.pagada = 0 OR i.pagada IS NULL
                ),
                0
            ) AS monto_pendiente,

            COALESCE(
                SUM(i.monto::numeric),
                0
            ) AS monto_total,

            COUNT(*) FILTER (
                WHERE i.fecha_carga::timestamp >= NOW() - INTERVAL '2 hours'
            ) AS nuevas

        FROM infracciones i

        LEFT JOIN conductores c
            ON i.conductor_id = c.id

        GROUP BY c.id, c.nombre

        ORDER BY nombre,
                total_pendientes ASC
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

@app.route("/peajes", methods=["GET", "POST"])
@login_requerido
def peajes():

    conn = get_connection()
    cursor = conn.cursor()

    # =========================
    # SUBIR CSV
    # =========================
    if request.method == "POST":

        archivo = request.files["archivo"]
        autopista = request.form.get("autopista")

        if archivo:

            df = pd.read_csv(
                archivo,
                sep=";"
                )
            df.columns = df.columns.str.strip().str.upper()

            print(df.columns)

            for _, row in df.iterrows():

                try:

                    estacion = str(row.get("ESTACION", "")).strip()                    

                    fecha = str(row.get("FECHA", "")).strip()

                    hora = normalizar_hora(row.get("HORA", ""))

                    patente = limpiar_patente(row.get("PATENTE", ""))

                    tarifa = normalizar_tarifa(row.get("TARIFA", 0))

                    conductor = None
                    conductor_id = None
                    vehiculo_id = None
                    turno = None

                    # 🔥 buscar vehículo
                    cursor.execute("""
                        SELECT id
                        FROM vehiculos
                        WHERE UPPER(patente) = %s
                    """, (patente,))

                    vehiculo = cursor.fetchone()

                    if vehiculo:

                        vehiculo_id = vehiculo["id"]

                        # 🔥 buscar conductor automático
                        conductor_id = buscar_conductor_automatico(
                            cursor,
                            vehiculo_id,
                            fecha,
                            hora[:5]
                        )

                        # 🔥 obtener turno
                        turno, _ = obtener_turno_y_fecha(
                            fecha,
                            hora[:5]
                        )

                        # 🔥 traer nombre conductor
                        if conductor_id:

                            cursor.execute("""
                                SELECT nombre
                                FROM conductores
                                WHERE id = %s
                            """, (conductor_id,))

                            conductor_data = cursor.fetchone()

                            if conductor_data:

                                conductor = conductor_data["nombre"]            

                    # 🔥 guardar peaje
                    cursor.execute("""
                        INSERT INTO peajes (
                            fecha,
                            hora,
                            patente,
                            tarifa,
                            autopista,
                            estacion,
                            vehiculo_id,
                            conductor_id,
                            conductor,
                            turno
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)

                        ON CONFLICT (
                            fecha,
                            hora,
                            patente,
                            tarifa,
                            estacion
                        )

                        DO NOTHING
                    """, (
                        fecha,
                        hora,
                        patente,
                        tarifa,
                        autopista,
                        estacion,
                        vehiculo_id,
                        conductor_id,
                        conductor,
                        turno
                    ))

                except Exception as e:

                    conn.rollback()

                    print("ERROR FILA:", e)

            conn.commit()

    # =========================
    # FILTROS
    # =========================

    desde = request.args.get("desde")
    hasta = request.args.get("hasta")

    query = """
        SELECT *
        FROM peajes
        WHERE 1=1
    """

    params = []

    if desde:

        query += " AND fecha >= %s"
        params.append(desde)

    if hasta:

        query += " AND fecha <= %s"
        params.append(hasta)

    query += """
        ORDER BY fecha DESC, hora DESC
        LIMIT 300
    """

    cursor.execute(query, params)

    registros = cursor.fetchall()

    # =========================
    # RESUMEN POR CONDUCTOR
    # =========================

    query_resumen = """
        SELECT
            COALESCE(conductor, 'SIN ASIGNAR') as conductor,
            COUNT(*) as cantidad,
            SUM(tarifa) as total
        FROM peajes
        WHERE 1=1
    """

    params_resumen = []

    if desde:

        query_resumen += " AND fecha >= %s"
        params_resumen.append(desde)

    if hasta:

        query_resumen += " AND fecha <= %s"
        params_resumen.append(hasta)

    query_resumen += """
        GROUP BY conductor
        ORDER BY total DESC
    """

    cursor.execute(
        query_resumen,
        params_resumen
    )

    resumen = cursor.fetchall()

    # =========================
    # TOTALES GENERALES
    # =========================

    query_totales = """
        SELECT
            COUNT(*) as cantidad_total,
            COALESCE(SUM(tarifa), 0) as monto_total
        FROM peajes
        WHERE 1=1
    """

    params_totales = []

    if desde:

        query_totales += " AND fecha >= %s"
        params_totales.append(desde)

    if hasta:

        query_totales += " AND fecha <= %s"
        params_totales.append(hasta)

    cursor.execute(
        query_totales,
        params_totales
    )

    totales = cursor.fetchone()

    # =========================
    # PEAJES SIN CONDUCTOR
    # =========================

    query_sin = """
        SELECT *
        FROM peajes
        WHERE conductor IS NULL
    """

    params_sin = []

    if desde:

        query_sin += " AND fecha >= %s"
        params_sin.append(desde)

    if hasta:

        query_sin += " AND fecha <= %s"
        params_sin.append(hasta)

    query_sin += """
        ORDER BY fecha DESC, hora DESC
    """

    cursor.execute(
        query_sin,
        params_sin
    )

    sin_conductor = cursor.fetchall()

    return render_template(
        "peajes.html",
        registros=registros,
        resumen=resumen,
        totales=totales,
        sin_conductor=sin_conductor,
        desde=desde,
        hasta=hasta
    )

@app.route('/alertas')
@login_requerido
def alertas():
    from datetime import datetime, timedelta

    conn = get_connection()
    cursor = conn.cursor()

    hoy = datetime.today().date()
    limite = hoy + timedelta(days=7)

    # =========================
    # LICENCIAS DE CONDUCTORES
    # =========================
    cursor.execute("""
        SELECT
            nombre,
            NULLIF(licencia_vencimiento::text, '')::date AS fecha
        FROM conductores
        WHERE NULLIF(licencia_vencimiento::text, '') IS NOT NULL
          AND NULLIF(licencia_vencimiento::text, '')::date <= %s
        ORDER BY fecha
    """, (limite,))

    licencias_raw = cursor.fetchall()

    licencias = []
    for l in licencias_raw:
        l = dict(l)

        fecha = l["fecha"]

        if fecha:
            if isinstance(fecha, str):
                fecha = datetime.strptime(fecha, "%Y-%m-%d").date()

            l["fecha"] = fecha
            l["vencido"] = fecha <= hoy
        else:
            l["vencido"] = False

        licencias.append(l)

    # =========================
    # VENCIMIENTOS VEHÍCULOS
    # =========================
    cursor.execute("""
        SELECT patente, 'VTV' AS tipo, NULLIF(vtv, '')::date AS fecha
        FROM vehiculos
        WHERE NULLIF(vtv, '') IS NOT NULL
          AND NULLIF(vtv, '')::date <= %s

        UNION ALL

        SELECT patente, 'REMIS' AS tipo, NULLIF(remis, '')::date AS fecha
        FROM vehiculos
        WHERE NULLIF(remis, '') IS NOT NULL
          AND NULLIF(remis, '')::date <= %s

        UNION ALL

        SELECT patente, 'GNC' AS tipo, NULLIF(gnc, '')::date AS fecha
        FROM vehiculos
        WHERE NULLIF(gnc, '') IS NOT NULL
          AND NULLIF(gnc, '')::date <= %s

        UNION ALL

        SELECT patente, 'TUBO' AS tipo, NULLIF(tubo, '')::date AS fecha
        FROM vehiculos
        WHERE NULLIF(tubo, '') IS NOT NULL
          AND NULLIF(tubo, '')::date <= %s

        ORDER BY fecha
    """, (limite, limite, limite, limite))

    vehiculos_raw = cursor.fetchall()

    vehiculos = []
    for v in vehiculos_raw:
        v = dict(v)

        fecha = v["fecha"]

        if fecha:
            if isinstance(fecha, str):
                fecha = datetime.strptime(fecha, "%Y-%m-%d").date()

            v["fecha"] = fecha
            v["vencido"] = fecha <= hoy
        else:
            v["vencido"] = False

        vehiculos.append(v)

    conn.close()

    total = len(licencias) + len(vehiculos)

    return render_template(
        "alertas.html",
        licencias=licencias,
        vehiculos=vehiculos,
        total=total,
        hoy=hoy
    )

@app.context_processor
def alertas_global():

    from datetime import datetime, timedelta
    

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
    '''cursor.execute("""
        SELECT COUNT(*) as total
        FROM infracciones
        WHERE fecha_vencimiento IS NOT NULL
        AND fecha_vencimiento != ''
        AND date(fecha_vencimiento) <= %s
    """, (limite,))

    inf = cursor.fetchone()["total"]'''

    conn.close()

    return {
        "alertas_total": lic + veh
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