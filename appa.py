from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    send_file
)

import sqlite3
import os
import shutil
import cv2
import matplotlib.pyplot as plt

from pyzbar.pyzbar import decode

from datetime import datetime
from functools import wraps

from werkzeug.utils import secure_filename
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from openpyxl import Workbook

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image
)

from reportlab.lib import colors

from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)

from reportlab.lib.enums import TA_CENTER

from reportlab.lib.pagesizes import letter

# =========================================
# APP
# =========================================

app = Flask(__name__)
app.secret_key = 'bodega_verastegui'

# =========================================
# BASE DE DATOS
# =========================================

def conectar():

    conexion = sqlite3.connect('database/bodega.db')

    conexion.row_factory = sqlite3.Row

    return conexion

# =========================================
# ROLES
# =========================================

def rol_requerido(roles):

    def decorador(f):

        @wraps(f)
        def wrapper(*args, **kwargs):

            if 'usuario' not in session:

                return redirect('/login')

            if session.get('rol') not in roles:

                return "<h1>Acceso Denegado</h1>"

            return f(*args, **kwargs)

        return wrapper

    return decorador

# =========================================
# CREAR TABLAS
# =========================================

def crear_tablas():

    conexion = conectar()

    cursor = conexion.cursor()

    # PRODUCTOS

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nombre TEXT NOT NULL,

            precio REAL NOT NULL,

            stock INTEGER NOT NULL,

            codigo_barra TEXT,

            imagen TEXT
        )
    ''')

    # AGREGAR CAMPO REORDEN
    try:

        cursor.execute('''

            ALTER TABLE productos

            ADD COLUMN reorden INTEGER DEFAULT 5

        ''')

    except:

        pass

    # VENTAS

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            total REAL NOT NULL,

            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # DETALLE VENTA

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detalle_venta (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            id_venta INTEGER,

            id_producto INTEGER,

            cantidad INTEGER,

            subtotal REAL
        )
    ''')

    # USUARIOS

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nombre TEXT,

            usuario TEXT UNIQUE,

            password TEXT,

            rol TEXT
        )
    ''')

    # LOGS

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            usuario TEXT,

            accion TEXT,

            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ADMIN

    admin = cursor.execute('''
        SELECT * FROM usuarios
        WHERE usuario = ?
    ''', ('admin',)).fetchone()

    if not admin:

        cursor.execute('''
            INSERT INTO usuarios
            (nombre, usuario, password, rol)

            VALUES (?, ?, ?, ?)
        ''', (

            'Administrador',
            'admin',
            generate_password_hash('1234'),
            'admin'
        ))

        

    conexion.commit()
    conexion.close()

crear_tablas()

# =========================================
# LOGS
# =========================================

def registrar_log(usuario, accion):

    conexion = conectar()

    conexion.execute('''
        INSERT INTO logs
        (usuario, accion)

        VALUES (?, ?)
    ''', (

        usuario,
        accion
    ))

    conexion.commit()
    conexion.close()

# =========================================
# BACKUP
# =========================================

def crear_backup():

    carpeta = 'backups'

    if not os.path.exists(carpeta):

        os.makedirs(carpeta)

    fecha = datetime.now().strftime('%Y%m%d_%H%M%S')

    origen = 'database/bodega.db'

    destino = f'backups/bodega_{fecha}.db'

    shutil.copy(origen, destino)

    return destino

# =========================================
# CARRITO
# =========================================

def agregar_al_carrito(producto, cantidad=1):

    if 'carrito' not in session:

        session['carrito'] = []

    carrito = session['carrito']

    encontrado = False

    for item in carrito:

        if item['id'] == producto['id']:

            item['cantidad'] += cantidad

            item['subtotal'] = (
                item['cantidad'] * item['precio']
            )

            encontrado = True

            break

    if not encontrado:

        carrito.append({

            'id': producto['id'],
            'nombre': producto['nombre'],
            'precio': producto['precio'],
            'cantidad': cantidad,
            'subtotal': producto['precio'] * cantidad
        })

    session['carrito'] = carrito

# ==============================
# AUMENTAR CANTIDAD
# ==============================

@app.route('/aumentar/<int:index>')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def aumentar(index):

    carrito = session.get('carrito', [])

    # VALIDAR INDEX
    if index < 0 or index >= len(carrito):

        return redirect('/ventas')

    conexion = conectar()

    item = carrito[index]

    # OBTENER PRODUCTO
    producto = conexion.execute('''
        SELECT * FROM productos
        WHERE id = ?
    ''', (item['id'],)).fetchone()

    conexion.close()

    # VALIDAR PRODUCTO
    if not producto:

        return redirect('/ventas')

    # VALIDAR STOCK
    if item['cantidad'] < producto['stock']:

        item['cantidad'] += 1

        item['subtotal'] = (
            item['cantidad']
            *
            item['precio']
        )

    session['carrito'] = carrito

    return redirect('/ventas')


# ==============================
# DISMINUIR CANTIDAD
# ==============================

@app.route('/disminuir/<int:index>')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def disminuir(index):

    carrito = session.get('carrito', [])

    # VALIDAR INDEX
    if index < 0 or index >= len(carrito):

        return redirect('/ventas')

    carrito[index]['cantidad'] -= 1

    # ELIMINAR SI ES 0
    if carrito[index]['cantidad'] <= 0:

        carrito.pop(index)

    else:

        carrito[index]['subtotal'] = (

            carrito[index]['cantidad']
            *
            carrito[index]['precio']

        )

    session['carrito'] = carrito

    return redirect('/ventas')


# ==============================
# ELIMINAR DEL CARRITO
# ==============================

@app.route('/eliminar_carrito/<int:index>')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def eliminar_carrito(index):

    carrito = session.get('carrito', [])

    if 0 <= index < len(carrito):

        carrito.pop(index)

    session['carrito'] = carrito

    return redirect('/ventas')




# =========================================
# TICKET PDF
# =========================================

def generar_ticket(id_venta, carrito, total):

    if not os.path.exists('tickets'):

        os.makedirs('tickets')

    archivo = f'tickets/venta_{id_venta}.pdf'

    c = canvas.Canvas(archivo, pagesize=letter)

    y = 750

    c.setFont("Helvetica-Bold", 18)

    c.drawString(180, y, "Bodega Verastegui")

    y -= 40

    c.setFont("Helvetica", 12)

    c.drawString(50, y, f"Venta N°: {id_venta}")

    y -= 30

    for item in carrito:

        texto = (
            f"{item['nombre']} "
            f"x{item['cantidad']} "
            f"- S/. {item['subtotal']}"
        )

        c.drawString(50, y, texto)

        y -= 20

    y -= 20

    c.setFont("Helvetica-Bold", 14)

    c.drawString(50, y, f"TOTAL: S/. {total}")

    c.save()

# =========================================
# LOGIN
# =========================================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        usuario = request.form['usuario']
        password = request.form['password']

        conexion = conectar()

        user = conexion.execute('''
            SELECT * FROM usuarios
            WHERE usuario = ?
        ''', (usuario,)).fetchone()

        conexion.close()

        if user and check_password_hash(user['password'], password):

            session['usuario'] = user['usuario']
            session['rol'] = user['rol']

            registrar_log(
                usuario,
                'Inicio de sesión'
            )

            return redirect('/')

        return 'Usuario o contraseña incorrectos'

    return render_template('login.html')

# =========================================
# LOGOUT
# =========================================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

# =========================================
# INDEX
# =========================================

@app.route('/')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def index():

    conexion = conectar()

    total_productos = conexion.execute('''
        SELECT COUNT(*) total
        FROM productos
    ''').fetchone()['total']

    total_ventas = conexion.execute('''
        SELECT COUNT(*) total
        FROM ventas
    ''').fetchone()['total']

    ingresos = conexion.execute('''
        SELECT IFNULL(SUM(total),0) total
        FROM ventas
    ''').fetchone()['total']

    stock_bajo = conexion.execute('''
        SELECT COUNT(*) total
        FROM productos
        WHERE stock <= 5
    ''').fetchone()['total']

    conexion.close()

    return render_template(

        'index.html',

        total_productos=total_productos,
        total_ventas=total_ventas,
        ingresos=ingresos,
        stock_bajo=stock_bajo
    )

# =========================================
# PRODUCTOS
# =========================================

@app.route('/productos')
@rol_requerido(['admin', 'supervisor'])
def productos():

    conexion = conectar()

    busqueda = request.args.get('buscar', '')

    productos = conexion.execute('''
        SELECT * FROM productos

        WHERE nombre LIKE ?
        OR codigo_barra LIKE ?
    ''', (

        f'%{busqueda}%',
        f'%{busqueda}%'
    )).fetchall()

    conexion.close()

    return render_template(
        'productos.html',
        productos=productos
    )

# =========================================
# AGREGAR PRODUCTO
# =========================================

@app.route('/agregar', methods=['GET', 'POST'])
@rol_requerido(['admin', 'supervisor'])
def agregar_producto():
    reorden = request.form.get('reorden', 5)

    if request.method == 'POST':

        nombre = request.form['nombre']
        precio = request.form['precio']
        stock = request.form['stock']
        codigo = request.form['codigo']

        imagen = request.files['imagen']

        nombre_imagen = ''

        if imagen:

            nombre_imagen = secure_filename(
                imagen.filename
            )

            ruta = os.path.join(
                'static/productos',
                nombre_imagen
            )

            imagen.save(ruta)

        conexion = conectar()

        conexion.execute('''

            INSERT INTO productos
            (
            nombre,
            precio,
            stock,
            codigo_barra,
            imagen,
            reorden
            )

            VALUES(?,?,?,?,?,?)

            ''',(

            nombre,
            precio,
            stock,
            codigo,
            nombre_imagen,
            reorden

            ))

        conexion.commit()
        conexion.close()

        registrar_log(
            session['usuario'],
            f'Agregó producto {nombre}'
        )

        return redirect('/productos')

    return render_template('agregar_producto.html')

# =========================================
# EDITAR PRODUCTO
# =========================================

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@rol_requerido(['admin', 'supervisor'])
def editar_producto(id):
    reorden = request.form.get('reorden', 5)

    conexion = conectar()

    producto = conexion.execute('''
        SELECT * FROM productos
        WHERE id = ?
    ''', (id,)).fetchone()

    if request.method == 'POST':

        nombre = request.form['nombre']
        precio = request.form['precio']
        stock = request.form['stock']
        codigo = request.form['codigo']

        conexion.execute('''
            UPDATE productos

            SET

            nombre=?,
            precio=?,
            stock=?,
            codigo_barra=?,
            reorden=?

            WHERE id=?
        ''', (

            nombre,
            precio,
            stock,
            codigo,
            reorden,
            id
        ))

        conexion.commit()
        conexion.close()

        return redirect('/productos')

    conexion.close()

    return render_template(
        'editar_producto.html',
        producto=producto
    )

# =========================================
# ELIMINAR PRODUCTO
# =========================================

@app.route('/eliminar/<int:id>')
@rol_requerido(['admin'])
def eliminar_producto(id):

    conexion = conectar()

    conexion.execute('''
        DELETE FROM productos
        WHERE id = ?
    ''', (id,))

    conexion.commit()
    conexion.close()

    return redirect('/productos')

# =========================================
# VENTAS
# =========================================

@app.route('/ventas', methods=['GET', 'POST'])
@rol_requerido(['admin', 'supervisor', 'cajero'])
def ventas():

    conexion = conectar()

    productos = conexion.execute('''
        SELECT * FROM productos
    ''').fetchall()

    if 'carrito' not in session:

        session['carrito'] = []

    carrito = session['carrito']

    if request.method == 'POST':

        id_producto = request.form['producto_id']

        cantidad = int(request.form['cantidad'])

        producto = conexion.execute('''
            SELECT * FROM productos
            WHERE id = ?
        ''', (id_producto,)).fetchone()

        if cantidad > producto['stock']:

            return "<h1>Stock insuficiente</h1>"

        agregar_al_carrito(
            producto,
            cantidad
        )

        return redirect('/ventas')

    total = sum(
        item['subtotal']
        for item in carrito
    )

    conexion.close()

    return render_template(

        'ventas.html',

        productos=productos,
        carrito=carrito,
        total=total
    )
# ==============================
# VACIAR CARRITO
# ==============================

@app.route('/vaciar_carrito')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def vaciar_carrito():

    session['carrito'] = []

    return redirect('/ventas')

# ==============================
# FINALIZAR VENTA
# ==============================

@app.route('/finalizar_venta')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def finalizar_venta():

    conexion = conectar()

    carrito = session.get('carrito', [])

    if len(carrito) == 0:

        conexion.close()

        return redirect('/ventas')

    total = sum(
        item['subtotal']
        for item in carrito
    )

    cursor = conexion.cursor()

    # CREAR VENTA
    cursor.execute('''
        INSERT INTO ventas (total)
        VALUES (?)
    ''', (total,))

    id_venta = cursor.lastrowid

    # DETALLES
    for item in carrito:

        producto = conexion.execute('''
            SELECT * FROM productos
            WHERE id = ?
        ''', (item['id'],)).fetchone()

        # VALIDAR STOCK
        if item['cantidad'] > producto['stock']:

            conexion.close()

            return redirect('/ventas')

        # INSERTAR DETALLE
        conexion.execute('''
            INSERT INTO detalle_venta
            (
                id_venta,
                id_producto,
                cantidad,
                subtotal
            )
            VALUES (?, ?, ?, ?)
        ''', (
            id_venta,
            item['id'],
            item['cantidad'],
            item['subtotal']
        ))

        # ACTUALIZAR STOCK
        nuevo_stock = (
            producto['stock']
            - item['cantidad']
        )

        conexion.execute('''
            UPDATE productos
            SET stock = ?
            WHERE id = ?
        ''', (
            nuevo_stock,
            item['id']
        ))

    conexion.commit()

    # =========================
    # GENERAR PDF
    # =========================

    generar_ticket(
        id_venta,
        carrito,
        total
    )

    conexion.close()

    # LIMPIAR CARRITO
    session['carrito'] = []

    # LOG
    registrar_log(
        session['usuario'],
        f'Generó venta #{id_venta}'
    )

    return redirect(
        f'/ticket/{id_venta}'
    )

# ==============================
# GENERAR TICKET PDF
# ==============================

def generar_ticket(id_venta, carrito, total):

    carpeta = 'static/tickets'

    if not os.path.exists(carpeta):

        os.makedirs(carpeta)

    archivo = f'static/tickets/venta_{id_venta}.pdf'

    doc = SimpleDocTemplate(

        archivo,

        pagesize=letter,

        rightMargin=30,
        leftMargin=30,

        topMargin=30,
        bottomMargin=30

    )

    elementos = []

    estilos = getSampleStyleSheet()

    # =========================
    # ESTILOS
    # =========================

    titulo_style = ParagraphStyle(

        'Titulo',

        parent=estilos['Heading1'],

        fontSize=24,

        alignment=TA_CENTER,

        textColor=colors.HexColor('#2575fc'),

        spaceAfter=10

    )

    total_style = ParagraphStyle(

        'Total',

        parent=estilos['Heading2'],

        fontSize=20,

        alignment=TA_CENTER,

        textColor=colors.HexColor('#16a34a'),

        spaceBefore=20

    )

    # =========================
    # LOGO
    # =========================

    logo_path = 'static/logos/logo.png'

    if os.path.exists(logo_path):

        logo = Image(
            logo_path,
            width=90,
            height=90
        )

        logo.hAlign = 'CENTER'

        elementos.append(logo)

    # =========================
    # TITULO
    # =========================

    titulo = Paragraph(

        "BODEGA VERASTEGUI",

        titulo_style

    )

    elementos.append(titulo)

    elementos.append(

        Paragraph(

            "Sistema Profesional de Ventas",

            estilos['BodyText']

        )

    )

    elementos.append(Spacer(1, 20))

    # =========================
    # DATOS
    # =========================

    fecha = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    usuario = session.get('usuario')

    info = f"""

    <b>Ticket:</b> #{id_venta}<br/>

    <b>Fecha:</b> {fecha}<br/>

    <b>Cajero:</b> {usuario}<br/>

    """

    elementos.append(
        Paragraph(
            info,
            estilos['BodyText']
        )
    )

    elementos.append(Spacer(1, 20))

    # =========================
    # TABLA
    # =========================

    datos = [[

        'Producto',
        'Cant.',
        'Precio',
        'Subtotal'

    ]]

    for item in carrito:

        datos.append([

            item['nombre'],

            item['cantidad'],

            f"S/. {item['precio']:.2f}",

            f"S/. {item['subtotal']:.2f}"

        ])

    tabla = Table(

        datos,

        colWidths=[220, 60, 90, 90]

    )

    tabla.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0),
            colors.HexColor('#2575fc')),

        ('TEXTCOLOR', (0,0), (-1,0),
            colors.white),

        ('FONTNAME', (0,0), (-1,0),
            'Helvetica-Bold'),

        ('FONTSIZE', (0,0), (-1,0),
            12),

        ('BOTTOMPADDING', (0,0), (-1,0),
            10),

        ('TOPPADDING', (0,0), (-1,0),
            10),

        ('GRID', (0,0), (-1,-1),
            1,
            colors.grey),

        ('BACKGROUND', (0,1), (-1,-1),
            colors.whitesmoke),

        ('ALIGN', (1,1), (-1,-1),
            'CENTER'),

    ]))

    elementos.append(tabla)

    # =========================
    # TOTAL
    # =========================

    total_texto = Paragraph(

        f"TOTAL: S/. {total:.2f}",

        total_style

    )

    elementos.append(total_texto)

    elementos.append(Spacer(1, 30))

    # =========================
    # MENSAJE
    # =========================

    mensaje = Paragraph(

        """

        <para align=center>

        ¡Gracias por su compra! ❤️<br/><br/>

        Vuelva pronto.

        </para>

        """,

        estilos['BodyText']

    )

    elementos.append(mensaje)

    # =========================
    # CREAR PDF
    # =========================

    doc.build(elementos)

    return archivo

# ==============================
# MOSTRAR TICKET
# ==============================

@app.route('/ticket/<int:id_venta>')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def ticket(id_venta):

    archivo = f'static/tickets/venta_{id_venta}.pdf'

    return send_file(
        archivo,
        mimetype='application/pdf'
    )

# =========================================
# HISTORIAL
# =========================================

@app.route('/historial')
@rol_requerido(['admin', 'supervisor'])
def historial():

    conexion = conectar()

    ventas = conexion.execute('''
        SELECT * FROM ventas
        ORDER BY fecha DESC
    ''').fetchall()

    conexion.close()

    return render_template(
        'historial.html',
        ventas=ventas
    )

# =========================================
# DASHBOARD
# =========================================

@app.route('/dashboard')
@rol_requerido(['admin', 'supervisor'])
def dashboard():

    conexion = conectar()

    # =========================
    # KPIs
    # =========================

    total_productos = conexion.execute('''
        SELECT COUNT(*) as total
        FROM productos
    ''').fetchone()['total']

    total_ventas = conexion.execute('''
        SELECT COUNT(*) as total
        FROM ventas
    ''').fetchone()['total']

    ingresos = conexion.execute('''
        SELECT IFNULL(SUM(total),0) as total
        FROM ventas
    ''').fetchone()['total']

    # =========================
    # STOCK BAJO
    # =========================

    stock_bajo = conexion.execute('''
        SELECT *
        FROM productos
        WHERE stock <= 5
        ORDER BY stock ASC
    ''').fetchall()

    # =========================
    # ULTIMAS VENTAS
    # =========================

    ultimas_ventas = conexion.execute('''
        SELECT *
        FROM ventas
        ORDER BY fecha DESC
        LIMIT 5
    ''').fetchall()

    # =========================
    # GRAFICO VENTAS
    # =========================

    grafico = conexion.execute('''
        SELECT
            DATE(fecha) as dia,
            SUM(total) as total
        FROM ventas
        GROUP BY DATE(fecha)
        ORDER BY DATE(fecha)
    ''').fetchall()

    dias = [
        item['dia']
        for item in grafico
    ]

    totales = [
        item['total']
        for item in grafico
    ]

    # =========================
    # PRODUCTOS TOP
    # =========================

    productos_top = conexion.execute('''
        SELECT
            productos.nombre,
            SUM(detalle_venta.cantidad) as total

        FROM detalle_venta

        INNER JOIN productos
        ON productos.id = detalle_venta.id_producto

        GROUP BY productos.nombre

        ORDER BY total DESC

        LIMIT 5
    ''').fetchall()

    nombres_productos = [
        p['nombre']
        for p in productos_top
    ]

    cantidades_productos = [
        p['total']
        for p in productos_top
    ]

    conexion.close()

    return render_template(

        'dashboard.html',

        total_productos=total_productos,
        total_ventas=total_ventas,
        ingresos=ingresos,

        stock_bajo=stock_bajo,
        ultimas_ventas=ultimas_ventas,

        dias=dias,
        totales=totales,

        nombres_productos=nombres_productos,
        cantidades_productos=cantidades_productos
    )

# =========================================
# REPORTES
# =========================================

@app.route('/reportes')
@rol_requerido(['admin', 'supervisor'])
def reportes():

    conexion = conectar()

    ventas = conexion.execute('''
        SELECT * FROM ventas
        ORDER BY fecha DESC
    ''').fetchall()

    total_ventas = len(ventas)

    ingresos = sum(
        venta['total']
        for venta in ventas
    )

    grafico = conexion.execute('''
        SELECT
            DATE(fecha) dia,
            SUM(total) total

        FROM ventas

        GROUP BY DATE(fecha)

        ORDER BY DATE(fecha)
    ''').fetchall()

    dias = [x['dia'] for x in grafico]

    totales = [x['total'] for x in grafico]

    productos_top = conexion.execute('''
        SELECT
            productos.nombre,
            SUM(detalle_venta.cantidad) total

        FROM detalle_venta

        INNER JOIN productos
        ON productos.id = detalle_venta.id_producto

        GROUP BY productos.nombre

        ORDER BY total DESC

        LIMIT 10
    ''').fetchall()

    nombres_productos = [
        p['nombre']
        for p in productos_top
    ]

    cantidades_productos = [
        p['total']
        for p in productos_top
    ]

    stock_bajo = conexion.execute('''
        SELECT * FROM productos
        WHERE stock <= 5
    ''').fetchall()

    conexion.close()

    return render_template(

        'reportes.html',

        ventas=ventas,
        total_ventas=total_ventas,
        ingresos=ingresos,

        dias=dias,
        totales=totales,

        productos_top=productos_top,

        nombres_productos=nombres_productos,
        cantidades_productos=cantidades_productos,

        stock_bajo=stock_bajo,

        productos_vendidos_total=sum(cantidades_productos),

        stock_bajo_total=len(stock_bajo)
    )

# ==============================
# EXPORTAR REPORTE PDF
# ==============================

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

@app.route('/reporte_pdf')
@rol_requerido(['admin', 'supervisor'])
def reporte_pdf():

    conexion = conectar()

    # =========================
    # DATOS
    # =========================

    total_ventas = conexion.execute('''
        SELECT COUNT(*) as total
        FROM ventas
    ''').fetchone()['total']

    ingresos = conexion.execute('''
        SELECT IFNULL(SUM(total),0) as total
        FROM ventas
    ''').fetchone()['total']

    productos_top = conexion.execute('''
        SELECT
            productos.nombre,
            SUM(detalle_venta.cantidad) as vendidos

        FROM detalle_venta

        INNER JOIN productos
        ON productos.id = detalle_venta.id_producto

        GROUP BY productos.nombre

        ORDER BY vendidos DESC

        LIMIT 10
    ''').fetchall()

    stock_bajo = conexion.execute('''
        SELECT nombre, stock
        FROM productos
        WHERE stock <= 5
    ''').fetchall()

    conexion.close()

    # =========================
    # CARPETA
    # =========================

    carpeta = 'reportes'

    if not os.path.exists(carpeta):

        os.makedirs(carpeta)

    archivo = 'reportes/reporte_general.pdf'

    # =========================
    # PDF
    # =========================

    doc = SimpleDocTemplate(

        archivo,

        pagesize=letter,

        rightMargin=30,
        leftMargin=30,

        topMargin=30,
        bottomMargin=30

    )

    estilos = getSampleStyleSheet()

    elementos = []

    # =========================
    # TITULO
    # =========================

    titulo = Paragraph(

        "📊 REPORTE PROFESIONAL - BODEGA VERASTEGUI",

        estilos['Title']

    )

    elementos.append(titulo)

    elementos.append(Spacer(1, 20))

    # =========================
    # RESUMEN
    # =========================

    resumen = f"""

    <b>Total Ventas:</b> {total_ventas}<br/><br/>

    <b>Ingresos Totales:</b> S/. {ingresos:.2f}<br/><br/>

    <b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}

    """

    elementos.append(

        Paragraph(
            resumen,
            estilos['BodyText']
        )

    )

    elementos.append(Spacer(1, 25))

    # =========================
    # PRODUCTOS TOP
    # =========================

    subtitulo1 = Paragraph(

        "🏆 Productos Más Vendidos",

        estilos['Heading2']

    )

    elementos.append(subtitulo1)

    elementos.append(Spacer(1, 10))

    datos_top = [[
        'Producto',
        'Vendidos'
    ]]

    for p in productos_top:

        datos_top.append([
            p['nombre'],
            p['vendidos']
        ])

    tabla_top = Table(datos_top, colWidths=[300, 150])

    tabla_top.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0),
            colors.HexColor('#2575fc')),

        ('TEXTCOLOR', (0,0), (-1,0),
            colors.white),

        ('FONTNAME', (0,0), (-1,0),
            'Helvetica-Bold'),

        ('GRID', (0,0), (-1,-1),
            1,
            colors.black),

        ('BACKGROUND', (0,1), (-1,-1),
            colors.whitesmoke),

        ('ALIGN', (1,1), (-1,-1),
            'CENTER')

    ]))

    elementos.append(tabla_top)

    elementos.append(Spacer(1, 25))

    # =========================
    # STOCK BAJO
    # =========================

    subtitulo2 = Paragraph(

        "⚠ Productos con Bajo Stock",

        estilos['Heading2']

    )

    elementos.append(subtitulo2)

    elementos.append(Spacer(1, 10))

    datos_stock = [[
        'Producto',
        'Stock'
    ]]

    for p in stock_bajo:

        datos_stock.append([
            p['nombre'],
            p['stock']
        ])

    tabla_stock = Table(datos_stock, colWidths=[300, 150])

    tabla_stock.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0),
            colors.red),

        ('TEXTCOLOR', (0,0), (-1,0),
            colors.white),

        ('FONTNAME', (0,0), (-1,0),
            'Helvetica-Bold'),

        ('GRID', (0,0), (-1,-1),
            1,
            colors.black),

        ('BACKGROUND', (0,1), (-1,-1),
            colors.beige),

        ('ALIGN', (1,1), (-1,-1),
            'CENTER')

    ]))

    elementos.append(tabla_stock)

    elementos.append(Spacer(1, 30))

    # =========================
    # FOOTER
    # =========================

    footer = Paragraph(

        """

        <para align=center>

        <font size=9 color=grey>

        Sistema desarrollado con Flask + SQLite<br/>

        Reporte generado automáticamente

        </font>

        </para>

        """,

        estilos['BodyText']

    )

    elementos.append(footer)

    # =========================
    # GENERAR PDF
    # =========================

    doc.build(elementos)

    # =========================
    # DESCARGAR
    # =========================

    return send_file(

        archivo,

        as_attachment=True

    )
# =========================================
# USUARIOS
# =========================================

@app.route('/usuarios')
@rol_requerido(['admin'])
def usuarios():

    conexion = conectar()

    usuarios = conexion.execute('''
        SELECT * FROM usuarios
        ORDER BY id DESC
    ''').fetchall()

    conexion.close()

    return render_template(
        'usuarios.html',
        usuarios=usuarios
    )

# =========================================
# AGREGAR USUARIO
# =========================================

@app.route('/agregar_usuario', methods=['GET', 'POST'])
@rol_requerido(['admin'])
def agregar_usuario():

    if request.method == 'POST':

        nombre = request.form['nombre']
        usuario = request.form['usuario']
        password = request.form['password']
        rol = request.form['rol']

        conexion = conectar()

        conexion.execute('''
            INSERT INTO usuarios
            (nombre, usuario, password, rol)

            VALUES (?, ?, ?, ?)
        ''', (

            nombre,
            usuario,
            generate_password_hash(password),
            rol
        ))

        conexion.commit()
        conexion.close()

        return redirect('/usuarios')

    return render_template('agregar_usuario.html')

# =========================================
# ELIMINAR USUARIO
# =========================================

@app.route('/eliminar_usuario/<int:id>')
@rol_requerido(['admin'])
def eliminar_usuario(id):

    conexion = conectar()

    conexion.execute('''
        DELETE FROM usuarios
        WHERE id = ?
    ''', (id,))

    conexion.commit()
    conexion.close()

    return redirect('/usuarios')

# =========================================
# EXPORTAR EXCEL
# =========================================

@app.route('/exportar_ventas')
@rol_requerido(['admin', 'supervisor'])
def exportar_ventas():

    conexion = conectar()

    ventas = conexion.execute('''
        SELECT * FROM ventas
    ''').fetchall()

    conexion.close()

    wb = Workbook()

    ws = wb.active

    ws.title = "Ventas"

    ws.append([
        'ID',
        'TOTAL',
        'FECHA'
    ])

    for venta in ventas:

        ws.append([

            venta['id'],
            venta['total'],
            venta['fecha']
        ])

    archivo = 'reportes/ventas.xlsx'

    wb.save(archivo)

    return send_file(
        archivo,
        as_attachment=True
    )

# =========================================
# BACKUP
# =========================================

@app.route('/backup')
@rol_requerido(['admin'])
def backup():

    archivo = crear_backup()

    return f'''
        <h1>Backup creado</h1>

        <p>{archivo}</p>

        <a href="/dashboard">
            Volver
        </a>
    '''
# =========================================
# LOGS DEL SISTEMA
# =========================================

@app.route('/logs')
@rol_requerido(['admin'])
def logs():

    conexion = conectar()

    logs = conexion.execute('''
        SELECT * FROM logs
        ORDER BY fecha DESC
    ''').fetchall()

    conexion.close()

    return render_template(
        'logs.html',
        logs=logs
    )

# =========================================
# SCANNER CODIGO PRODUCTOS
# =========================================

@app.route('/scanner_codigo')
@rol_requerido(['admin', 'supervisor'])
def scanner_codigo():

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():

        return 'No se pudo abrir la cámara'

    codigo_detectado = ''

    while True:

        success, frame = cap.read()

        if not success:

            continue

        codigos = decode(frame)

        for codigo in codigos:

            codigo_detectado = codigo.data.decode('utf-8')

            break

        cv2.imshow(
            'Escanear Codigo',
            frame
        )

        tecla = cv2.waitKey(1)

        # ESC
        if tecla == 27 or codigo_detectado:

            break

    cap.release()

    cv2.destroyAllWindows()

    return codigo_detectado

# =========================================
# SCANNER VENTAS
# =========================================

@app.route('/scanner_ventas')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def scanner_ventas():

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():

        return redirect('/ventas')

    codigo_detectado = ''

    while True:

        success, frame = cap.read()

        if not success:

            continue

        codigos = decode(frame)

        for codigo in codigos:

            codigo_detectado = codigo.data.decode('utf-8')

            break

        cv2.imshow(
            'Scanner Ventas',
            frame
        )

        tecla = cv2.waitKey(1)

        if tecla == 27 or codigo_detectado:

            break

    cap.release()

    cv2.destroyAllWindows()

    if codigo_detectado:

        conexion = conectar()

        producto = conexion.execute('''
            SELECT * FROM productos
            WHERE codigo_barra = ?
        ''', (codigo_detectado,)).fetchone()

        conexion.close()

        if producto:

            agregar_al_carrito(producto, 1)

    return redirect('/ventas')

# ==========================
# ALERTAS GLOBALES
# ==========================

@app.context_processor
def alertas_globales():

    conexion = conectar()

    alertas = conexion.execute('''

        SELECT *

        FROM productos

        WHERE stock<=5

        ORDER BY stock ASC

        LIMIT 5

    ''').fetchall()

    conexion.close()

    return dict(

        alertas=alertas,

        total_alertas=len(alertas)

    )

# ==========================
# ALERTAS
# ==========================
@app.context_processor
def alertas_globales():

    conexion=conectar()

    alertas=conexion.execute('''

    SELECT *

    FROM productos

    WHERE stock<=reorden

    ORDER BY stock ASC

    LIMIT 5

    ''').fetchall()

    conexion.close()

    return dict(

        alertas=alertas,

        total_alertas=len(alertas)

    )

# ==============================
# STOCK BAJO / ALERTAS
# ==============================

@app.route('/stock_bajo')
@rol_requerido([
    'admin',
    'supervisor'
])
def stock_bajo():

    conexion = conectar()

    productos = conexion.execute('''

        SELECT *

        FROM productos

        WHERE stock <= reorden

        ORDER BY stock ASC

    ''').fetchall()

    conexion.close()

    return render_template(

        'stock_bajo.html',

        productos=productos

    )
# =========================================
# INICIAR APP
# =========================================

if __name__ == '__main__':

    app.run(debug=True)