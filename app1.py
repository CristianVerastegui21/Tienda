from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    url_for,
    send_file
)
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from openpyxl import Workbook
from flask import send_file
import matplotlib.pyplot as plt
import cv2
from pyzbar.pyzbar import decode
import numpy as np
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename
from functools import wraps
from flask import session, redirect
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

def rol_requerido(roles_permitidos):
    def wrapper(f):
        @wraps(f)
        def decorada(*args, **kwargs):

            if 'usuario' not in session:
                return redirect('/login')

            if session.get('rol') not in roles_permitidos:
                return "<h1>Acceso denegado</h1>"

            return f(*args, **kwargs)

        return decorada
    return wrapper

app = Flask(__name__)

# CONEXIÓN A BASE DE DATOS
def conectar():
    conexion = sqlite3.connect('database/bodega.db')
    conexion.row_factory = sqlite3.Row
    return conexion

# CREAR TABLA PRODUCTOS
# CREAR TABLAS
def crear_tabla():

    

    conexion = conectar()

    cursor = conexion.cursor()

    # TABLA PRODUCTOS
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

    # TABLA VENTAS
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
            subtotal REAL,

            FOREIGN KEY(id_venta) REFERENCES ventas(id),
            FOREIGN KEY(id_producto) REFERENCES productos(id)
        )
    ''')

    # TABLA USUARIOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            usuario TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    ''')

    # CREAR ADMIN SI NO EXISTE
    admin = conexion.execute('''
        SELECT * FROM usuarios
        WHERE usuario = ?
    ''', ('admin',)).fetchone()

    if not admin:

        conexion.execute('''
            INSERT INTO usuarios
            (nombre, usuario, password, rol)
            VALUES (?, ?, ?, ?)
        ''', (
            'Administrador',
            'admin',
            generate_password_hash('1234'),
            'admin'
        ))

    # TABLA LOGS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            usuario TEXT,

            accion TEXT,

            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
                   
    ''')


    conexion.commit()

    conexion.close()



crear_tabla()

# REGISTRAR LOG
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

# GENERAR TICKET PDF
def generar_ticket(id_venta, carrito, total):

    carpeta = 'tickets'

    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    nombre_pdf = f'tickets/venta_{id_venta}.pdf'

    c = canvas.Canvas(nombre_pdf, pagesize=letter)

    y = 750

    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, y, "Bodega Verastegui")

    y -= 40

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Venta N°: {id_venta}")

    y -= 20

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

# CREAR BACKUP
def crear_backup():

    carpeta = 'backups'

    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    fecha = datetime.now().strftime(
        '%Y%m%d_%H%M%S'
    )

    origen = 'database/bodega.db'

    destino = f'backups/bodega_{fecha}.db'

    shutil.copy(origen, destino)

    return destino

# AGREGAR PRODUCTO AL CARRITO
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

    # SI NO EXISTE
    if not encontrado:

        item = {
            'id': producto['id'],
            'nombre': producto['nombre'],
            'precio': producto['precio'],
            'cantidad': cantidad,
            'subtotal': producto['precio'] * cantidad
        }

        carrito.append(item)

    session['carrito'] = carrito

# RUTA PRINCIPAL
@app.route('/')
def index():
    return render_template('index.html')

# VALIDAR LOGIN
def login_requerido():

    if 'usuario' not in session:

        return False

    return True



# VALIDAR ADMIN
def solo_admin():

    return session.get('rol') == 'admin'


# VALIDAR SUPERVISOR O ADMIN
def supervisor_o_admin():

    return session.get('rol') in ['admin', 'supervisor']

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        usuario = request.form['usuario']
        password = request.form['password']

        conexion = conectar()

        user = conexion.execute('''
            SELECT * FROM usuarios
            WHERE usuario = ?
            AND password = ?
        ''', (
            usuario,
            password
        )).fetchone()

        conexion.close()

        if user:

            session['usuario'] = user['usuario']
            session['rol'] = user['rol']

            return redirect('/')

        return 'Usuario o contraseña incorrectos'

    return render_template('login.html')

# LOGOUT
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

# VALIDAR LOGIN
    if 'usuario' not in session:
        return redirect('/login')
    
# DASHBOARD
@app.route('/dashboard')
@rol_requerido(['admin', 'supervisor'])
def dashboard():
    ...

    if 'usuario' not in session:
        return redirect('/login')

    conexion = conectar()

    # TOTAL PRODUCTOS
    total_productos = conexion.execute('''
        SELECT COUNT(*) as total
        FROM productos
    ''').fetchone()['total']

    # TOTAL VENTAS
    total_ventas = conexion.execute('''
        SELECT COUNT(*) as total
        FROM ventas
    ''').fetchone()['total']

    # INGRESOS
    ingresos = conexion.execute('''
        SELECT IFNULL(SUM(total), 0) as total
        FROM ventas
    ''').fetchone()['total']

    # STOCK BAJO
    stock_bajo = conexion.execute('''
        SELECT * FROM productos
        WHERE stock <= 5
    ''').fetchall()

    # ÚLTIMAS VENTAS
    ultimas_ventas = conexion.execute('''
        SELECT * FROM ventas
        ORDER BY fecha DESC
        LIMIT 5
    ''').fetchall()

    conexion.close()

    return render_template(
        'dashboard.html',
        total_productos=total_productos,
        total_ventas=total_ventas,
        ingresos=ingresos,
        stock_bajo=stock_bajo,
        ultimas_ventas=ultimas_ventas
    )

# BACKUP BASE DATOS
@app.route('/backup')
@rol_requerido(['admin'])
def backup():
    ...

    if 'usuario' not in session:
        return redirect('/login')

    archivo = crear_backup()

    return f'''
        <h1>Backup Creado</h1>

        <p>{archivo}</p>

        <a href="/dashboard">
            Volver
        </a>
    '''

# GRAFICOS DE VENTAS
@app.route('/graficos')
def graficos():

    if 'usuario' not in session:
        return redirect('/login')

    conexion = conectar()

    ventas = conexion.execute('''
        SELECT
            DATE(fecha) as dia,
            SUM(total) as total
        FROM ventas
        GROUP BY DATE(fecha)
        ORDER BY dia
    ''').fetchall()

    conexion.close()

    dias = [venta['dia'] for venta in ventas]
    totales = [venta['total'] for venta in ventas]

    # CREAR GRÁFICO
    plt.figure(figsize=(8,5))

    plt.plot(dias, totales, marker='o')

    plt.title('Ventas por Día')

    plt.xlabel('Fecha')

    plt.ylabel('Ingresos')

    plt.xticks(rotation=45)

    plt.tight_layout()

    ruta = 'static/graficos/ventas.png'

    plt.savefig(ruta)

    plt.close()

    return render_template(
        'graficos.html',
        imagen=ruta
    )
 
# SCANNER PARA PRODUCTOS
@app.route('/scanner_codigo')
def scanner_codigo():

    cap = cv2.VideoCapture(0)

    # VALIDAR CAMARA
    if not cap.isOpened():

        return 'No se pudo abrir la cámara'

    codigo_detectado = None

    while True:

        success, frame = cap.read()

        # VALIDAR FRAME
        if not success or frame is None:

            continue

        try:

            codigos = decode(frame)

            for barcode in codigos:

                codigo_detectado = barcode.data.decode('utf-8')

                break

        except Exception as e:

            print("Error scanner:", e)

        cv2.imshow(
            "Escanear Codigo",
            frame
        )

        key = cv2.waitKey(1)

        # ESC o detectado
        if key == 27 or codigo_detectado:

            break

    cap.release()

    cv2.destroyAllWindows()

    if codigo_detectado:

        return codigo_detectado

    return ''

# SCANNER PARA VENTAS
@app.route('/scanner_ventas')
def scanner_ventas():

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():

        return redirect('/ventas')

    codigo_detectado = None

    while True:

        success, frame = cap.read()

        if not success or frame is None:

            continue

        try:

            codigos = decode(frame)

            for barcode in codigos:

                codigo_detectado = barcode.data.decode('utf-8')

                break

        except Exception as e:

            print("Error scanner:", e)

        cv2.imshow(
            "Scanner Ventas",
            frame
        )

        key = cv2.waitKey(1)

        if key == 27 or codigo_detectado:

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

@app.route('/agregar_por_codigo/<codigo>')
def agregar_por_codigo(codigo):

    conexion = conectar()

    producto = conexion.execute('''
        SELECT * FROM productos
        WHERE codigo_barra = ?
    ''', (codigo,)).fetchone()

    conexion.close()

    if producto:

        agregar_al_carrito(producto, 1)

    return redirect('/ventas')

# EXPORTAR VENTAS EXCEL
@app.route('/exportar_ventas')
def exportar_ventas():

    if 'usuario' not in session:
        return redirect('/login')

    conexion = conectar()

    ventas = conexion.execute('''
        SELECT * FROM ventas
        ORDER BY fecha DESC
    ''').fetchall()

    conexion.close()

    wb = Workbook()

    ws = wb.active

    ws.title = "Ventas"

    # ENCABEZADOS
    ws.append([
        'ID',
        'Total',
        'Fecha'
    ])

    # DATOS
    for venta in ventas:

        ws.append([
            venta['id'],
            venta['total'],
            venta['fecha']
        ])

    # GUARDAR ARCHIVO
    archivo = 'reportes/ventas.xlsx'

    wb.save(archivo)

    return send_file(
        archivo,
        as_attachment=True
    )




# MOSTRAR PRODUCTOS
@app.route('/productos')
@rol_requerido(['admin', 'supervisor'])
def productos():
    ...
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

    return render_template('productos.html', productos=productos)

# AGREGAR PRODUCTO
@app.route('/agregar', methods=['GET', 'POST'])
def agregar_producto():

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
            (nombre, precio, stock, codigo_barra,imagen)
            VALUES (?, ?, ?, ?,?)
        ''', (nombre, precio, stock, codigo, nombre_imagen))

        conexion.commit()
        conexion.close()

        return redirect('/productos')

    return render_template('agregar_producto.html')

# EDITAR PRODUCTO
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):

    conexion = conectar()

    producto = conexion.execute(
        'SELECT * FROM productos WHERE id = ?',
        (id,)
    ).fetchone()

    if request.method == 'POST':

        nombre = request.form['nombre']
        precio = request.form['precio']
        stock = request.form['stock']
        codigo = request.form['codigo']

        conexion.execute('''
            UPDATE productos
            SET nombre = ?, precio = ?, stock = ?, codigo_barra = ?
            WHERE id = ?
        ''', (nombre, precio, stock, codigo, id))

        conexion.commit()
        conexion.close()

        return redirect('/productos')

    conexion.close()

    return render_template(
        'editar_producto.html',
        producto=producto
    )

# ELIMINAR PRODUCTO
@app.route('/eliminar/<int:id>')
def eliminar_producto(id):

    conexion = conectar()

    conexion.execute(
        'DELETE FROM productos WHERE id = ?',
        (id,)
    )

    conexion.commit()
    conexion.close()

    return redirect('/productos')

# VALIDAR LOGIN
    if 'usuario' not in session:
        return redirect('/login')
# VENTAS
# MODULO VENTAS
@app.route('/ventas', methods=['GET', 'POST'])
@rol_requerido(['admin', 'supervisor', 'cajero'])
def ventas():
    ...
    conexion = conectar()

    productos = conexion.execute(
        'SELECT * FROM productos'
    ).fetchall()

    if 'carrito' not in session:
        session['carrito'] = []

    carrito = session['carrito']

    # AGREGAR PRODUCTO
    if request.method == 'POST':

        id_producto = request.form['producto_id']
        cantidad = int(request.form['cantidad'])

        producto = conexion.execute(
            'SELECT * FROM productos WHERE id = ?',
            (id_producto,)
        ).fetchone()

        if cantidad > producto['stock']:
            
            conexion.close()

            return f'''
                <h1>Error</h1>
                <p>No hay suficiente stock disponible.</p>
                <a href="/ventas">Volver</a>
            '''

        subtotal = producto['precio'] * cantidad

        agregar_al_carrito(
        producto,
        cantidad
)

        return redirect('/ventas')

    total = sum(item['subtotal'] for item in carrito)

    conexion.close()

    return render_template(
        'ventas.html',
        productos=productos,
        carrito=carrito,
        total=total
    )

# AUMENTAR CANTIDAD
@app.route('/aumentar/<int:index>')
def aumentar(index):

    carrito = session.get('carrito', [])

    if 0 <= index < len(carrito):

        carrito[index]['cantidad'] += 1

        carrito[index]['subtotal'] = (
            carrito[index]['cantidad']
            *
            carrito[index]['precio']
        )

    session['carrito'] = carrito

    return redirect('/ventas')

# DISMINUIR CANTIDAD
@app.route('/disminuir/<int:index>')
def disminuir(index):

    carrito = session.get('carrito', [])

    if 0 <= index < len(carrito):

        carrito[index]['cantidad'] -= 1

        # ELIMINAR SI LLEGA A 0
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

# FINALIZAR VENTA
@app.route('/finalizar_venta')
def finalizar_venta():

    conexion = conectar()

    carrito = session.get('carrito', [])

    if len(carrito) == 0:
        return redirect('/ventas')

    total = sum(item['subtotal'] for item in carrito)

    cursor = conexion.cursor()

    # GUARDAR VENTA
    cursor.execute(
        'INSERT INTO ventas (total) VALUES (?)',
        (total,)
    )

    id_venta = cursor.lastrowid

    # GUARDAR DETALLES
    for item in carrito:
        producto = conexion.execute(
            'SELECT * FROM productos WHERE id = ?',
            (item['id'],)
        ).fetchone()

        # VALIDAR STOCK
        if item['cantidad'] > producto['stock']:

            conexion.close()

            return f'''
                <h1>Error de Stock</h1>
                <p>No hay stock suficiente para {producto["nombre"]}</p>
                <a href="/ventas">Volver</a>
            '''

        conexion.execute('''
            INSERT INTO detalle_venta
            (id_venta, id_producto, cantidad, subtotal)
            VALUES (?, ?, ?, ?)
        ''', (
            id_venta,
            item['id'],
            item['cantidad'],
            item['subtotal']
        ))

        # ACTUALIZAR STOCK
        producto = conexion.execute(
            'SELECT * FROM productos WHERE id = ?',
            (item['id'],)
        ).fetchone()

        nuevo_stock = producto['stock'] - item['cantidad']

        conexion.execute('''
            UPDATE productos
            SET stock = ?
            WHERE id = ?
        ''', (
            nuevo_stock,
            item['id']
        ))
    # GENERAR PDF
    generar_ticket(
        id_venta,
        carrito,
        total
    )
    conexion.commit()
    conexion.close()

    # LIMPIAR CARRITO
    session['carrito'] = []

    return redirect('/ventas')

# ELIMINAR DEL CARRITO
@app.route('/eliminar_carrito/<int:index>')
def eliminar_carrito(index):

    carrito = session.get('carrito', [])

    if 0 <= index < len(carrito):
        carrito.pop(index)

    session['carrito'] = carrito

    return redirect('/ventas')

# VALIDAR LOGIN
    if 'usuario' not in session:
        return redirect('/login')
    
# HISTORIAL DE VENTAS
@app.route('/historial')
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

# VACIAR CARRITO
@app.route('/vaciar_carrito')
def vaciar_carrito():

    session['carrito'] = []

    return redirect('/ventas')

# REPORTES
# REPORTES PROFESIONALES
@app.route('/reportes')
@rol_requerido(['admin', 'supervisor'])
def reportes():
    ...

    if 'usuario' not in session:
        return redirect('/login')

    conexion = conectar()

    # =========================
    # FILTROS
    # =========================

    desde = request.args.get('desde')
    hasta = request.args.get('hasta')
    periodo = request.args.get('periodo', 'diario')

    query_filtro = ""

    parametros = []

    if desde and hasta:

        query_filtro = '''
            WHERE DATE(fecha)
            BETWEEN ? AND ?
        '''

        parametros = [desde, hasta]

    # =========================
    # TOTAL VENTAS
    # =========================

    total_ventas = conexion.execute(f'''
        SELECT COUNT(*) as total
        FROM ventas
        {query_filtro}
    ''', parametros).fetchone()['total']

    # =========================
    # INGRESOS
    # =========================

    ingresos = conexion.execute(f'''
        SELECT IFNULL(SUM(total),0) as total
        FROM ventas
        {query_filtro}
    ''', parametros).fetchone()['total']

    # =========================
    # VENTAS
    # =========================

    ventas = conexion.execute(f'''
        SELECT *
        FROM ventas
        {query_filtro}
        ORDER BY fecha DESC
    ''', parametros).fetchall()

    # =========================
    # PRODUCTOS TOP
    # =========================

    productos_top = conexion.execute(f'''
        SELECT
            productos.nombre,
            SUM(detalle_venta.cantidad) as total

        FROM detalle_venta

        INNER JOIN productos
        ON productos.id = detalle_venta.id_producto

        INNER JOIN ventas
        ON ventas.id = detalle_venta.id_venta

        {query_filtro}

        GROUP BY productos.nombre

        ORDER BY total DESC

        LIMIT 10
    ''', parametros).fetchall()

    # =========================
    # STOCK BAJO
    # =========================

    stock_bajo = conexion.execute('''
        SELECT *
        FROM productos
        WHERE stock <= 5
    ''').fetchall()

    # =========================
    # GRAFICO VENTAS
    # =========================

    if periodo == 'diario':

        grafico = conexion.execute(f'''
            SELECT
                DATE(fecha) as periodo,
                SUM(total) as total
            FROM ventas
            {query_filtro}
            GROUP BY DATE(fecha)
            ORDER BY DATE(fecha)
        ''', parametros).fetchall()

    elif periodo == 'mensual':

        grafico = conexion.execute(f'''
            SELECT
                strftime('%m-%Y', fecha) as periodo,
                SUM(total) as total
            FROM ventas
            {query_filtro}
            GROUP BY strftime('%m-%Y', fecha)
            ORDER BY fecha
        ''', parametros).fetchall()

    elif periodo == 'anual':

        grafico = conexion.execute(f'''
            SELECT
                strftime('%Y', fecha) as periodo,
                SUM(total) as total
            FROM ventas
            {query_filtro}
            GROUP BY strftime('%Y', fecha)
            ORDER BY fecha
        ''', parametros).fetchall()

    else:

        grafico = conexion.execute(f'''
            SELECT
                DATE(fecha) as periodo,
                SUM(total) as total
            FROM ventas
            {query_filtro}
            GROUP BY DATE(fecha)
            ORDER BY DATE(fecha)
        ''', parametros).fetchall()

    dias = [
        item['periodo']
        for item in grafico
    ]

    totales = [
        item['total']
        for item in grafico
    ]

    # =========================
    # DATOS GRAFICO PRODUCTOS
    # =========================

    nombres_productos = [
        p['nombre']
        for p in productos_top
    ]

    cantidades_productos = [
        p['total']
        for p in productos_top
    ]

    # =========================
    # TOTALES
    # =========================

    productos_vendidos_total = sum(
        cantidades_productos
    ) if cantidades_productos else 0

    stock_bajo_total = len(stock_bajo)

    conexion.close()

    return render_template(

        'reportes.html',

        total_ventas=total_ventas,
        ingresos=ingresos,

        ventas=ventas,

        productos_top=productos_top,

        stock_bajo=stock_bajo,

        dias=dias,
        totales=totales,

        nombres_productos=nombres_productos,
        cantidades_productos=cantidades_productos,

        productos_vendidos_total=productos_vendidos_total,
        stock_bajo_total=stock_bajo_total
    )
# ==============================
# USUARIOS
# ==============================

# USUARIOS
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

# ==============================
# AGREGAR USUARIO
# ==============================

# AGREGAR USUARIO
@app.route('/agregar_usuario', methods=['GET', 'POST'])
@rol_requerido(['admin'])
def agregar_usuario():

    if request.method == 'POST':

        nombre = request.form['nombre']
        usuario = request.form['usuario']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        rol = request.form['rol']

        conexion = conectar()

        conexion.execute('''
            INSERT INTO usuarios
            (nombre, usuario, password, rol)
            VALUES (?, ?, ?, ?)
        ''', (
            nombre,
            usuario,
            password_hash,
            rol
        ))

        conexion.commit()
        conexion.close()

        return redirect('/usuarios')

    return render_template(
        'agregar_usuario.html'
    )
# ==============================
# ELIMINAR USUARIO
# ==============================

# ELIMINAR USUARIO
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
    
# EDITAR USUARIO
@app.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
@rol_requerido(['admin'])
def editar_usuario(id):

    conexion = conectar()

    usuario = conexion.execute('''
        SELECT * FROM usuarios
        WHERE id = ?
    ''', (id,)).fetchone()

    if request.method == 'POST':

        nombre = request.form['nombre']
        username = request.form['usuario']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        rol = request.form['rol']

        conexion.execute('''
            UPDATE usuarios
            SET nombre = ?,
                usuario = ?,
                password = ?,
                rol = ?
            WHERE id = ?
        ''', (
            nombre,
            username,
            password_hash,
            rol,
            id
        ))

        conexion.commit()
        conexion.close()

        return redirect('/usuarios')

    conexion.close()

    return render_template(
        'editar_usuario.html',
        usuario=usuario
    )

if __name__ == '__main__':

    app.secret_key = 'bodega_verastegui'
    app.run(debug=True)
