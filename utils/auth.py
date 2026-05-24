from functools import wraps

from flask import redirect, session, request, jsonify


def rol_requerido(roles):
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            es_api = request.path.startswith('/api/')

            if 'usuario' not in session:
                if es_api:
                    return jsonify(ok=False, error='Sesion expirada'), 401
                return redirect('/login')

            if session.get('rol') not in roles:
                if es_api:
                    return jsonify(ok=False, error='Acceso denegado'), 403
                return "<h1>Acceso Denegado</h1>"

            return f(*args, **kwargs)

        return wrapper

    return decorador
