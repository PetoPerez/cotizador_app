"""Convierte un número en pesos mexicanos a letras."""

_UNIDADES = ['', 'UNO', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE',
             'DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE', 'DIECISÉIS',
             'DIECISIETE', 'DIECIOCHO', 'DIECINUEVE', 'VEINTE']
_DECENAS_TENS = ['', '', 'VEINTI', 'TREINTA', 'CUARENTA', 'CINCUENTA',
                 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA']
_CENTENAS = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS',
             'QUINIENTOS', 'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS']


def _centena_a_letras(n: int) -> str:
    if n == 0:
        return ''
    if n == 100:
        return 'CIEN'
    c = n // 100
    resto = n % 100
    partes = []
    if c > 0:
        partes.append(_CENTENAS[c])
    if resto <= 20:
        if resto > 0:
            partes.append(_UNIDADES[resto])
    elif resto < 30:
        unidad = resto - 20
        partes.append(_DECENAS_TENS[2] + _UNIDADES[unidad].lower())
    else:
        d = resto // 10
        u = resto % 10
        if u == 0:
            partes.append(_DECENAS_TENS[d])
        else:
            partes.append(f'{_DECENAS_TENS[d]} Y {_UNIDADES[u]}')
    return ' '.join(partes)


def _miles_a_letras(n: int) -> str:
    """Convierte un entero de 0 a 999_999_999 a letras."""
    if n == 0:
        return 'CERO'
    partes = []
    millones = n // 1_000_000
    miles = (n % 1_000_000) // 1000
    cientos = n % 1000

    if millones > 0:
        if millones == 1:
            partes.append('UN MILLÓN')
        else:
            partes.append(f'{_centena_a_letras(millones)} MILLONES')

    if miles > 0:
        if miles == 1:
            partes.append('MIL')
        else:
            partes.append(f'{_centena_a_letras(miles)} MIL')

    if cientos > 0:
        partes.append(_centena_a_letras(cientos))

    return ' '.join(partes).upper()


def numero_a_letras(monto: float, moneda: str = 'MXN') -> str:
    """
    Convierte un número decimal a letras estilo cheque.
    Ej: 73080.00 → 'SETENTA Y TRES MIL OCHENTA PESOS 00/100 M.N.'
    """
    entero = int(monto)
    centavos = round((monto - entero) * 100)
    if centavos == 100:
        entero += 1
        centavos = 0
    letras = _miles_a_letras(entero)
    sufijo_moneda = 'M.N.' if moneda == 'MXN' else 'USD'
    palabra_moneda = 'PESOS' if moneda == 'MXN' else 'DÓLARES'
    return f'{letras} {palabra_moneda} {centavos:02d}/100 {sufijo_moneda}'
