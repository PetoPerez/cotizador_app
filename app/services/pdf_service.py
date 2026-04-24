from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import os

template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
env = Environment(loader=FileSystemLoader(template_dir))


def generar_pdf(cotizacion) -> bytes:
    template = env.get_template("cotizacion.html")
    html_str = template.render(cot=cotizacion)
    return HTML(string=html_str).write_pdf()