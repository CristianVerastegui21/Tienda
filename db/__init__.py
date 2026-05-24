import os
import sqlite3

from werkzeug.security import generate_password_hash

# Ruta absoluta: en Render/Gunicorn el directorio de trabajo puede variar
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_DIR = os.path.join(_BASE_DIR, 'database')
_DB_PATH = os.path.join(_DB_DIR, 'bodega.db')


def conectar():
    os.makedirs(_DB_DIR, exist_ok=True)

    conexion = sqlite3.connect(_DB_PATH)
    conexion.row_factory = sqlite3.Row

    return conexion


def _agregar_columna(cursor, tabla, columna, definicion):
    try:
        cursor.execute(
            f'ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}'
        )
    except sqlite3.OperationalError:
        pass


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

    _agregar_columna(cursor, 'productos', 'reorden', 'INTEGER DEFAULT 5')
    _agregar_columna(cursor, 'productos', 'entradas', 'INTEGER DEFAULT 0')
    _agregar_columna(cursor, 'productos', 'salidas', 'INTEGER DEFAULT 0')

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

    admin = cursor.execute(
        'SELECT * FROM usuarios WHERE usuario = ?',
        ('admin',)
    ).fetchone()

    if not admin:
        cursor.execute('''
            INSERT INTO usuarios (nombre, usuario, password, rol)
            VALUES (?, ?, ?, ?)
        ''', (
            'Administrador',
            'admin',
            generate_password_hash('1234'),
            'admin'
        ))

    conexion.commit()
    conexion.close()
