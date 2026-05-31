import os
from datetime import datetime
from urllib.parse import urlencode

from flask import Blueprint, render_template, request, send_file

from db import conectar
from utils.auth import rol_requerido
from utils.reportes_export import generar_excel_reporte, generar_pdf_reporte
from utils.reportes_filtros import parse_filtros, sql_grupo_fecha, sql_filtro_fecha

bp = Blueprint('reportes', __name__)


def _query_string_desde_request():
    if not request.args:
        return ''
    return urlencode(request.args)


def _obtener_datos_reporte(cursor, filtros):
    desde = filtros['desde']
    hasta = filtros['hasta']
    filtro_fecha = sql_filtro_fecha()

    cursor.execute(f'''
        SELECT *
        FROM ventas
        WHERE {filtro_fecha}
        ORDER BY fecha DESC
    ''', (desde, hasta))
    ventas = cursor.fetchall()

    total_ventas = len(ventas)
    ingresos = sum(float(v['total']) for v in ventas)

    grupo_sql, alias = sql_grupo_fecha(filtros['agrupar'])
    cursor.execute(f'''
        SELECT
            {grupo_sql} AS {alias},
            SUM(total) AS total
        FROM ventas
        WHERE {filtro_fecha}
        GROUP BY {grupo_sql}
        ORDER BY {grupo_sql}
    ''', (desde, hasta))
    grafico = cursor.fetchall()

    dias = [str(x[alias]) for x in grafico]
    totales = [float(x['total']) for x in grafico]

    cursor.execute('''
        SELECT
            productos.nombre,
            SUM(detalle_venta.cantidad) AS total
        FROM detalle_venta
        INNER JOIN ventas ON ventas.id = detalle_venta.id_venta
        INNER JOIN productos ON productos.id = detalle_venta.id_producto
        WHERE ventas.fecha::date BETWEEN %s AND %s
        GROUP BY productos.nombre
        ORDER BY total DESC
        LIMIT 10
    ''', (desde, hasta))
    productos_top = cursor.fetchall()

    nombres_productos = [p['nombre'] for p in productos_top]
    cantidades_productos = [int(p['total']) for p in productos_top]
    unidades = sum(cantidades_productos)

    cursor.execute('''
        SELECT *
        FROM productos
        WHERE stock <= reorden
        ORDER BY stock ASC
    ''')
    stock_bajo = cursor.fetchall()

    resumen = {
        'total_ventas': total_ventas,
        'ingresos': ingresos,
        'unidades': unidades,
        'stock_bajo_total': len(stock_bajo),
    }

    return {
        'ventas': ventas,
        'total_ventas': total_ventas,
        'ingresos': ingresos,
        'dias': dias,
        'totales': totales,
        'productos_top': productos_top,
        'nombres_productos': nombres_productos,
        'cantidades_productos': cantidades_productos,
        'stock_bajo': stock_bajo,
        'productos_vendidos_total': unidades,
        'stock_bajo_total': len(stock_bajo),
        'resumen': resumen,
    }


@bp.route('/historial')
@rol_requerido(['admin', 'supervisor'])
def historial():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM ventas ORDER BY fecha DESC')
    ventas = cursor.fetchall()
    conexion.close()
    return render_template('historial.html', ventas=ventas)


@bp.route('/reportes')
@rol_requerido(['admin', 'supervisor'])
def reportes():
    filtros = parse_filtros(request.args)

    conexion = conectar()
    cursor = conexion.cursor()
    datos = _obtener_datos_reporte(cursor, filtros)
    conexion.close()

    return render_template(
        'reportes.html',
        filtros=filtros,
        query_string=_query_string_desde_request(),
        **datos,
    )


@bp.route('/reporte_pdf')
@rol_requerido(['admin', 'supervisor'])
def reporte_pdf():
    filtros = parse_filtros(request.args)

    conexion = conectar()
    cursor = conexion.cursor()
    datos = _obtener_datos_reporte(cursor, filtros)
    conexion.close()

    os.makedirs('reportes', exist_ok=True)
    slug = filtros['desde'].replace('-', '')
    archivo = f'reportes/reporte_{slug}.pdf'

    generar_pdf_reporte(
        archivo,
        filtros,
        datos['resumen'],
        datos['ventas'],
        datos['productos_top'],
        datos['stock_bajo'],
    )

    return send_file(
        archivo,
        as_attachment=True,
        download_name=f'reporte_bodega_{filtros["desde"]}.pdf',
    )


@bp.route('/exportar_ventas')
@rol_requerido(['admin', 'supervisor'])
def exportar_ventas():
    filtros = parse_filtros(request.args)

    conexion = conectar()
    cursor = conexion.cursor()
    datos = _obtener_datos_reporte(cursor, filtros)
    conexion.close()

    os.makedirs('reportes', exist_ok=True)
    archivo = f'reportes/reporte_{filtros["desde"]}.xlsx'

    generar_excel_reporte(
        archivo,
        filtros,
        datos['resumen'],
        datos['ventas'],
        datos['productos_top'],
        datos['stock_bajo'],
    )

    return send_file(
        archivo,
        as_attachment=True,
        download_name=f'reporte_bodega_{filtros["desde"]}.xlsx',
    )
