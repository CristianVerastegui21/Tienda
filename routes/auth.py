from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    flash
)

from werkzeug.security import (
    check_password_hash
)

from db import conectar

from utils.logs import registrar_log


bp = Blueprint(
    'auth',
    __name__
)


@bp.route(
    '/login',
    methods=['GET', 'POST']
)
def login():

    if request.method == 'POST':

        usuario = request.form[
            'usuario'
        ]

        password = request.form[
            'password'
        ]

        conexion = conectar()

        cursor = conexion.cursor()

        cursor.execute('''
            SELECT *
            FROM usuarios
            WHERE usuario = %s
        ''', (usuario,))

        user = cursor.fetchone()

        conexion.close()

        if user and check_password_hash(
            user['password'],
            password
        ):

            session['usuario'] = (
                user['usuario']
            )

            session['rol'] = (
                user['rol']
            )

            registrar_log(
                usuario,
                'Inicio de sesion'
            )

            return redirect('/')

        flash(
            'Usuario o contraseña incorrectos',
            'danger'
        )

    return render_template(
        'login.html'
    )


@bp.route('/logout')
def logout():

    session.clear()

    return redirect('/login')