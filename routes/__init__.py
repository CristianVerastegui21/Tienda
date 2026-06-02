from routes.public import bp as public_bp

from routes.auth import bp as auth_bp
from routes.dashboard import bp as dashboard_bp, registrar_alertas_globales
from routes.productos import bp as productos_bp
from routes.reportes import bp as reportes_bp
from routes.sistema import bp as sistema_bp
from routes.usuarios import bp as usuarios_bp
from routes.ventas import bp as ventas_bp



def registrar_rutas(app):

    app.register_blueprint(public_bp)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(productos_bp)
    app.register_blueprint(ventas_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(sistema_bp)
    registrar_alertas_globales(app)

   
