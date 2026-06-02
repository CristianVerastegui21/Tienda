from dotenv import load_dotenv

load_dotenv()

import os

from flask import Flask, g

from db import cerrar_request_db, conectar, init_db
from routes import registrar_rutas

app = Flask(__name__)

app.secret_key = os.getenv(
    'SECRET_KEY',
    'dev_secret'
)


@app.before_request
def _abrir_db_por_request():
    conectar()


@app.teardown_request
def _cerrar_db_por_request(exception=None):
    cerrar_request_db(exception)


init_db()
registrar_rutas(app)

if __name__ == '__main__':
    app.run(debug=True)
