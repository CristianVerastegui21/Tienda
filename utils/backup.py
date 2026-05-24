import os
import shutil
from datetime import datetime


def crear_backup():
    carpeta = 'backups'

    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    fecha = datetime.now().strftime('%Y%m%d_%H%M%S')

    origen = 'database/bodega.db'

    destino = f'backups/bodega_{fecha}.db'

    shutil.copy(origen, destino)

    return destino
