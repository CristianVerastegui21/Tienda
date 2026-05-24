from flask import Flask

from database import crear_tablas
from routes import registrar_rutas

app = Flask(__name__)
app.secret_key = 'bodega_verastegui'

crear_tablas()
registrar_rutas(app)

if __name__ == '__main__':
  #  app.run()

     app.run(debug=True)
