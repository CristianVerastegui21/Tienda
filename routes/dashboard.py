from flask import (
    Blueprint,
    render_template
)

from db import conectar

from utils.auth import rol_requerido


bp = Blueprint(
    'dashboard',
    __name__
)


# ─────────────────────────────────────────────
# INICIO
# ─────────────────────────────────────────────

@bp.route('/')

@rol_requerido([
    'admin',
    'supervisor',
    'cajero'
])

def index():

    conexion = conectar()

    cursor = conexion.cursor()

    cursor.execute('''
        SELECT COUNT(*) AS total
        FROM productos
    ''')

    total_productos = cursor.fetchone()['total']

    cursor.execute('''
        SELECT COUNT(*) AS total
        FROM ventas
    ''')

    total_ventas = cursor.fetchone()['total']

    cursor.execute('''
        SELECT COALESCE(SUM(total), 0) AS total
        FROM ventas
    ''')

    ingresos = cursor.fetchone()['total']

    cursor.execute('''
        SELECT COUNT(*) AS total
        FROM productos
        WHERE stock <= 5
    ''')

    stock_bajo = cursor.fetchone()['total']

    conexion.close()

    return render_template(
        'index.html',
        total_productos=total_productos,
        total_ventas=total_ventas,
        ingresos=ingresos,
        stock_bajo=stock_bajo
    )


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@bp.route('/dashboard')

@rol_requerido([
    'admin',
    'supervisor'
])

def dashboard():

    conexion = conectar()

    cursor = conexion.cursor()

    # TOTAL PRODUCTOS
    cursor.execute('''
        SELECT COUNT(*) AS total
        FROM productos
    ''')

    total_productos = cursor.fetchone()['total']

    # TOTAL VENTAS
    cursor.execute('''
        SELECT COUNT(*) AS total
        FROM ventas
    ''')

    total_ventas = cursor.fetchone()['total']

    # INGRESOS
    cursor.execute('''
        SELECT COALESCE(SUM(total), 0) AS total
        FROM ventas
    ''')

    ingresos = cursor.fetchone()['total']

    # STOCK BAJO
    cursor.execute('''
        SELECT *
        FROM productos
        WHERE stock <= reorden
        ORDER BY stock ASC
    ''')

    stock_bajo = cursor.fetchall()

    # ÚLTIMAS VENTAS
    cursor.execute('''
        SELECT *
        FROM ventas
        ORDER BY fecha DESC
        LIMIT 5
    ''')

    ultimas_ventas = cursor.fetchall()

    # GRÁFICO VENTAS
    cursor.execute('''
        SELECT
            DATE(fecha) AS dia,
            SUM(total) AS total
        FROM ventas
        GROUP BY DATE(fecha)
        ORDER BY DATE(fecha)
    ''')

    grafico = cursor.fetchall()

    dias = [
        str(item['dia'])
        for item in grafico
    ]

    totales = [
        float(item['total'])
        for item in grafico
    ]

    # PRODUCTOS MÁS VENDIDOS
    cursor.execute('''
        SELECT
            productos.nombre,
            SUM(detalle_venta.cantidad) AS total

        FROM detalle_venta

        INNER JOIN productos
        ON productos.id = detalle_venta.id_producto

        GROUP BY productos.nombre

        ORDER BY total DESC

        LIMIT 5
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


# ─────────────────────────────────────────────
# ALERTAS GLOBALES
# ─────────────────────────────────────────────

def registrar_alertas_globales(app):

    @app.context_processor
    def alertas_globales():

        try:

            conexion = conectar()

            cursor = conexion.cursor()

            cursor.execute('''
                SELECT *
                FROM productos
                WHERE stock <= reorden
                ORDER BY stock ASC
                LIMIT 5
            ''')

            alertas = cursor.fetchall()

            conexion.close()

            return dict(
                alertas=alertas,
                total_alertas=len(alertas)
            )

        except Exception:

            return dict(
                alertas=[],
                total_alertas=0
            )