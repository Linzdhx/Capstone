from enum import Enum


class Semaforo(str, Enum):
    VERDE = "verde"
    AMARILLO = "amarillo"
    ROJO = "rojo"
    SIN_DATOS = "sin_datos"


# Umbrales según el Informe Final (porcentaje de stock visible)
UMBRAL_ROJO = 0.20      # 0 % – 20 %  -> rojo
UMBRAL_AMARILLO = 0.40  # 21 % – 40 % -> amarillo; sobre 40 % -> verde


def clasificar(occupancy_rate: float, total_spaces: int) -> Semaforo:
    """Devuelve el color del semáforo según el % de stock visible."""
    if total_spaces <= 0:
        return Semaforo.SIN_DATOS
    if occupancy_rate <= UMBRAL_ROJO:
        return Semaforo.ROJO
    if occupancy_rate <= UMBRAL_AMARILLO:
        return Semaforo.AMARILLO
    return Semaforo.VERDE