from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import os
from app.config import settings

template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
env = Environment(loader=FileSystemLoader(template_dir))

_MESES = ['enero','febrero','marzo','abril','mayo','junio',
          'julio','agosto','septiembre','octubre','noviembre','diciembre']
_DIAS  = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo']

def _fecha_es(dt):
    return f"{_DIAS[dt.weekday()]}, {dt.day} de {_MESES[dt.month-1]} de {dt.year}"

def generar_pdf(cotizacion) -> bytes:
    # Si la cotización tiene empresa_id (nueva arquitectura), leer datos desde BD.
    # Si no (cotización histórica), caer al mapeo por código + config.
    empresa_rel = getattr(cotizacion, 'empresa_rel', None)
    empresa_code = getattr(cotizacion, 'empresa', 'clm') or 'clm'

    fallback_template_map = {
        'clm': 'cotizacion_clm.html',
        'supliese_gamesail': 'cotizacion_supliese_gamesail.html',
        'supliese': 'cotizacion_supliese.html',
        'servicios_lavanderia': 'cotizacion_servicios_lavanderia.html',
        'supliese_gomez': 'cotizacion_servicios_lavanderia.html',  # alias legacy
    }

    if empresa_rel is not None:
        template_name = empresa_rel.template_pdf or fallback_template_map.get(empresa_code, 'cotizacion_clm.html')
        empresa = {
            "nombre":        empresa_rel.nombre,
            "marca":         empresa_rel.acronimo,
            "nombre_corto":  empresa_rel.nombre_corto or empresa_rel.nombre,
            "direccion":     empresa_rel.direccion or settings.EMPRESA_DIRECCION,
            "telefono":      empresa_rel.telefono or settings.EMPRESA_TELEFONO,
            "email":         empresa_rel.email or settings.EMPRESA_EMAIL,
            "rfc":           empresa_rel.rfc,
            "logo_url":      empresa_rel.logo_url,
            "logo_decoracion_url": empresa_rel.logo_decoracion_url,
            "acronimo":      empresa_rel.acronimo,
        }
    else:
        template_name = fallback_template_map.get(empresa_code, 'cotizacion_clm.html')
        empresa = {
            "nombre":        settings.EMPRESA_NOMBRE,
            "marca":         settings.EMPRESA_MARCA,
            "nombre_corto":  settings.EMPRESA_NOMBRE_CORTO,
            "direccion":     settings.EMPRESA_DIRECCION,
            "telefono":      settings.EMPRESA_TELEFONO,
            "email":         settings.EMPRESA_EMAIL,
        }

    # Base path para imágenes
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    base_url = f"file://{os.path.abspath(static_dir)}/"
    moneda = getattr(cotizacion, 'moneda', 'MXN') or 'MXN'
    tc_raw = getattr(cotizacion, 'tipo_cambio', None)
    # Precios en BD están en USD, multiplicamos por TC para MXN
    tc = float(tc_raw) if tc_raw and moneda == 'MXN' else 1.0

    template = env.get_template(template_name)
    html_str = template.render(
        cot=cotizacion,
        empresa=empresa,
        fecha_es=_fecha_es,
        moneda=moneda,
        tc=tc,
        float=float,
    )
    return HTML(string=html_str, base_url=base_url).write_pdf()
