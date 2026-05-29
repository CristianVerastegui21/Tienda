import os
from datetime import datetime

from flask import Blueprint, render_template, send_file
from openpyxl import Workbook

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from db import conectar
from utils.auth import rol_requerido

bp = Blueprint('reportes', __name__)


# ─────────────────────────────────────────────
# HISTORIAL
# ─────────────────────────────────────────────

@bp.route('/historial')

@rol_requerido([
    'admin',
    'supervisor'
])

def historial():

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('''
        SELECT *
        FROM ventas
        ORDER BY fecha DESC
    ''')

    ventas = cursor.fetchall()

    conexion.close()

    return render_template(
        'historial.html',
        ventas=ventas
    )


# ─────────────────────────────────────────────
# REPORTES
# ─────────────────────────────────────────────

@bp.route('/reportes')

@rol_requerido([
    'admin',
    'supervisor'
])

def reportes():

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('''
        SELECT *
        FROM ventas
        ORDER BY fecha DESC
    ''')

    ventas = cursor.fetchall()

    total_ventas = len(ventas)

    ingresos = sum(
        float(venta['total'])
        for venta in ventas
    )

    cursor.execute('''
        SELECT
            DATE(fecha) as dia,
            SUM(total) as total

        FROM ventas

        GROUP BY DATE(fecha)

        ORDER BY DATE(fecha)
    ''')

    grafico = cursor.fetchall()

    dias = [
        str(x['dia'])
        for x in grafico
    ]

    totales = [
        float(x['total'])
        for x in grafico
    ]

    cursor.execute('''
        SELECT
            productos.nombre,
            SUM(detalle_venta.cantidad) as total

        FROM detalle_venta

        INNER JOIN productos
        ON productos.id = detalle_venta.id_producto

        GROUP BY productos.nombre

        ORDER BY total DESC

        LIMIT 10
    ''')

    productos_top = cursor.fetchall()

    nombres_productos = [
        p['nombre']
        for p in productos_top
    ]

    cantidades_productos = [
        int(p['total'])
        for p in productos_top
    ]

    cursor.execute('''
        SELECT *
        FROM productos
        WHERE stock <= 5
    ''')

    stock_bajo = cursor.fetchall()

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


# ─────────────────────────────────────────────
# REPORTE PDF
# ─────────────────────────────────────────────

@bp.route('/reporte_pdf')

@rol_requerido([
    'admin',
    'supervisor'
])

def reporte_pdf():

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('''
        SELECT COUNT(*) as total
        FROM ventas
    ''')

    total_ventas = cursor.fetchone()['total']

    cursor.execute('''
        SELECT COALESCE(SUM(total),0) as total
        FROM ventas
    ''')

    ingresos = float(
        cursor.fetchone()['total']
    )

    cursor.execute('''
        SELECT
            productos.nombre,
            SUM(detalle_venta.cantidad) as vendidos

        FROM detalle_venta

        INNER JOIN productos
        ON productos.id = detalle_venta.id_producto

        GROUP BY productos.nombre

        ORDER BY vendidos DESC

        LIMIT 10
    ''')

    productos_top = cursor.fetchall()

    cursor.execute('''
        SELECT nombre, stock
        FROM productos
        WHERE stock <= reorden
    ''')

    stock_bajo = cursor.fetchall()

    conexion.close()

    carpeta = 'reportes'

    os.makedirs(
        carpeta,
        exist_ok=True
    )

    archivo = 'reportes/reporte_general.pdf'

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

    titulo = Paragraph(
        "REPORTE PROFESIONAL - BODEGA VERASTEGUI",
        estilos['Title']
    )

    elementos.append(titulo)

    elementos.append(
        Spacer(1, 20)
    )

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

    elementos.append(
        Spacer(1, 25)
    )

    subtitulo1 = Paragraph(
        "Productos Mas Vendidos",
        estilos['Heading2']
    )

    elementos.append(subtitulo1)

    elementos.append(
        Spacer(1, 10)
    )

    datos_top = [[
        'Producto',
        'Vendidos'
    ]]

    for p in productos_top:

        datos_top.append([
            p['nombre'],
            p['vendidos']
        ])

    tabla_top = Table(
        datos_top,
        colWidths=[300, 150]
    )

    tabla_top.setStyle(TableStyle([

        (
            'BACKGROUND',
            (0, 0),
            (-1, 0),
            colors.HexColor('#2575fc')
        ),

        (
            'TEXTCOLOR',
            (0, 0),
            (-1, 0),
            colors.white
        ),

        (
            'FONTNAME',
            (0, 0),
            (-1, 0),
            'Helvetica-Bold'
        ),

        (
            'GRID',
            (0, 0),
            (-1, -1),
            1,
            colors.black
        ),

        (
            'BACKGROUND',
            (0, 1),
            (-1, -1),
            colors.whitesmoke
        ),

        (
            'ALIGN',
            (1, 1),
            (-1, -1),
            'CENTER'
        )

    ]))

    elementos.append(tabla_top)

    elementos.append(
        Spacer(1, 25)
    )

    subtitulo2 = Paragraph(
        "Productos con Bajo Stock",
        estilos['Heading2']
    )

    elementos.append(subtitulo2)

    elementos.append(
        Spacer(1, 10)
    )

    datos_stock = [[
        'Producto',
        'Stock'
    ]]

    for p in stock_bajo:

        datos_stock.append([
            p['nombre'],
            p['stock']
        ])

    tabla_stock = Table(
        datos_stock,
        colWidths=[300, 150]
    )

    tabla_stock.setStyle(TableStyle([

        (
            'BACKGROUND',
            (0, 0),
            (-1, 0),
            colors.red
        ),

        (
            'TEXTCOLOR',
            (0, 0),
            (-1, 0),
            colors.white
        ),

        (
            'FONTNAME',
            (0, 0),
            (-1, 0),
            'Helvetica-Bold'
        ),

        (
            'GRID',
            (0, 0),
            (-1, -1),
            1,
            colors.black
        ),

        (
            'BACKGROUND',
            (0, 1),
            (-1, -1),
            colors.beige
        ),

        (
            'ALIGN',
            (1, 1),
            (-1, -1),
            'CENTER'
        )

    ]))

    elementos.append(tabla_stock)

    elementos.append(
        Spacer(1, 30)
    )

    footer = Paragraph(
        """
        <para align=center>
        <font size=9 color=grey>
        Sistema desarrollado con Flask + PostgreSQL + Supabase<br/>
        Reporte generado automaticamente
        </font>
        </para>
        """,
        estilos['BodyText']
    )

    elementos.append(footer)

    doc.build(elementos)

    return send_file(
        archivo,
        as_attachment=True
    )


# ─────────────────────────────────────────────
# EXPORTAR EXCEL
# ─────────────────────────────────────────────

@bp.route('/exportar_ventas')

@rol_requerido([
    'admin',
    'supervisor'
])

def exportar_ventas():

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('''
        SELECT *
        FROM ventas
        ORDER BY fecha DESC
    ''')

    ventas = cursor.fetchall()

    conexion.close()

    os.makedirs(
        'reportes',
        exist_ok=True
    )

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
            float(venta['total']),
            str(venta['fecha'])
        ])

    archivo = 'reportes/ventas.xlsx'

    wb.save(archivo)

    return send_file(
        archivo,
        as_attachment=True
    )