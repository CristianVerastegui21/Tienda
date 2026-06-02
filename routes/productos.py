import os

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    flash
)

from werkzeug.utils import secure_filename

from db import conectar, liberar

from routes.dashboard import invalidar_cache_alertas
from utils.auth import rol_requerido
from utils.logs import registrar_log
from utils.supabase_storage import (
    subir_imagen_supabase
)


bp = Blueprint(
    'productos',
    __name__
)


# ─────────────────────────────────────────────────
# CARPETA IMÁGENES
# ─────────────────────────────────────────────────

UPLOAD_FOLDER = 'static/productos'

ALLOWED_EXTS = {
    'png',
    'jpg',
    'jpeg',
    'webp',
    'gif'
}


def allowed_file(filename):

    return (
        '.' in filename and
        filename.rsplit(
            '.',
            1
        )[1].lower() in ALLOWED_EXTS
    )


def guardar_imagen(file):

    if not file or file.filename == '':
        return ''

    if not allowed_file(file.filename):
        return ''

    os.makedirs(
        UPLOAD_FOLDER,
        exist_ok=True
    )

    nombre = secure_filename(
        file.filename
    )

    file.save(
        os.path.join(
            UPLOAD_FOLDER,
            nombre
        )
    )

    return nombre


# ─────────────────────────────────────────────────
# LISTAR PRODUCTOS
# ─────────────────────────────────────────────────

@bp.route('/productos')

@rol_requerido([
    'admin',
    'supervisor'
])

def productos():

    conexion = conectar()

    cursor = conexion.cursor()

    busqueda = request.args.get(
        'buscar',
        ''
    ).strip()

    cursor.execute('''
        SELECT *
        FROM productos
        WHERE nombre ILIKE %s
           OR codigo_barra ILIKE %s
        ORDER BY nombre ASC
    ''', (
        f'%{busqueda}%',
        f'%{busqueda}%'
    ))

    filas = cursor.fetchall()

    cursor.close()

    liberar(conexion)

    return render_template(
        'productos.html',
        productos=filas
    )


# ─────────────────────────────────────────────────
# AGREGAR PRODUCTO
# ─────────────────────────────────────────────────

@bp.route(
    '/agregar',
    methods=['GET', 'POST']
)
@rol_requerido([
    'admin',
    'supervisor'
])
def agregar_producto():

    if request.method == 'POST':
        conexion = conectar()
        cursor = conexion.cursor()

        nombre = request.form.get(
            'nombre',
            ''
        ).strip()

        precio = request.form.get(
            'precio',
            0
        )

        stock = request.form.get(
            'stock',
            0
        )

        reorden = request.form.get(
            'reorden',
            5
        )

        categoria_id = request.form.get(
            'categoria_id'
        )

        codigo = request.form.get(
            'codigo',
            ''
        ).strip()

        imagen = request.files.get(
            'imagen'
        )

        if not nombre:

            flash(
                'El nombre es obligatorio',
                'error'
            )

            cursor.close()
            liberar(conexion)

            conexion = conectar()
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT id, nombre
                FROM categorias
                ORDER BY nombre
            """)
            categorias = cursor.fetchall()
            cursor.close()
            liberar(conexion)

            return render_template(
                'agregar_producto.html',
                categorias=categorias
            )

        nombre_imagen = subir_imagen_supabase(
            imagen
        )

        cursor.execute('''
            INSERT INTO productos
            (
                nombre,
                precio,
                stock,
                codigo_barra,
                imagen,
                categoria_id,
                reorden
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        ''', (
            nombre,
            precio,
            stock,
            codigo,
            nombre_imagen,
            categoria_id,
            reorden
        ))

        conexion.commit()
        invalidar_cache_alertas()

        cursor.close()
        liberar(conexion)

        registrar_log(
            session['usuario'],
            f'Agregó producto: {nombre}'
        )

        flash(
            f'Producto "{nombre}" agregado correctamente',
            'success'
        )

        return redirect('/productos')

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT id, nombre
        FROM categorias
        ORDER BY nombre
    """)
    categorias = cursor.fetchall()
    cursor.close()
    liberar(conexion)

    return render_template(
        'agregar_producto.html',
        categorias=categorias
    )


# ─────────────────────────────────────────────────
# EDITAR PRODUCTO
# ─────────────────────────────────────────────────

@bp.route(
    '/editar/<int:id>',
    methods=['GET', 'POST']
)
@rol_requerido([
    'admin',
    'supervisor'
])
def editar_producto(id):

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('''
        SELECT *
        FROM productos
        WHERE id = %s
    ''', (id,))

    producto = cursor.fetchone()

    if not producto:

        cursor.close()
        liberar(conexion)

        flash(
            'Producto no encontrado',
            'error'
        )

        return redirect('/productos')

    if request.method == 'POST':

        nombre = request.form.get(
            'nombre',
            ''
        ).strip()

        precio = request.form.get(
            'precio',
            0
        )

        reorden = int(
            request.form.get(
                'reorden',
                5
            )
        )

        categoria_id = request.form.get(
            'categoria_id'
        )

        codigo = request.form.get(
            'codigo',
            ''
        ).strip()

        entradas = int(
            request.form.get(
                'entradas',
                0
            ) or 0
        )

        salidas = int(
            request.form.get(
                'salidas',
                0
            ) or 0
        )

        stock_actual = int(
            producto['stock']
        )

        nuevo_stock = max(
            0,
            stock_actual + entradas - salidas
        )

        cursor.execute('''
            UPDATE productos
            SET nombre       = %s,
                precio       = %s,
                stock        = %s,
                entradas     = %s,
                salidas      = %s,
                codigo_barra = %s,
                categoria_id = %s,
                reorden      = %s
            WHERE id = %s
        ''', (
            nombre,
            precio,
            nuevo_stock,
            entradas,
            salidas,
            codigo,
            categoria_id,
            reorden,
            id
        ))

        conexion.commit()
        invalidar_cache_alertas()

        cursor.close()
        liberar(conexion)

        registrar_log(
            session['usuario'],
            f'Editó producto #{id}: {nombre}'
        )

        flash(
            f'Producto "{nombre}" actualizado',
            'success'
        )

        return redirect('/productos')

    cursor.execute("""
        SELECT id, nombre
        FROM categorias
        ORDER BY nombre
    """)

    categorias = cursor.fetchall()

    cursor.close()
    liberar(conexion)

    return render_template(
        'editar_producto.html',
        producto=producto,
        categorias=categorias
    )

# ─────────────────────────────────────────────────
# ELIMINAR PRODUCTO
# ─────────────────────────────────────────────────

@bp.route('/eliminar/<int:id>')

@rol_requerido([
    'admin'
])

def eliminar_producto(id):

    conexion = conectar()

    cursor = conexion.cursor()

    cursor.execute('''
        SELECT nombre
        FROM productos
        WHERE id = %s
    ''', (id,))

    producto = cursor.fetchone()

    if producto:

        cursor.execute('''
            DELETE FROM productos
            WHERE id = %s
        ''', (id,))

        conexion.commit()
        invalidar_cache_alertas()

        registrar_log(
            session['usuario'],
            f'Eliminó producto #{id}: {producto["nombre"]}'
        )

        flash(
            f'Producto "{producto["nombre"]}" eliminado',
            'success'
        )

    cursor.close()

    liberar(conexion)

    return redirect('/productos')


# ─────────────────────────────────────────────────
# SCANNER BACKEND LOCAL
# ─────────────────────────────────────────────────

@bp.route('/scanner_codigo')

@rol_requerido([
    'admin',
    'supervisor'
])

def scanner_codigo():

    try:

        import cv2

        from pyzbar.pyzbar import (
            decode as pyzbar_decode
        )

    except ImportError:

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

            codigo_detectado = c.data.decode(
                'utf-8'
            )

            break

        cv2.imshow(
            'Escanear Código',
            frame
        )

        tecla = cv2.waitKey(1)

        if tecla == 27 or codigo_detectado:
            break

    cap.release()

    cv2.destroyAllWindows()

    return (codigo_detectado, 200)