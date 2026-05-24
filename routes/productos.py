import os
from flask import (
    Blueprint, render_template, request,
    redirect, session, flash
)
from werkzeug.utils import secure_filename

from db import conectar
from utils.auth import rol_requerido
from utils.logs import registrar_log

bp = Blueprint('productos', __name__)

# ─────────────────────────────────────────────────
# Carpeta de imágenes de productos
# ─────────────────────────────────────────────────
UPLOAD_FOLDER  = 'static/productos'
ALLOWED_EXTS   = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTS
    )

def guardar_imagen(file):
    """Guarda la imagen subida y retorna el nombre del archivo."""
    if not file or file.filename == '':
        return ''
    if not allowed_file(file.filename):
        return ''
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    nombre = secure_filename(file.filename)
    file.save(os.path.join(UPLOAD_FOLDER, nombre))
    return nombre


# ─────────────────────────────────────────────────
# MIGRACIÓN AUTOMÁTICA
# Agrega columnas entradas / salidas si no existen.
# Se ejecuta al importar el blueprint.
# ─────────────────────────────────────────────────
def _migrar_columnas():
    """Agrega columnas que pueden no existir en la BD."""
    conexion = conectar()
    for columna, definicion in [
        ('entradas', 'INTEGER DEFAULT 0'),
        ('salidas',  'INTEGER DEFAULT 0'),
    ]:
        try:
            conexion.execute(
                f'ALTER TABLE productos ADD COLUMN {columna} {definicion}'
            )
        except Exception:
            pass  # ya existe
    conexion.commit()
    conexion.close()

_migrar_columnas()


# ─────────────────────────────────────────────────
# LISTAR PRODUCTOS
# ─────────────────────────────────────────────────
@bp.route('/productos')
@rol_requerido(['admin', 'supervisor'])
def productos():
    conexion  = conectar()
    busqueda  = request.args.get('buscar', '').strip()

    filas = conexion.execute('''
        SELECT * FROM productos
        WHERE nombre      LIKE ?
           OR codigo_barra LIKE ?
        ORDER BY nombre ASC
    ''', (f'%{busqueda}%', f'%{busqueda}%')).fetchall()

    conexion.close()

    return render_template(
        'productos.html',
        productos=filas
    )


# ─────────────────────────────────────────────────
# AGREGAR PRODUCTO
# ─────────────────────────────────────────────────
@bp.route('/agregar', methods=['GET', 'POST'])
@rol_requerido(['admin', 'supervisor'])
def agregar_producto():

    if request.method == 'POST':
        nombre  = request.form.get('nombre',  '').strip()
        precio  = request.form.get('precio',  0)
        stock   = request.form.get('stock',   0)
        reorden = request.form.get('reorden', 5)
        codigo  = request.form.get('codigo',  '').strip()
        imagen  = request.files.get('imagen')

        # Validación básica
        if not nombre:
            flash('El nombre es obligatorio', 'error')
            return render_template('agregar_producto.html')

        nombre_imagen = guardar_imagen(imagen)

        conexion = conectar()
        conexion.execute('''
            INSERT INTO productos
                (nombre, precio, stock, codigo_barra, imagen, reorden)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, precio, stock, codigo, nombre_imagen, reorden))
        conexion.commit()
        conexion.close()

        registrar_log(session['usuario'], f'Agregó producto: {nombre}')
        flash(f'Producto "{nombre}" agregado correctamente', 'success')
        return redirect('/productos')

    return render_template('agregar_producto.html')


# ─────────────────────────────────────────────────
# EDITAR PRODUCTO
# ─────────────────────────────────────────────────
@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@rol_requerido(['admin', 'supervisor'])
def editar_producto(id):
    conexion = conectar()

    producto = conexion.execute(
        'SELECT * FROM productos WHERE id = ?', (id,)
    ).fetchone()

    if not producto:
        conexion.close()
        flash('Producto no encontrado', 'error')
        return redirect('/productos')

    if request.method == 'POST':
        nombre   = request.form.get('nombre',   '').strip()
        precio   = request.form.get('precio',   0)
        reorden  = int(request.form.get('reorden', 5))
        codigo   = request.form.get('codigo',   '').strip()

        # Entradas y salidas de stock
        entradas = int(request.form.get('entradas', 0) or 0)
        salidas  = int(request.form.get('salidas',  0) or 0)

        # Calcular nuevo stock: actual + entradas − salidas (mínimo 0)
        stock_actual = int(producto['stock'])
        nuevo_stock  = max(0, stock_actual + entradas - salidas)

        conexion.execute('''
            UPDATE productos
            SET nombre       = ?,
                precio       = ?,
                stock        = ?,
                entradas     = ?,
                salidas      = ?,
                codigo_barra = ?,
                reorden      = ?
            WHERE id = ?
        ''', (nombre, precio, nuevo_stock, entradas, salidas, codigo, reorden, id))
        conexion.commit()
        conexion.close()

        registrar_log(session['usuario'], f'Editó producto #{id}: {nombre}')
        flash(f'Producto "{nombre}" actualizado', 'success')
        return redirect('/productos')

    conexion.close()
    return render_template('editar_producto.html', producto=producto)


# ─────────────────────────────────────────────────
# ELIMINAR PRODUCTO
# ─────────────────────────────────────────────────
@bp.route('/eliminar/<int:id>')
@rol_requerido(['admin'])
def eliminar_producto(id):
    conexion = conectar()

    producto = conexion.execute(
        'SELECT nombre FROM productos WHERE id = ?', (id,)
    ).fetchone()

    if producto:
        conexion.execute('DELETE FROM productos WHERE id = ?', (id,))
        conexion.commit()
        registrar_log(
            session['usuario'],
            f'Eliminó producto #{id}: {producto["nombre"]}'
        )
        flash(f'Producto "{producto["nombre"]}" eliminado', 'success')

    conexion.close()
    return redirect('/productos')


# ─────────────────────────────────────────────────────────────────────
# SCANNER BACKEND (solo para uso local con OpenCV / cámara del servidor)
# En producción (Render) esta ruta devuelve un mensaje claro.
# El scanner real de producción es 100% frontend (html5-qrcode).
# ─────────────────────────────────────────────────────────────────────
@bp.route('/scanner_codigo')
@rol_requerido(['admin', 'supervisor'])
def scanner_codigo():
    try:
        import cv2
        from pyzbar.pyzbar import decode as pyzbar_decode
    except ImportError:
        # En producción (Render) no están instalados → el frontend lo maneja
        return ('', 200)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return ('', 200)

    codigo_detectado = ''
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        for c in pyzbar_decode(frame):
            codigo_detectado = c.data.decode('utf-8')
            break
        cv2.imshow('Escanear Código — ESC para cerrar', frame)
        tecla = cv2.waitKey(1)
        if tecla == 27 or codigo_detectado:
            break

    cap.release()
    cv2.destroyAllWindows()
    return (codigo_detectado, 200)