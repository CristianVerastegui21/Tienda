import os
import uuid

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


def subir_ticket(ruta_pdf):

    try:

        nombre_archivo = (
            f"{uuid.uuid4()}.pdf"
        )

        with open(
            ruta_pdf,
            "rb"
        ) as archivo:

            contenido = archivo.read()

        supabase.storage.from_(
            "tickets"
        ).upload(
            nombre_archivo,
            contenido,
            {
                "content-type":
                "application/pdf"
            }
        )

        url = supabase.storage.from_(
            "tickets"
        ).get_public_url(
            nombre_archivo
        )

        return url

    except Exception as e:

        print(
            "Error subiendo ticket:",
            e
        )

        return ""