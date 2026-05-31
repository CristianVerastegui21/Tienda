from datetime import date, datetime, timedelta


MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]


def _parse_date(valor, default):
  if not valor:
    return default
  try:
    return datetime.strptime(valor[:10], '%Y-%m-%d').date()
  except ValueError:
    return default


def rango_semana_iso(anio, semana):
  inicio = date.fromisocalendar(anio, semana, 1)
  fin = date.fromisocalendar(anio, semana, 7)
  return inicio, fin


def parse_filtros(args):
  hoy = date.today()
  tipo = (args.get('tipo') or 'mes').strip().lower()

  if tipo == 'dia':
    dia = _parse_date(args.get('fecha'), hoy)
    desde = hasta = dia
    etiqueta = dia.strftime('%d/%m/%Y')

  elif tipo == 'semana':
    anio = int(args.get('anio') or hoy.isocalendar()[0])
    semana = int(args.get('semana') or hoy.isocalendar()[1])
    semana = max(1, min(53, semana))
    desde, hasta = rango_semana_iso(anio, semana)
    etiqueta = f'Semana {semana} · {anio} ({desde.strftime("%d/%m")} - {hasta.strftime("%d/%m/%Y")})'

  elif tipo == 'anio':
    anio = int(args.get('anio') or hoy.year)
    desde = date(anio, 1, 1)
    hasta = date(anio, 12, 31)
    etiqueta = f'Ano {anio}'

  elif tipo == 'rango':
    desde = _parse_date(args.get('desde'), hoy.replace(day=1))
    hasta = _parse_date(args.get('hasta'), hoy)
    if desde > hasta:
      desde, hasta = hasta, desde
    etiqueta = f'{desde.strftime("%d/%m/%Y")} - {hasta.strftime("%d/%m/%Y")}'

  else:
    tipo = 'mes'
    mes_val = args.get('mes') or hoy.strftime('%Y-%m')
    try:
      anio_m, mes_m = map(int, mes_val.split('-'))
    except ValueError:
      anio_m, mes_m = hoy.year, hoy.month
    desde = date(anio_m, mes_m, 1)
    if mes_m == 12:
      hasta = date(anio_m, 12, 31)
    else:
      hasta = date(anio_m, mes_m + 1, 1) - timedelta(days=1)
    etiqueta = f'{MESES[mes_m - 1]} {anio_m}'

  agrupar = (args.get('agrupar') or 'diario').strip().lower()
  if agrupar not in ('diario', 'mensual', 'anual'):
    agrupar = 'diario'

  return {
    'tipo': tipo,
    'desde': desde.isoformat(),
    'hasta': hasta.isoformat(),
    'etiqueta': etiqueta,
    'agrupar': agrupar,
    'fecha': args.get('fecha') or desde.isoformat(),
    'mes': args.get('mes') or desde.strftime('%Y-%m'),
    'semana': args.get('semana') or str(hoy.isocalendar()[1]),
    'anio': args.get('anio') or str(hoy.year),
    'desde_input': args.get('desde') or desde.isoformat(),
    'hasta_input': args.get('hasta') or hasta.isoformat(),
  }


def sql_grupo_fecha(agrupar):
  if agrupar == 'mensual':
    return "TO_CHAR(fecha, 'YYYY-MM')", 'periodo'
  if agrupar == 'anual':
    return "TO_CHAR(fecha, 'YYYY')", 'periodo'
  return 'DATE(fecha)', 'dia'


def sql_filtro_fecha():
  return 'fecha::date BETWEEN %s AND %s'
