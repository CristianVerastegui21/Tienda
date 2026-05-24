import os

from flask import Blueprint, render_template, request, redirect, session
from werkzeug.utils import secure_filename

from database import conectar
from utils.auth import rol_requerido
from utils.logs import registrar_log
from utils.scanner import SCANNER, cv2, decode

bp = Blueprint('productos', __name__)


@bp.route('/productos')
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


@bp.route('/agregar', methods=['GET', 'POST'])
@rol_requerido(['admin', 'supervisor'])
def agregar_producto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = request.form['precio']
        stock = request.form['stock']
        reorden = request.form.get('reorden', 1)
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

            ''', (
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
            f'Agrego producto {nombre}'
        )

        return redirect('/productos')

    return render_template('agregar_producto.html')


@bp.route('/scanner_codigo')
@rol_requerido(['admin', 'supervisor'])
def scanner_codigo():
    if not SCANNER:
        return "Scanner no disponible en servidor"

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        return 'No se pudo abrir la camara'

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

        if tecla == 27 or codigo_detectado:
            break

    cap.release()

    cv2.destroyAllWindows()

    return codigo_detectado

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@rol_requerido(['admin', 'supervisor'])
def editar_producto(id):

    conexion = conectar()

    producto = conexion.execute('''
        SELECT * FROM productos
        WHERE id=?
    ''',(id,)).fetchone()

    if request.method=='POST':

        nombre = request.form['nombre']
        precio = request.form['precio']
        codigo = request.form['codigo']

        reorden = int(
            request.form.get('reorden',5)
        )

        entradas = int(
            request.form.get('entradas',0)
        )

        salidas = int(
            request.form.get('salidas',0)
        )

        # stock actual + nuevas entradas
        stock = int(producto['stock']) + entradas - salidas

        conexion.execute('''
            UPDATE productos
            SET
            nombre=?,
            precio=?,
            stock=?,
            entradas=?,
            salidas=?,
            codigo_barra=?,
            reorden=?
            WHERE id=?
        ''',(

            nombre,
            precio,
            stock,
            entradas,
            salidas,
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



@bp.route('/eliminar/<int:id>')
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
