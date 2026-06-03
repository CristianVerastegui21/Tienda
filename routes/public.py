from flask import Blueprint, render_template, request

from db import conectar, liberar
from utils.public_data import (
    enriquecer_categoria,
    enriquecer_producto,
    slug_categoria,
)

bp = Blueprint('public', __name__)

PRODUCTO_SELECT = '''
    SELECT
        p.id,
        p.nombre,
        p.precio,
        p.stock,
        p.imagen,
        c.nombre AS categoria
    FROM productos p
    LEFT JOIN categorias c ON c.id = p.categoria_id
'''


def _consultar(query, params=None):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute(query, params or ())
    filas = cursor.fetchall()
    cursor.close()
    liberar(conexion)
    return filas


def _consultar_varias(consultas):
    conexion = conectar()
    cursor = conexion.cursor()
    resultados = []
    for query, params in consultas:
        cursor.execute(query, params or ())
        resultados.append(cursor.fetchall())
    cursor.close()
    liberar(conexion)
    return resultados


def obtener_categorias_destacadas(limite=4):
    filas = _consultar('''
        SELECT
            c.id,
            c.nombre,
            COUNT(p.id) AS total,
            (
                SELECT p2.imagen
                FROM productos p2
                WHERE p2.categoria_id = c.id
                  AND p2.stock > 0
                  AND p2.imagen IS NOT NULL
                  AND p2.imagen <> ''
                ORDER BY p2.id DESC
                LIMIT 1
            ) AS imagen_muestra
        FROM categorias c
        INNER JOIN productos p
            ON p.categoria_id = c.id AND p.stock > 0
        GROUP BY c.id, c.nombre
        ORDER BY total DESC, c.nombre ASC
        LIMIT %s
    ''', (limite,))
    return [enriquecer_categoria(f) for f in filas]


def obtener_mas_vendidos(limite=8):
    filas = _consultar(f'''
        {PRODUCTO_SELECT}
        INNER JOIN detalle_venta dv ON dv.id_producto = p.id
        WHERE p.stock > 0
        GROUP BY p.id, p.nombre, p.precio, p.stock, p.imagen, c.nombre
        ORDER BY SUM(dv.cantidad) DESC
        LIMIT %s
    ''', (limite,))

    if filas:
        return [enriquecer_producto(f) for f in filas]

    filas = _consultar(f'''
        {PRODUCTO_SELECT}
        WHERE p.stock > 0
        ORDER BY p.salidas DESC NULLS LAST, p.id DESC
        LIMIT %s
    ''', (limite,))
    return [enriquecer_producto(f) for f in filas]


def obtener_novedades(limite=8):
    filas = _consultar(f'''
        {PRODUCTO_SELECT}
        WHERE p.stock > 0
        ORDER BY p.id DESC
        LIMIT %s
    ''', (limite,))
    return [enriquecer_producto(f) for f in filas]


def obtener_productos_catalogo(categoria_slug=None):
    params = []
    filtro = 'WHERE p.stock > 0'

    if categoria_slug and categoria_slug != 'all':
        filas_cat = _consultar('SELECT id, nombre FROM categorias')
        ids = [
            c['id'] for c in filas_cat
            if slug_categoria(c['nombre']) == categoria_slug
        ]
        if ids:
            filtro += ' AND p.categoria_id = %s'
            params.append(ids[0])
        else:
            return []

    filas = _consultar(
        f'{PRODUCTO_SELECT} {filtro} ORDER BY p.nombre ASC',
        tuple(params) or None,
    )
    return [enriquecer_producto(f) for f in filas]


def obtener_todas_categorias():
    filas = _consultar('''
        SELECT
            c.id,
            c.nombre,
            COUNT(p.id) AS total
        FROM categorias c
        LEFT JOIN productos p
            ON p.categoria_id = c.id AND p.stock > 0
        GROUP BY c.id, c.nombre
        HAVING COUNT(p.id) > 0
        ORDER BY c.nombre ASC
    ''')
    return [enriquecer_categoria(f) for f in filas]


def obtener_stats_tienda():
    filas = _consultar('''
        SELECT
            (SELECT COUNT(*) FROM productos WHERE stock > 0) AS productos_disponibles,
            (SELECT COUNT(*) FROM productos) AS productos_total,
            (SELECT COUNT(DISTINCT id_venta) FROM detalle_venta) AS ventas_con_productos
    ''')
    if not filas:
        return {
            'productos_disponibles': 0,
            'productos_total': 0,
            'ventas_con_productos': 0,
        }
    return dict(filas[0])


@bp.route('/')
def inicio():
    consultas = [
        (f'''
            SELECT
                c.id, c.nombre, COUNT(p.id) AS total,
                (
                    SELECT p2.imagen FROM productos p2
                    WHERE p2.categoria_id = c.id AND p2.stock > 0
                      AND p2.imagen IS NOT NULL AND p2.imagen <> ''
                    ORDER BY p2.id DESC LIMIT 1
                ) AS imagen_muestra
            FROM categorias c
            INNER JOIN productos p ON p.categoria_id = c.id AND p.stock > 0
            GROUP BY c.id, c.nombre
            ORDER BY total DESC, c.nombre ASC
            LIMIT 4
        ''', None),
        (f'''
            {PRODUCTO_SELECT}
            INNER JOIN detalle_venta dv ON dv.id_producto = p.id
            WHERE p.stock > 0
            GROUP BY p.id, p.nombre, p.precio, p.stock, p.imagen, c.nombre
            ORDER BY SUM(dv.cantidad) DESC
            LIMIT 8
        ''', None),
        (f'''
            {PRODUCTO_SELECT}
            WHERE p.stock > 0
            ORDER BY p.id DESC
            LIMIT 8
        ''', None),
        ('''
            SELECT
                (SELECT COUNT(*) FROM productos WHERE stock > 0) AS productos_disponibles,
                (SELECT COUNT(*) FROM productos) AS productos_total,
                (SELECT COUNT(DISTINCT id_venta) FROM detalle_venta) AS ventas_con_productos
        ''', None),
        ('''
            SELECT
                c.id, c.nombre, COUNT(p.id) AS total
            FROM categorias c
            LEFT JOIN productos p ON p.categoria_id = c.id AND p.stock > 0
            GROUP BY c.id, c.nombre
            HAVING COUNT(p.id) > 0
            ORDER BY c.nombre ASC
        ''', None),
    ]

    cats_raw, vendidos_raw, novedades_raw, stats_raw, todas_raw = _consultar_varias(consultas)

    categorias = [enriquecer_categoria(f) for f in cats_raw]
    todas_categorias = [enriquecer_categoria(f) for f in todas_raw]

    if vendidos_raw:
        mas_vendidos = [enriquecer_producto(f) for f in vendidos_raw]
    else:
        fallback = _consultar(f'''
            {PRODUCTO_SELECT}
            WHERE p.stock > 0
            ORDER BY p.salidas DESC NULLS LAST, p.id DESC
            LIMIT 8
        ''')
        mas_vendidos = [enriquecer_producto(f) for f in fallback]

    novedades = [enriquecer_producto(f) for f in novedades_raw]

    stats = dict(stats_raw[0]) if stats_raw else {
        'productos_disponibles': 0,
        'productos_total': 0,
        'ventas_con_productos': 0,
    }

    hero_productos = []
    for lista in (mas_vendidos, novedades):
        for producto in lista:
            if producto['id'] not in {p['id'] for p in hero_productos}:
                hero_productos.append(producto)
            if len(hero_productos) >= 2:
                break
        if len(hero_productos) >= 2:
            break

    return render_template(
        'public/inicio.html',
        categorias=categorias,
        todas_categorias=todas_categorias,
        mas_vendidos=mas_vendidos,
        novedades=novedades,
        hero_productos=hero_productos,
        stats=stats,
    )


@bp.route('/catalogo')
def catalogo():
    cat_slug = request.args.get('cat', 'all').strip().lower()
    buscar = request.args.get('q', '').strip()

    productos = obtener_productos_catalogo(
        None if cat_slug in ('', 'all') else cat_slug
    )
    categorias = obtener_todas_categorias()

    return render_template(
        'public/catalogo.html',
        productos=productos,
        categorias=categorias,
        cat_activa=cat_slug,
        buscar_inicial=buscar,
    )


@bp.route('/nosotros')
def nosotros():
    return render_template('public/nosotros.html')


@bp.route('/contacto')
def contacto():
    return render_template('public/contacto.html')

@bp.route('/privacidad')
def privacidad():
    return render_template('public/privacidad.html')

@bp.route('/terminos')
def terminos():
    return render_template('public/terminos.html')
