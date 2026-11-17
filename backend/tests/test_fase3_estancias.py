import pytest
from datetime import datetime, timezone
from app.core.estancias import calcular_dias_estancia

def test_calculo_dias_estancia_mismo_dia():
    ingreso = datetime(2026, 11, 3, 7, 0, tzinfo=timezone.utc)
    salida = datetime(2026, 11, 3, 18, 0, tzinfo=timezone.utc)
    dias = calcular_dias_estancia(ingreso, salida, "America/Mexico_City")
    assert dias == 1

def test_calculo_dias_estancia_normal():
    # 3 nov 22:40 UTC to 10 nov 08:15 UTC
    ingreso = datetime(2026, 11, 3, 22, 40, tzinfo=timezone.utc)
    salida = datetime(2026, 11, 10, 8, 15, tzinfo=timezone.utc)
    dias = calcular_dias_estancia(ingreso, salida, "America/Mexico_City")
    assert dias == 8
