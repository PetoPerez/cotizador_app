from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, default_url_fetcher
import os
from app.config import settings
from app.utils.numero_letras import numero_a_letras
from app.services.exchange_rate_service import get_usd_mxn

# Timeout (segundos) para descargar imágenes remotas al generar el PDF.
# Evita que una imagen lenta/colgada bloquee al worker indefinidamente.
_IMG_TIMEOUT = 5

template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
env = Environment(loader=FileSystemLoader(template_dir))

_MESES = ['enero','febrero','marzo','abril','mayo','junio',
          'julio','agosto','septiembre','octubre','noviembre','diciembre']
_DIAS  = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo']

def _fecha_es(dt):
    return f"{_DIAS[dt.weekday()]}, {dt.day} de {_MESES[dt.month-1]} de {dt.year}"

def generar_pdf(cotizacion):
    """Genera el PDF de la cotización.

    Devuelve una tupla (pdf_bytes, imagenes_fallidas) donde imagenes_fallidas
    es el número de imágenes que no se pudieron descargar (por timeout o error).
    El PDF se genera de todas formas, omitiendo esas imágenes.
    """
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
    # Factor por el que se multiplica el precio guardado en BD para mostrarlo en la moneda solicitada.
    #   Servicios de Lavandería: precios guardados en MXN.
    #     - cotización MXN → tc = 1
    #     - cotización USD → tc = 1/TC (dividir para convertir MXN→USD)
    #   Otras empresas: precios guardados en USD.
    #     - cotización MXN → tc = TC (multiplicar para convertir USD→MXN)
    #     - cotización USD → tc = 1
    # Respaldo: si se necesita convertir pero la cotización no guardó tipo de
    # cambio, se usa el tipo de cambio en vivo para no mostrar montos en una
    # moneda con la etiqueta de otra.
    def _tc_efectivo():
        if tc_raw and float(tc_raw) > 0:
            return float(tc_raw)
        return get_usd_mxn() or 1.0

    if empresa_code == 'servicios_lavanderia':
        # Precios guardados en MXN. Solo se convierte si la cotización es USD.
        tc = (1.0 / _tc_efectivo()) if moneda == 'USD' else 1.0
    else:
        # Precios guardados en USD. Solo se convierte si la cotización es MXN.
        tc = _tc_efectivo() if moneda == 'MXN' else 1.0

    template = env.get_template(template_name)
    html_str = template.render(
        cot=cotizacion,
        empresa=empresa,
        fecha_es=_fecha_es,
        moneda=moneda,
        tc=tc,
        float=float,
        numero_a_letras=numero_a_letras,
    )

    # Fetcher con timeout: si una imagen no responde a tiempo, se registra el
    # fallo y se omite; el PDF se genera igual sin bloquear al worker.
    fallidas = []

    def _url_fetcher(url):
        try:
            return default_url_fetcher(url, timeout=_IMG_TIMEOUT)
        except Exception:
            fallidas.append(url)
            raise  # WeasyPrint omite la imagen y continúa

    pdf_bytes = HTML(string=html_str, base_url=base_url,
                     url_fetcher=_url_fetcher).write_pdf()
    return pdf_bytes, len(fallidas)
