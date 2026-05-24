from flask import Blueprint, render_template, request, redirect
from werkzeug.security import generate_password_hash

from db import conectar
from utils.auth import rol_requerido

bp = Blueprint('usuarios', __name__)


@bp.route('/usuarios')
@rol_requerido(['admin'])
def usuarios():
    conexion = conectar()

    usuarios = conexion.execute('''
        SELECT * FROM usuarios
        ORDER BY id DESC
    ''').fetchall()

    conexion.close()

    admins = len(
        [u for u in usuarios
         if u["rol"] == "admin"]
    )

    supervisores = len(
        [u for u in usuarios
         if u["rol"] == "supervisor"]
    )

    cajeros = len(
        [u for u in usuarios
         if u["rol"] == "cajero"]
    )

    return render_template(
        'usuarios.html',
        usuarios=usuarios,
        admins=admins,
        supervisores=supervisores,
        cajeros=cajeros
    )


@bp.route('/agregar_usuario', methods=['GET', 'POST'])
@rol_requerido(['admin'])
def agregar_usuario():
    if request.method == 'POST':
        nombre = request.form['nombre']
        usuario = request.form['usuario']
        password = request.form['password']
        rol = request.form['rol']

        conexion = conectar()

        conexion.execute('''
            INSERT INTO usuarios
            (nombre, usuario, password, rol)

            VALUES (?, ?, ?, ?)
        ''', (
            nombre,
            usuario,
            generate_password_hash(password),
            rol
        ))

        conexion.commit()
        conexion.close()

        return redirect('/usuarios')

    return render_template('agregar_usuario.html')


@bp.route('/eliminar_usuario/<int:id>')
@rol_requerido(['admin'])
def eliminar_usuario(id):
    conexion = conectar()

    conexion.execute('''
        DELETE FROM usuarios
        WHERE id = ?
    ''', (id,))

    conexion.commit()
    conexion.close()

    return redirect('/usuarios')
