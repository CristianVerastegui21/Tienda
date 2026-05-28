import os
import sqlite3
import psycopg2

from psycopg2.extras import RealDictCursor

from werkzeug.security import (
    generate_password_hash
)


# =========================
# SQLITE LOCAL
# =========================

_BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

_DB_DIR = os.path.join(
    _BASE_DIR,
    'database'
)

_DB_PATH = os.path.join(
    _DB_DIR,
    'bodega.db'
)


# =========================
# CONEXION
# =========================

def conectar():

    DATABASE_URL = os.getenv(
        'DATABASE_URL'
    )

    # PRODUCCION RENDER
    if DATABASE_URL:

        conexion = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor
        )

        return conexion

    # LOCAL SQLITE
    os.makedirs(_DB_DIR, exist_ok=True)

    conexion = sqlite3.connect(
        _DB_PATH
    )

    conexion.row_factory = sqlite3.Row

    return conexion


# =========================
# CREAR TABLAS
# =========================

def crear_tablas():

    conexion = conectar()

    cursor = conexion.cursor()

    postgres = os.getenv(
        'DATABASE_URL'
    )


    # =====================
    # POSTGRESQL
    # =====================

    if postgres:

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id SERIAL PRIMARY KEY,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL,
                stock INTEGER NOT NULL,
                codigo_barra TEXT,
                imagen TEXT,
                reorden INTEGER DEFAULT 5,
                entradas INTEGER DEFAULT 0,
                salidas INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ventas (
                id SERIAL PRIMARY KEY,
                total REAL NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detalle_venta (
                id SERIAL PRIMARY KEY,
                id_venta INTEGER,
                id_producto INTEGER,
                cantidad INTEGER,
                subtotal REAL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nombre TEXT,
                usuario TEXT UNIQUE,
                password TEXT,
                rol TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                usuario TEXT,
                accion TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            SELECT *
            FROM usuarios
            WHERE usuario=%s
        ''', ('admin',))

        admin = cursor.fetchone()

        if not admin:

            cursor.execute('''
                INSERT INTO usuarios (
                    nombre,
                    usuario,
                    password,
                    rol
                )
                VALUES (%s,%s,%s,%s)
            ''', (
                'Administrador',
                'admin',
                generate_password_hash(
                    '1234'
                ),
                'admin'
            ))


    # =====================
    # SQLITE
    # =====================

    else:

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
            ADD COLUMN reorden
            INTEGER DEFAULT 5
            ''')
        except:
            pass

        try:
            cursor.execute('''
            ALTER TABLE productos
            ADD COLUMN entradas
            INTEGER DEFAULT 0
            ''')
        except:
            pass

        try:
            cursor.execute('''
            ALTER TABLE productos
            ADD COLUMN salidas
            INTEGER DEFAULT 0
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

        admin = cursor.execute(
            '''
            SELECT *
            FROM usuarios
            WHERE usuario = ?
            ''',
            ('admin',)
        ).fetchone()

        if not admin:

            cursor.execute('''
                INSERT INTO usuarios (
                    nombre,
                    usuario,
                    password,
                    rol
                )
                VALUES (?, ?, ?, ?)
            ''', (
                'Administrador',
                'admin',
                generate_password_hash(
                    '1234'
                ),
                'admin'
            ))

    conexion.commit()

    conexion.close()