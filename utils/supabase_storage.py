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


def subir_imagen_supabase(file):

    try:

        extension = file.filename.rsplit(
            '.',
            1
        )[1].lower()

        nombre_archivo = (
            f'{uuid.uuid4()}.{extension}'
        )

        contenido = file.read()

        supabase.storage.from_(
            'productos'
        ).upload(
            nombre_archivo,
            contenido,
            {
                "content-type":
                file.content_type
            }
        )

        url = supabase.storage.from_(
            'productos'
        ).get_public_url(
            nombre_archivo
        )

        return url

    except Exception as e:

        print(
            'Error Supabase:',
            e
        )

        return ''