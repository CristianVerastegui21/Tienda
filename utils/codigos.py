import re


def normalizar_codigo(codigo):
    if codigo is None:
        return ''
    texto = str(codigo).strip()
    texto = re.sub(r'\s+', '', texto)
    return texto


def buscar_producto_por_codigo(conexion, codigo):
    codigo = normalizar_codigo(codigo)
    if not codigo:
        return None

    candidatos = [codigo]

    solo_digitos = re.sub(r'\D', '', codigo)
    if solo_digitos and solo_digitos != codigo:
        candidatos.append(solo_digitos)

    if solo_digitos.isdigit():
        sin_ceros = solo_digitos.lstrip('0') or '0'
        candidatos.extend([
            sin_ceros,
            solo_digitos.zfill(8),
            solo_digitos.zfill(12),
            solo_digitos.zfill(13),
            solo_digitos.zfill(14),
        ])

    vistos = set()
    for valor in candidatos:
        if not valor or valor in vistos:
            continue
        vistos.add(valor)

        producto = conexion.execute('''
            SELECT * FROM productos
            WHERE codigo_barra = ?
        ''', (valor,)).fetchone()

        if producto:
            return producto

    return None
