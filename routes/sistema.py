from flask import Blueprint, render_template

from db import conectar
from utils.auth import rol_requerido
from utils.backup import crear_backup

bp = Blueprint(
    'sistema',
    __name__
)


# ─────────────────────────────────────────────
# BACKUP
# ─────────────────────────────────────────────

@bp.route('/backup')

@rol_requerido([
    'admin'
])

def backup():

    archivo = crear_backup()

    return f'''
        <h1>Backup creado correctamente</h1>

        <p>{archivo}</p>

        <a href="/dashboard">
            Volver al Dashboard
        </a>
    '''


# ─────────────────────────────────────────────
# LOGS
# ─────────────────────────────────────────────

@bp.route('/logs')

@rol_requerido([
    'admin'
])

def logs():

    conexion = conectar()

    cursor = conexion.cursor()

    cursor.execute('''
        SELECT *
        FROM logs
        ORDER BY fecha DESC
    ''')

    logs = cursor.fetchall()

    conexion.close()

    return render_template(
        'logs.html',
        logs=logs
    )


# ─────────────────────────────────────────────
# STOCK BAJO
# ─────────────────────────────────────────────

@bp.route('/stock_bajo')

@rol_requerido([
    'admin',
    'supervisor'
])

def stock_bajo():

    conexion = conectar()

    cursor = conexion.cursor()

    cursor.execute('''
        SELECT *
        FROM productos
        WHERE stock <= reorden
        ORDER BY stock ASC
    ''')

    productos = cursor.fetchall()

    conexion.close()

    return render_template(
        'stock_bajo.html',
        productos=productos
    )