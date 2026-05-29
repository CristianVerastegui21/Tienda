import psycopg2

from psycopg2.extras import RealDictCursor


DATABASE_URL = "postgresql://postgres.hwrtxhmxqtucogxwoikd:C70946222vs21@aws-1-us-east-1.pooler.supabase.com:5432/postgres"


def conectar():

    conexion = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )

    return conexion