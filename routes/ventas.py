import os
from datetime import datetime
from flask import (
    Blueprint, render_template, request,
    redirect, session, send_file, flash
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, Image, HRFlowable
)

from db import conectar
from utils.auth import rol_requerido
from utils.logs import registrar_log

bp = Blueprint('ventas', __name__)


# ────────────────────────────────────────────────────────────
# PUNTO DE VENTA
# ────────────────────────────────────────────────────────────
@bp.route('/ventas', methods=['GET', 'POST'])
@rol_requerido(['admin', 'supervisor', 'cajero'])
def ventas():
    conexion  = conectar()
    productos = conexion.execute('SELECT * FROM productos ORDER BY nombre').fetchall()

    if 'carrito' not in session:
        session['carrito'] = []

    carrito = session['carrito']

    if request.method == 'POST':
        id_producto = request.form.get('producto_id')
        cantidad    = int(request.form.get('cantidad', 1))

        producto = conexion.execute(
            'SELECT * FROM productos WHERE id = ?', (id_producto,)
        ).fetchone()

        conexion.close()

        if not producto:
            flash('Producto no encontrado', 'error')
            return redirect('/ventas')

        if cantidad > producto['stock']:
            flash(f'Stock insuficiente para "{producto["nombre"]}"', 'error')
            return redirect('/ventas')

        _agregar_al_carrito(producto, cantidad)
        return redirect('/ventas')

    total = sum(item['subtotal'] for item in carrito)
    conexion.close()

    return render_template(
        'ventas.html',
        productos=productos,
        carrito=carrito,
        total=total
    )


# ────────────────────────────────────────────────────────────
# SCANNER VENTAS — solo modo local (cv2)
# En producción (Render), el scanner es 100% frontend
# ────────────────────────────────────────────────────────────
@bp.route('/scanner_ventas')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def scanner_ventas():
    try:
        import cv2
        from pyzbar.pyzbar import decode as pyzbar_decode
    except ImportError:
        return redirect('/ventas')

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return redirect('/ventas')

    codigo_detectado = ''
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        for c in pyzbar_decode(frame):
            codigo_detectado = c.data.decode('utf-8')
            break
        cv2.imshow('Scanner Ventas — ESC para salir', frame)
        if cv2.waitKey(1) == 27 or codigo_detectado:
            break

    cap.release()
    cv2.destroyAllWindows()

    if codigo_detectado:
        conexion = conectar()
        producto = conexion.execute(
            'SELECT * FROM productos WHERE codigo_barra = ?',
            (codigo_detectado,)
        ).fetchone()
        conexion.close()
        if producto:
            _agregar_al_carrito(producto, 1)

    return redirect('/ventas')


# ────────────────────────────────────────────────────────────
# CARRITO — helpers internos
# ────────────────────────────────────────────────────────────
def _agregar_al_carrito(producto, cantidad=1):
    """Agrega o incrementa un producto en la sesión del carrito."""
    if 'carrito' not in session:
        session['carrito'] = []

    carrito = session['carrito']

    for item in carrito:
        if item['id'] == producto['id']:
            item['cantidad'] += cantidad
            item['subtotal']  = item['cantidad'] * item['precio']
            session['carrito'] = carrito
            return

    carrito.append({
        'id':       producto['id'],
        'nombre':   producto['nombre'],
        'precio':   producto['precio'],
        'cantidad': cantidad,
        'subtotal': producto['precio'] * cantidad,
    })
    session['carrito'] = carrito


# ────────────────────────────────────────────────────────────
# CARRITO — rutas
# ────────────────────────────────────────────────────────────
@bp.route('/aumentar/<int:index>')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def aumentar(index):
    carrito = session.get('carrito', [])
    if not (0 <= index < len(carrito)):
        return redirect('/ventas')

    conexion = conectar()
    prod = conexion.execute(
        'SELECT stock FROM productos WHERE id = ?',
        (carrito[index]['id'],)
    ).fetchone()
    conexion.close()

    if prod and carrito[index]['cantidad'] < prod['stock']:
        carrito[index]['cantidad'] += 1
        carrito[index]['subtotal']  = carrito[index]['cantidad'] * carrito[index]['precio']

    session['carrito'] = carrito
    return redirect('/ventas')


@bp.route('/disminuir/<int:index>')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def disminuir(index):
    carrito = session.get('carrito', [])
    if not (0 <= index < len(carrito)):
        return redirect('/ventas')

    carrito[index]['cantidad'] -= 1

    if carrito[index]['cantidad'] <= 0:
        carrito.pop(index)
    else:
        carrito[index]['subtotal'] = carrito[index]['cantidad'] * carrito[index]['precio']

    session['carrito'] = carrito
    return redirect('/ventas')


@bp.route('/eliminar_carrito/<int:index>')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def eliminar_carrito(index):
    carrito = session.get('carrito', [])
    if 0 <= index < len(carrito):
        carrito.pop(index)
    session['carrito'] = carrito
    return redirect('/ventas')


@bp.route('/vaciar_carrito')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def vaciar_carrito():
    session['carrito'] = []
    return redirect('/ventas')


# ────────────────────────────────────────────────────────────
# FINALIZAR VENTA
# ────────────────────────────────────────────────────────────
@bp.route('/finalizar_venta')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def finalizar_venta():
    conexion = conectar()
    carrito  = session.get('carrito', [])

    if not carrito:
        conexion.close()
        return redirect('/ventas')

    total  = sum(item['subtotal'] for item in carrito)
    cursor = conexion.cursor()

    # Crear venta
    cursor.execute('INSERT INTO ventas (total) VALUES (?)', (total,))
    id_venta = cursor.lastrowid

    for item in carrito:
        prod = conexion.execute(
            'SELECT * FROM productos WHERE id = ?', (item['id'],)
        ).fetchone()

        if not prod or item['cantidad'] > prod['stock']:
            conexion.close()
            flash('Error de stock al finalizar la venta. Revisa el carrito.', 'error')
            return redirect('/ventas')

        conexion.execute('''
            INSERT INTO detalle_venta (id_venta, id_producto, cantidad, subtotal)
            VALUES (?, ?, ?, ?)
        ''', (id_venta, item['id'], item['cantidad'], item['subtotal']))

        conexion.execute(
            'UPDATE productos SET stock = stock - ? WHERE id = ?',
            (item['cantidad'], item['id'])
        )

    conexion.commit()

    # Generar PDF del ticket
    generar_ticket(id_venta, carrito, total)

    conexion.close()
    session['carrito'] = []

    registrar_log(session['usuario'], f'Generó venta #{id_venta}')
    return redirect(f'/ticket/{id_venta}')


# ────────────────────────────────────────────────────────────
# TICKET PDF
# ────────────────────────────────────────────────────────────
def generar_ticket(id_venta, carrito, total):
    carpeta = 'static/tickets'
    os.makedirs(carpeta, exist_ok=True)
    archivo = f'{carpeta}/venta_{id_venta}.pdf'

    doc = SimpleDocTemplate(
        archivo, pagesize=letter,
        rightMargin=25, leftMargin=25,
        topMargin=25,  bottomMargin=25
    )

    estilos = getSampleStyleSheet()
    azul    = colors.HexColor('#2563eb')
    verde   = colors.HexColor('#16a34a')
    gris    = colors.HexColor('#6b7280')
    claro   = colors.HexColor('#f8fafc')

    st_titulo = ParagraphStyle(
        'titulo', parent=estilos['Heading1'],
        alignment=TA_CENTER, fontSize=22,
        textColor=azul, spaceAfter=4
    )
    st_sub = ParagraphStyle(
        'sub', parent=estilos['BodyText'],
        alignment=TA_CENTER, fontSize=9, textColor=gris
    )
    st_gracias = ParagraphStyle(
        'gracias', parent=estilos['BodyText'],
        alignment=TA_CENTER, fontSize=11
    )

    elems = []

    # Logo
    logo = 'static/logos/logo.png'
    if os.path.exists(logo):
        img = Image(logo, width=65, height=65)
        img.hAlign = 'CENTER'
        elems.append(img)

    elems += [
        Paragraph('BODEGA VERASTEGUI', st_titulo),
        Paragraph('Sistema Profesional de Gestión y Ventas', st_sub),
        Paragraph('Trujillo — Perú', st_sub),
        Spacer(1, 10),
        HRFlowable(width='100%', thickness=1, color=azul),
        Spacer(1, 8),
    ]

    # Info de venta
    fecha   = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    usuario = session.get('usuario', 'Sistema')

    tabla_info = Table(
        [['Ticket:', f'#{id_venta}'], ['Fecha:', fecha], ['Cajero:', usuario]],
        colWidths=[100, 300]
    )
    tabla_info.setStyle(TableStyle([
        ('FONTNAME',      (0,0), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR',     (0,0), (0,-1), colors.grey),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elems += [tabla_info, Spacer(1, 12),
              Paragraph('DETALLE DE PRODUCTOS', ParagraphStyle('t', fontSize=10, textColor=gris)),
              Spacer(1, 5)]

    # Tabla de productos
    data = [['#', 'Producto', 'Cant.', 'Precio', 'Subtotal']]
    total_unidades = 0
    for i, item in enumerate(carrito, 1):
        total_unidades += item['cantidad']
        data.append([i, item['nombre'], item['cantidad'],
                     f"S/. {item['precio']:.2f}", f"S/. {item['subtotal']:.2f}"])

    tabla = Table(data, colWidths=[30, 220, 50, 80, 90])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), azul),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID',       (0,0), (-1,-1), .5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, claro]),
        ('ALIGN',  (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    elems += [tabla, Spacer(1,8),
              Paragraph(f"{len(carrito)} productos | {total_unidades} unidades", st_sub),
              Spacer(1, 10)]

    # Total
    caja_total = Table([['TOTAL:', f'S/. {total:.2f}']])
    caja_total.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('BOX',        (0,0), (-1,-1), 1, verde),
        ('TEXTCOLOR',  (1,0), (1,0),   verde),
        ('FONTNAME',   (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE',   (1,0), (1,0),   18),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))

    elems += [caja_total, Spacer(1,20),
              Paragraph('¡Gracias por su compra!', st_gracias),
              Paragraph('Vuelva pronto', st_sub),
              Spacer(1,10),
              Paragraph(datetime.now().strftime('%d/%m/%Y %H:%M'), st_sub)]

    doc.build(elems)
    return archivo


@bp.route('/ticket/<int:id_venta>')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def ticket(id_venta):
    archivo = f'static/tickets/venta_{id_venta}.pdf'
    return send_file(archivo, mimetype='application/pdf')


@bp.route('/venta/<int:id>')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def ver_venta(id):
    conexion = conectar()
    venta    = conexion.execute('SELECT * FROM ventas WHERE id=?', (id,)).fetchone()
    detalles = conexion.execute('''
        SELECT d.*, p.nombre, p.precio
        FROM detalle_venta d
        INNER JOIN productos p ON d.id_producto = p.id
        WHERE d.id_venta = ?
    ''', (id,)).fetchall()
    conexion.close()
    return render_template('venta_detalle.html', venta=venta, detalles=detalles)