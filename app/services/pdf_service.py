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
    # Seleccionar template según empresa
    empresa_code = getattr(cotizacion, 'empresa', 'clm') or 'clm'
    template_map = {
        'clm': 'cotizacion_clm.html',
        'supliese_gamesail': 'cotizacion_supliese_gamesail.html',
        'supliese': 'cotizacion_supliese.html',
    }
    template_name = template_map.get(empresa_code, 'cotizacion_clm.html')

    empresa = {
        "nombre":        settings.EMPRESA_NOMBRE,
        "marca":         settings.EMPRESA_MARCA,
        "nombre_corto":  settings.EMPRESA_NOMBRE_CORTO,
        "direccion":     settings.EMPRESA_DIRECCION,
        "telefono":      settings.EMPRESA_TELEFONO,
        "email":         settings.EMPRESA_EMAIL,
    }
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
    return HTML(string=html_str).write_pdf()
