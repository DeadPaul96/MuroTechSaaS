"""Validación de horario de envío y reintentos automáticos para MH Costa Rica."""
import time
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

CR_TZ = timezone(timedelta(hours=-6))

# Feriados oficiales de Costa Rica (actualizar anualmente)
FERIADOS_CRC_2026 = {
    '2026-01-01', '2026-04-02', '2026-04-03', '2026-04-04',
    '2026-05-01', '2026-05-25', '2026-07-27', '2026-08-02',
    '2026-09-15', '2026-10-12', '2026-12-25',
}


def validar_horario_envio() -> tuple[bool, str]:
    """Valida si el horario actual permite envío a MH.

    Reglas API 4.4:
    - Lunes a Viernes: 8:00 AM – 8:00 PM
    - Sábados: 8:00 AM – 8:00 PM
    - Domingos: No permitido
    - Feriados: No permitido
    """
    ahora = datetime.now(CR_TZ)
    dia = ahora.weekday()  # 0=Lunes, 6=Domingo
    hora = ahora.hour
    fecha_str = ahora.strftime('%Y-%m-%d')

    if fecha_str in FERIADOS_CRC_2026:
        return False, 'Hoy es feriado oficial. Envío no permitido.'

    if dia == 6:
        return False, 'Domingos no se permite envío a Hacienda.'

    if not (8 <= hora < 20):
        return False, f'Horario de envío: 8:00 AM – 8:00 PM.Hora actual: {ahora.strftime("%I:%M %p")}.'

    return True, 'Horario válido para envío.'


def segundos_hasta_proximo_horario() -> int:
    """Calcula segundos hasta el próximo horario hábil de MH."""
    ahora = datetime.now(CR_TZ)
    dia = ahora.weekday()

    if dia == 6:
        proximo = (ahora + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    elif hora >= 20:
        proximo_dia = ahora + timedelta(days=1)
        if proximo_dia.weekday() == 6:
            proximo_dia += timedelta(days=1)
        proximo = proximo_dia.replace(hour=8, minute=0, second=0, microsecond=0)
    else:
        proximo = ahora.replace(hour=8, minute=0, second=0, microsecond=0)
        if ahora < proximo:
            return int((proximo - ahora).total_seconds())
        proximo = ahora.replace(hour=20, minute=0, second=0, microsecond=0)
        if ahora < proximo:
            return 0

    return int((proximo - ahora).total_seconds())


def enviar_con_reintentos(
    fn_envio,
    *,
    max_reintentos: int = 3,
    delay_base: float = 2.0,
    delay_max: float = 60.0,
    validar_horario: bool = True,
) -> dict:
    """Ejecuta envío a MH con reintentos y exponential backoff.

    Args:
        fn_envio: Callable que ejecuta el envío. Debe retornar dict o lanzar HaciendaError.
        max_reintentos: Número máximo de reintentos.
        delay_base: Segundos base para exponential backoff.
        delay_max: Segundos máximos de espera entre reintentos.
        validar_horario: Si True, verifica horario antes de enviar.

    Returns:
        dict: Resultado del envío exitoso.

    Raises:
        HaciendaError: Si todos los reintentos fallan.
    """
    from fiscal.hacienda_client import HaciendaError

    if validar_horario:
        permitido, motivo = validar_horario_envio()
        if not permitido:
            raise HaciendaError(
                f'Envío fuera de horario MH: {motivo}',
                status_code=429,
                payload={'reason': 'outside_schedule', 'detail': motivo},
            )

    ultimo_error = None

    for intento in range(1, max_reintentos + 1):
        try:
            resultado = fn_envio()
            if intento > 1:
                logger.info('Envío MH exitoso en intento %d', intento)
            return resultado
        except HaciendaError as err:
            ultimo_error = err
            status = getattr(err, 'status_code', 0)

            # No reintentar errores de cliente (4xx) excepto 429 y 408
            if 400 <= status < 500 and status not in (408, 429):
                logger.warning('Error MH no reintentable (%d): %s', status, err)
                raise

            if intento < max_reintentos:
                delay = min(delay_base * (2 ** (intento - 1)), delay_max)
                logger.warning(
                    'Intento %d/%d fallido (status=%d). Reintentando en %.1fs: %s',
                    intento, max_reintentos, status, delay, err,
                )
                time.sleep(delay)
            else:
                logger.error(
                    'Todos los reintentos agotados (%d). Último error: %s',
                    max_reintentos, err,
                )

    raise ultimo_error
