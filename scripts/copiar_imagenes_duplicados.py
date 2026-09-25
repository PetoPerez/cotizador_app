"""Copia la imagen del producto original a sus duplicados activos sin imagen.

Duplicado = mismo modelo (normalizado) que otro producto activo con imagen.
El archivo se copia en Supabase a la carpeta del duplicado, para que borrar la
imagen de uno no deje sin imagen al otro.

Uso:  python scripts/copiar_imagenes_duplicados.py            # solo muestra
      python scripts/copiar_imagenes_duplicados.py --aplicar  # escribe
"""
import sys
import uuid
from dotenv import load_dotenv

load_dotenv(".env")

from sqlalchemy import text
from app.database import SessionLocal
from app import models
from app.services import storage_service as ss

aplicar = "--aplicar" in sys.argv
db = SessionLocal()
rows = db.execute(text("""
    select d.id, d.modelo, d.marca,
      (select pi.url from productos o join producto_imagenes pi on pi.producto_id = o.id
        where o.activo and o.imagen_url is not null
          and lower(trim(o.modelo)) = lower(trim(d.modelo))
        order by o.created_at, pi.orden limit 1) src
    from productos d
    where d.activo and d.imagen_url is null
      and not exists (select 1 from producto_imagenes x where x.producto_id = d.id)
    order by d.modelo""")).fetchall()

s3 = ss._client() if aplicar else None
try:
    for r in rows:
        if not r.src:
            continue
        src_key = ss.key_from_url(r.src)
        key = f"productos/{r.id}/{uuid.uuid4()}.{src_key.rsplit('.', 1)[-1]}"
        url = f"{ss._SUPABASE_URL}/storage/v1/object/public/{ss._BUCKET}/{key}"
        print(("copiando" if aplicar else "copiaría"), r.modelo, r.marca, "<-", src_key)
        if aplicar:
            s3.copy_object(Bucket=ss._BUCKET, Key=key,
                           CopySource={"Bucket": ss._BUCKET, "Key": src_key})
            db.add(models.ProductoImagen(producto_id=r.id, url=url, orden=0))
            db.get(models.Producto, r.id).imagen_url = url
    db.commit()
except Exception:
    db.rollback()
    raise
