from flask import Blueprint, render_template

from database import conectar
from utils.auth import rol_requerido

bp = Blueprint('dashboard', __name__)


@bp.route('/')
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


@bp.route('/dashboard')
@rol_requerido(['admin', 'supervisor'])
def dashboard():
    conexion = conectar()

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

    stock_bajo = conexion.execute('''
        SELECT *
        FROM productos
        WHERE stock <= reorden
        ORDER BY stock ASC
    ''').fetchall()

    ultimas_ventas = conexion.execute('''
        SELECT *
        FROM ventas
        ORDER BY fecha DESC
        LIMIT 5
    ''').fetchall()

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


def registrar_alertas_globales(app):
    @app.context_processor
    def alertas_globales():
        conexion = conectar()

        alertas = conexion.execute('''

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
