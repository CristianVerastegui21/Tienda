from functools import wraps

from flask import redirect, session


def rol_requerido(roles):
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'usuario' not in session:
                return redirect('/login')

            if session.get('rol') not in roles:
                return "<h1>Acceso Denegado</h1>"

            return f(*args, **kwargs)

        return wrapper

    return decorador
