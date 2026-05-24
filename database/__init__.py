import os
import sqlite3

from werkzeug.security import generate_password_hash


def conectar():
    if not os.path.exists("database"):
        os.makedirs("database")

    conexion = sqlite3.connect(
        "database/bodega.db"
    )

    conexion.row_factory = sqlite3.Row

    return conexion


def crear_tablas():
    conexion = conectar()

    cursor = conexion.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nombre TEXT NOT NULL,

            precio REAL NOT NULL,

            stock INTEGER NOT NULL,

            codigo_barra TEXT,

            imagen TEXT
        )
    ''')

    try:
        cursor.execute('''

            ALTER TABLE productos

            ADD COLUMN reorden INTEGER DEFAULT 5
            ADD COluMN entradas INTEGER DEFAULT 0
            ADD COLUMN salidas INTEGER DEFAULT 0


        ''')
    except:
        pass

    


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            total REAL NOT NULL,

            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detalle_venta (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            id_venta INTEGER,

            id_producto INTEGER,

            cantidad INTEGER,

            subtotal REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nombre TEXT,

            usuario TEXT UNIQUE,

            password TEXT,

            rol TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            usuario TEXT,

            accion TEXT,

            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    admin = cursor.execute('''
        SELECT * FROM usuarios
        WHERE usuario = ?
    ''', ('admin',)).fetchone()

    if not admin:
        cursor.execute('''
            INSERT INTO usuarios
            (nombre, usuario, password, rol)

            VALUES (?, ?, ?, ?)
        ''', (
            'Administrador',
            'admin',
            generate_password_hash('1234'),
            'admin'
        ))

    conexion.commit()
    conexion.close()
