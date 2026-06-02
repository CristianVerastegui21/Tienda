import re
import unicodedata

IMAGENES_CATEGORIA = {
    'abarrotes': 'https://images.unsplash.com/photo-1590794056226-79ef3a8147e1?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60',
    'bebidas': 'https://images.unsplash.com/photo-1534353473418-4cfa6c56fd38?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60',
    'lacteos': 'https://images.unsplash.com/photo-1628088062854-d1870b4553da?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60',
    'limpieza': 'https://images.unsplash.com/photo-1585421514284-efb74c2b69ba?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60',
    'snacks': 'https://images.unsplash.com/photo-1621939514649-280e2ee25f60?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60',
    'embutidos': 'https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60',
    'general': 'https://images.unsplash.com/photo-1604719312566-8912e9227c6a?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60',
}

ICONOS_CATEGORIA = {
    'abarrotes': 'fa-wheat-awn',
    'bebidas': 'fa-bottle-water',
    'lacteos': 'fa-droplet',
    'limpieza': 'fa-spray-can-sparkles',
    'snacks': 'fa-cookie-bite',
    'embutidos': 'fa-bacon',
    'general': 'fa-layer-group',
}


def slug_categoria(nombre):
    if not nombre:
        return 'general'
    texto = unicodedata.normalize('NFKD', str(nombre))
    texto = texto.encode('ascii', 'ignore').decode('ascii')
    texto = re.sub(r'[^a-z0-9]+', '-', texto.lower()).strip('-')
    return texto or 'general'


def imagen_categoria(slug, imagen_producto=None):
    if imagen_producto:
        return imagen_producto
    return IMAGENES_CATEGORIA.get(slug, IMAGENES_CATEGORIA['general'])


def imagen_producto(producto):
    imagen = producto.get('imagen') if isinstance(producto, dict) else None
    if imagen:
        return imagen
    slug = slug_categoria(
        producto.get('categoria') if isinstance(producto, dict) else None
    )
    return IMAGENES_CATEGORIA.get(slug, IMAGENES_CATEGORIA['general'])


def enriquecer_producto(producto):
    fila = dict(producto)
    fila['categoria_slug'] = slug_categoria(fila.get('categoria'))
    fila['imagen_url'] = imagen_producto(fila)
    return fila


def enriquecer_categoria(fila):
    cat = dict(fila)
    cat['slug'] = slug_categoria(cat.get('nombre'))
    cat['imagen_url'] = imagen_categoria(
        cat['slug'],
        cat.get('imagen_muestra'),
    )
    cat['icono'] = ICONOS_CATEGORIA.get(
        cat['slug'],
        ICONOS_CATEGORIA['general'],
    )
    return cat
