import os

from flask import Flask

from db import crear_tablas
from routes import registrar_rutas

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'bodega_verastegui')

for carpeta in (
    'database',
    'static/tickets',
    'static/productos',
    'reportes',
    'backups',
):
    os.makedirs(carpeta, exist_ok=True)

crear_tablas()
registrar_rutas(app)

if __name__ == '__main__':
   app.run()

   
