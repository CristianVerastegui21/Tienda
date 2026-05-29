import os
from datetime import datetime


def crear_backup():

    carpeta = 'backups'

    os.makedirs(
        carpeta,
        exist_ok=True
    )

    fecha = datetime.now().strftime(
        '%Y%m%d_%H%M%S'
    )

    archivo = (
        f'backups/supabase_backup_{fecha}.txt'
    )

    with open(
        archivo,
        'w',
        encoding='utf-8'
    ) as f:

        f.write(
            'Backup gestionado por Supabase PostgreSQL\n'
        )

        f.write(
            f'Fecha: {fecha}\n'
        )

    return archivo