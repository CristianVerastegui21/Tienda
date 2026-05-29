from db import conectar


def registrar_log(usuario, accion):

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

    conexion.close()