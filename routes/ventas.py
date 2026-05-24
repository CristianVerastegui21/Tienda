import os
from datetime import datetime
from flask import flash
from flask import Blueprint, render_template, request, redirect, session, send_file
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    HRFlowable
)

from db import conectar
from utils.auth import rol_requerido
from utils.logs import registrar_log
from utils.scanner import SCANNER, cv2, decode

bp = Blueprint('ventas', __name__)


@bp.route('/ventas', methods=['GET', 'POST'])
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

@bp.route('/buscar_producto_scanner/<codigo>')
@rol_requerido([
    'admin',
    'supervisor',
    'cajero'
])
def buscar_producto_scanner(codigo):

    conexion = conectar()

    producto = conexion.execute('''
        SELECT *
        FROM productos
        WHERE codigo_barra = ?
    ''', (codigo,)).fetchone()

    conexion.close()

    if producto:

        agregar_al_carrito(
            producto,
            1
        )

        flash(
            f'{producto["nombre"]} agregado al carrito',
            'success'
        )

    else:

        flash(
            'Producto no encontrado',
            'warning'
        )

    return redirect('/ventas')


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


@bp.route('/aumentar/<int:index>')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def aumentar(index):
    carrito = session.get('carrito', [])

    if index < 0 or index >= len(carrito):
        return redirect('/ventas')

    conexion = conectar()

    item = carrito[index]

    producto = conexion.execute('''
        SELECT * FROM productos
        WHERE id = ?
    ''', (item['id'],)).fetchone()

    conexion.close()

    if not producto:
        return redirect('/ventas')

    if item['cantidad'] < producto['stock']:
        item['cantidad'] += 1

        item['subtotal'] = (
            item['cantidad']
            *
            item['precio']
        )

    session['carrito'] = carrito

    return redirect('/ventas')


@bp.route('/disminuir/<int:index>')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def disminuir(index):
    carrito = session.get('carrito', [])

    if index < 0 or index >= len(carrito):
        return redirect('/ventas')

    carrito[index]['cantidad'] -= 1

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


@bp.route('/finalizar_venta')
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

    cursor.execute('''
        INSERT INTO ventas (total)
        VALUES (?)
    ''', (total,))

    id_venta = cursor.lastrowid

    for item in carrito:
        producto = conexion.execute('''
            SELECT * FROM productos
            WHERE id = ?
        ''', (item['id'],)).fetchone()

        if item['cantidad'] > producto['stock']:
            conexion.close()
            return redirect('/ventas')

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

    generar_ticket(
        id_venta,
        carrito,
        total
    )

    conexion.close()

    session['carrito'] = []

    registrar_log(
        session['usuario'],
        f'Genero venta #{id_venta}'
    )

    return redirect(
        f'/ticket/{id_venta}'
    )


def generar_ticket(id_venta, carrito, total):
    carpeta = 'static/tickets'

    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    archivo = f"static/tickets/venta_{id_venta}.pdf"

    doc = SimpleDocTemplate(
        archivo,
        pagesize=letter,
        rightMargin=25,
        leftMargin=25,
        topMargin=25,
        bottomMargin=25
    )

    estilos = getSampleStyleSheet()
    elementos = []

    azul = colors.HexColor("#2563eb")
    verde = colors.HexColor("#16a34a")
    gris = colors.HexColor("#6b7280")
    claro = colors.HexColor("#f8fafc")

    titulo = ParagraphStyle(
        'titulo',
        parent=estilos['Heading1'],
        alignment=TA_CENTER,
        fontSize=22,
        textColor=azul,
        spaceAfter=4
    )

    subtitulo = ParagraphStyle(
        'sub',
        parent=estilos['BodyText'],
        alignment=TA_CENTER,
        fontSize=9,
        textColor=gris
    )

    gracias = ParagraphStyle(
        'gracias',
        parent=estilos['BodyText'],
        alignment=TA_CENTER,
        fontSize=11
    )

    logo = 'static/logos/logo.png'

    if os.path.exists(logo):
        img = Image(
            logo,
            width=65,
            height=65
        )

        img.hAlign = 'CENTER'

        elementos.append(img)

    elementos.append(
        Paragraph(
            "BODEGA VERASTEGUI",
            titulo
        )
    )

    elementos.append(
        Paragraph(
            "Sistema Profesional de Gestion y Ventas",
            subtitulo
        )
    )

    elementos.append(
        Paragraph(
            "RUC: 20XXXXXXXXXX",
            subtitulo
        )
    )

    elementos.append(
        Paragraph(
            "Trujillo - Peru",
            subtitulo
        )
    )

    elementos.append(
        Spacer(1, 10)
    )

    linea = HRFlowable(
        width="100%",
        thickness=1,
        color=azul
    )

    elementos.append(linea)

    elementos.append(
        Spacer(1, 8)
    )

    fecha = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    usuario = session.get(
        'usuario',
        'Sistema'
    )

    datos = [
        ["Ticket:", f"#{id_venta}"],
        ["Fecha:", fecha],
        ["Cajero:", usuario]
    ]

    tabla_info = Table(
        datos,
        colWidths=[100, 300]
    )

    tabla_info.setStyle(
        TableStyle([
        ('FONTNAME', (0, 0), (0, -1),
         'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1),
         colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
        ])
    )

    elementos.append(
        tabla_info
    )

    elementos.append(
        Spacer(1, 12)
    )

    elementos.append(
        Paragraph(
            "DETALLE DE PRODUCTOS",
            ParagraphStyle(
                't',
                fontSize=10,
                textColor=gris
            )
        )
    )

    elementos.append(
        Spacer(1, 5)
    )

    data = [[
        "#",
        "Producto",
        "Cant.",
        "Precio",
        "Subtotal"
    ]]

    total_unidades = 0

    for i, item in enumerate(carrito, 1):
        total_unidades += item['cantidad']

        data.append([
            i,
            item['nombre'],
            item['cantidad'],
            f"S/. {item['precio']:.2f}",
            f"S/. {item['subtotal']:.2f}"
        ])

    tabla = Table(
        data,
        colWidths=[30, 220, 50, 80, 90]
    )

    tabla.setStyle(
        TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0),
         azul),
        ('TEXTCOLOR', (0, 0), (-1, 0),
         colors.white),
        ('FONTNAME', (0, 0), (-1, 0),
         'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1),
         .5,
         colors.lightgrey),
        ('ROWBACKGROUNDS',
         (0, 1),
         (-1, -1),
         [colors.white, claro]),
        ('ALIGN',
         (0, 0),
         (-1, -1),
         'CENTER'),
        ('VALIGN',
         (0, 0),
         (-1, -1),
         'MIDDLE')
        ])
    )

    elementos.append(tabla)

    elementos.append(
        Spacer(1, 8)
    )

    elementos.append(
        Paragraph(
            f"{len(carrito)} productos | {total_unidades} unidades",
            subtitulo
        )
    )

    elementos.append(
        Spacer(1, 10)
    )

    caja_total = Table([[
        "TOTAL:",
        f"S/. {total:.2f}"
    ]])

    caja_total.setStyle(
        TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1),
         colors.HexColor("#f0fdf4")),
        ('BOX', (0, 0), (-1, -1),
         1,
         verde),
        ('TEXTCOLOR', (1, 0), (1, 0),
         verde),
        ('FONTNAME', (0, 0), (-1, -1),
         'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0),
         18),
        ('ALIGN', (0, 0), (-1, -1),
         'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1),
         10),
        ('BOTTOMPADDING', (0, 0), (-1, -1),
         10)
        ])
    )

    elementos.append(
        caja_total
    )

    elementos.append(
        Spacer(1, 20)
    )

    codigo = f"{id_venta:06d}"

    barras = "█" * 40

    elementos.append(
        Paragraph(
            barras,
            ParagraphStyle(
            'b',
            alignment=TA_CENTER,
            fontName='Courier'
            )
        )
    )

    elementos.append(
        Paragraph(
            codigo,
            subtitulo
        )
    )

    elementos.append(
        Spacer(1, 15)
    )

    elementos.append(
        Paragraph(
            "Gracias por su compra!",
            gracias
        )
    )

    elementos.append(
        Paragraph(
            "Vuelva pronto",
            subtitulo
        )
    )

    elementos.append(
        Spacer(1, 10)
    )

    elementos.append(
        Paragraph(
            datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            ),
            subtitulo
        )
    )

    doc.build(
        elementos
    )

    return archivo


@bp.route('/ticket/<int:id_venta>')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def ticket(id_venta):
    archivo = f'static/tickets/venta_{id_venta}.pdf'

    return send_file(
        archivo,
        mimetype='application/pdf'
    )


@bp.route('/venta/<int:id>')
@rol_requerido(['admin', 'supervisor', 'cajero'])
def ver_venta(id):
    conexion = conectar()

    venta = conexion.execute('''
        SELECT *
        FROM ventas
        WHERE id=?
    ''', (id,)).fetchone()

    detalles = conexion.execute('''
        SELECT
            d.*,
            p.nombre,
            p.precio

        FROM detalle_venta d

        INNER JOIN productos p
        ON d.id_producto = p.id

        WHERE d.id_venta = ?

    ''', (id,)).fetchall()

    conexion.close()

    return render_template(
        'venta_detalle.html',
        venta=venta,
        detalles=detalles
    )
