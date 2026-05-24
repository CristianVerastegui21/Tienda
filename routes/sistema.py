from flask import Blueprint, render_template

from database import conectar
from utils.auth import rol_requerido
from utils.backup import crear_backup

bp = Blueprint('sistema', __name__)


@bp.route('/backup')
@rol_requerido(['admin'])
def backup():
    archivo = crear_backup()

    return f'''
        <h1>Backup creado</h1>

        <p>{archivo}</p>

        <a href="/dashboard">
            Volver
        </a>
    '''


@bp.route('/logs')
@rol_requerido(['admin'])
def logs():
    conexion = conectar()

    logs = conexion.execute('''
        SELECT * FROM logs
        ORDER BY fecha DESC
    ''').fetchall()

    conexion.close()

    return render_template(
        'logs.html',
        logs=logs
    )


@bp.route('/stock_bajo')
@rol_requerido([
    'admin',
    'supervisor'
])
def stock_bajo():
    conexion = conectar()

    productos = conexion.execute('''

        SELECT *

        FROM productos

        WHERE stock <= reorden

        ORDER BY stock ASC

    ''').fetchall()

    conexion.close()

    return render_template(
        'stock_bajo.html',
        productos=productos
    )
