import atexit
import os

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

_pool = None
_migraciones_ok = False

DATABASE_URL = os.getenv('DATABASE_URL')


def init_db():
    global _pool
    if _pool is not None:
        return
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL no esta configurada')
    minconn = int(os.getenv('DB_POOL_MIN', '1'))
    maxconn = int(os.getenv('DB_POOL_MAX', '12'))
    _pool = pool.ThreadedConnectionPool(
        minconn,
        maxconn,
        DATABASE_URL,
        cursor_factory=RealDictCursor,
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )
    atexit.register(cerrar_pool)
    _ejecutar_migraciones_pendientes()


def cerrar_pool():
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


def _ejecutar_migraciones_pendientes():
    global _migraciones_ok
    if _migraciones_ok:
        return
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        for columna, definicion in [
            ('entradas', 'INTEGER DEFAULT 0'),
            ('salidas', 'INTEGER DEFAULT 0'),
        ]:
            try:
                cursor.execute(f'''
                    ALTER TABLE productos
                    ADD COLUMN {columna} {definicion}
                ''')
                conexion.commit()
            except psycopg2.errors.DuplicateColumn:
                conexion.rollback()
            except Exception:
                conexion.rollback()
        cursor.close()
    finally:
        devolver_conexion(conexion)
    _migraciones_ok = True


def obtener_conexion():
    if _pool is None:
        init_db()
    conexion = _pool.getconn()
    conexion.autocommit = False
    return conexion


def devolver_conexion(conexion):
    if conexion is None or _pool is None:
        return
    try:
        if not conexion.closed:
            conexion.rollback()
    except Exception:
        pass
    try:
        _pool.putconn(conexion)
    except Exception:
        try:
            conexion.close()
        except Exception:
            pass


def conectar():
    from flask import g, has_request_context

    if has_request_context():
        if not getattr(g, '_db', None):
            g._db = obtener_conexion()
        return g._db

    return obtener_conexion()


def liberar(conexion):
    from flask import g, has_request_context

    if has_request_context() and getattr(g, '_db', None) is conexion:
        return

    devolver_conexion(conexion)


def cerrar_request_db(_exception=None):
    from flask import g

    conexion = g.pop('_db', None)
    if conexion is not None:
        devolver_conexion(conexion)
