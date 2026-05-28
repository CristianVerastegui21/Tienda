from flask import Flask
import os
from db import crear_tablas
from routes import registrar_rutas

app = Flask(__name__)
#app.secret_key = 'bodega_verastegui'

app.secret_key = os.getenv(
    'SECRET_KEY',
    'BODEGA_VERASTEGUI_2026_SUPER_SECRET'
)

crear_tablas()
registrar_rutas(app)

if __name__ == '__main__':
   #app.run()

   
 app.run(debug=True)