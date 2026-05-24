from database import conectar


def registrar_log(usuario, accion):
    conexion = conectar()

    conexion.execute('''
        INSERT INTO logs
        (usuario, accion)

        VALUES (?, ?)
    ''', (
        usuario,
        accion
    ))

    conexion.commit()
    conexion.close()
