from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash
)

from werkzeug.security import (
    generate_password_hash
)

from db import conectar

from utils.auth import rol_requerido


bp = Blueprint(
    'usuarios',
    __name__
)


# ─────────────────────────────────────────────
# LISTAR USUARIOS
# ─────────────────────────────────────────────

@bp.route('/usuarios')

@rol_requerido([
    'admin'
])

def usuarios():

    conexion = conectar()

    cursor = conexion.cursor()

    cursor.execute('''
        SELECT *
        FROM usuarios
        ORDER BY id DESC
    ''')

    usuarios = cursor.fetchall()

    conexion.close()

    admins = len([
        u for u in usuarios
        if u['rol'] == 'admin'
    ])

    supervisores = len([
        u for u in usuarios
        if u['rol'] == 'supervisor'
    ])

    cajeros = len([
        u for u in usuarios
        if u['rol'] == 'cajero'
    ])

    return render_template(
        'usuarios.html',
        usuarios=usuarios,
        admins=admins,
        supervisores=supervisores,
        cajeros=cajeros
    )


# ─────────────────────────────────────────────
# AGREGAR USUARIO
# ─────────────────────────────────────────────

@bp.route(
    '/agregar_usuario',
    methods=['GET', 'POST']
)

@rol_requerido([
    'admin'
])

def agregar_usuario():

    if request.method == 'POST':

        nombre = request.form['nombre']

        usuario = request.form['usuario']

        password = request.form['password']

        rol = request.form['rol']

        conexion = conectar()

        cursor = conexion.cursor()

        cursor.execute('''
            INSERT INTO usuarios
            (
                nombre,
                usuario,
                password,
                rol
            )

            VALUES (%s, %s, %s, %s)
        ''', (
            nombre,
            usuario,
            generate_password_hash(password),
            rol
        ))

        conexion.commit()

        conexion.close()

        flash(
            'Usuario agregado correctamente',
            'success'
        )

        return redirect('/usuarios')

    return render_template(
        'agregar_usuario.html'
    )


# ─────────────────────────────────────────────
# EDITAR USUARIO
# ─────────────────────────────────────────────

@bp.route(
    '/editar_usuario/<int:id>',
    methods=['GET', 'POST']
)

@rol_requerido([
    'admin'
])

def editar_usuario(id):

    conexion = conectar()

    cursor = conexion.cursor()

    cursor.execute('''
        SELECT *
        FROM usuarios
        WHERE id = %s
    ''', (id,))

    usuario = cursor.fetchone()

    if not usuario:

        conexion.close()

        return redirect('/usuarios')

    if request.method == 'POST':

        nombre = request.form['nombre']

        username = request.form['usuario']

        password = request.form['password']

        rol = request.form['rol']

        # CONTRASEÑA NUEVA
        if password.strip():

            password_hash = generate_password_hash(
                password
            )

            cursor.execute('''
                UPDATE usuarios
                SET
                    nombre = %s,
                    usuario = %s,
                    password = %s,
                    rol = %s
                WHERE id = %s
            ''', (
                nombre,
                username,
                password_hash,
                rol,
                id
            ))

        else:

            cursor.execute('''
                UPDATE usuarios
                SET
                    nombre = %s,
                    usuario = %s,
                    rol = %s
                WHERE id = %s
            ''', (
                nombre,
                username,
                rol,
                id
            ))

        conexion.commit()

        conexion.close()

        flash(
            'Usuario actualizado correctamente',
            'success'
        )

        return redirect('/usuarios')

    conexion.close()

    return render_template(
        'editar_usuario.html',
        usuario=usuario
    )


# ─────────────────────────────────────────────
# ELIMINAR USUARIO
# ─────────────────────────────────────────────

@bp.route('/eliminar_usuario/<int:id>')

@rol_requerido([
    'admin'
])

def eliminar_usuario(id):

    conexion = conectar()

    cursor = conexion.cursor()

    cursor.execute('''
        DELETE FROM usuarios
        WHERE id = %s
    ''', (id,))

    conexion.commit()

    conexion.close()

    flash(
        'Usuario eliminado correctamente',
        'success'
    )

    return redirect('/usuarios')