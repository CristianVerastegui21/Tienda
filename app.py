from dotenv import load_dotenv
load_dotenv()

import os
from flask import Flask


from routes import registrar_rutas

app = Flask(__name__)
#app.secret_key = 'bodega_verastegui'


app.secret_key = os.getenv(
    'SECRET_KEY',
    'dev_secret'
)

registrar_rutas(app)

if __name__ == '__main__':
   app.run()

   
 #app.run(debug=True)