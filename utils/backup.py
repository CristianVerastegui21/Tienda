import os
import shutil
from datetime import datetime

from db import _DB_PATH


def crear_backup():
    carpeta = 'backups'

    os.makedirs(carpeta, exist_ok=True)

    fecha = datetime.now().strftime('%Y%m%d_%H%M%S')

    origen = _DB_PATH

    destino = f'backups/bodega_{fecha}.db'

    shutil.copy(origen, destino)

    return destino
