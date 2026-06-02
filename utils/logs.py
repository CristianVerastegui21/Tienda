from db import conectar, liberar


def registrar_log(usuario, accion):
    from flask import g, has_request_context

    propia = True
    if has_request_context() and getattr(g, '_db', None):
        conexion = g._db
        propia = False
    else:
        conexion = conectar()

    cursor = conexion.cursor()

    cursor.execute('''
        INSERT INTO logs
        (
            usuario,
            accion
        )
        VALUES (%s, %s)
    ''', (
        usuario,
        accion
    ))

    conexion.commit()
    cursor.close()

    if propia:
        liberar(conexion)
