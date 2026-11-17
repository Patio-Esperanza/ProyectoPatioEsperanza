import pytest
from sqlalchemy.exc import IntegrityError
from app.models.contenedor import Contenedor, EstadoContenedor, TipoContenedor, TamanoContenedor
from app.models.inspeccion import Inspeccion
from app.models.evidencia import Evidencia
from app.models.ubicacion import Patio

@pytest.mark.anyio
async def test_contenedor_active_unique_index(db_session):
    patio = Patio(nombre="Patio Central", codigo="PC1")
    db_session.add(patio)
    await db_session.flush()

    c1 = Contenedor(
        numero_contenedor="MSCU1234567",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.VEINTE,
        patio_id=patio.id,
        estado=EstadoContenedor.INGRESADO,
        peso_kg=20000,
    )
    db_session.add(c1)
    await db_session.commit()

    c2 = Contenedor(
        numero_contenedor="MSCU1234567",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.VEINTE,
        patio_id=patio.id,
        estado=EstadoContenedor.INGRESADO,
        peso_kg=20000,
    )
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

@pytest.mark.anyio
async def test_inspeccion_y_evidencia_models(db_session):
    patio = Patio(nombre="Patio Sur", codigo="PS1")
    db_session.add(patio)
    await db_session.flush()

    c = Contenedor(
        numero_contenedor="CSQU3054383",
        tipo=TipoContenedor.VACIO,
        tamano=TamanoContenedor.CUARENTA,
        patio_id=patio.id,
        estado=EstadoContenedor.INGRESADO,
        peso_kg=15000,
    )
    db_session.add(c)
    await db_session.flush()

    insp = Inspeccion(
        contenedor_id=c.id,
        placas="ABC-123",
        operador="Juan Perez",
        sellos="S123",
        danos={"puerta": "ninguno"},
        notas="Buen estado",
    )
    db_session.add(insp)
    await db_session.flush()

    ev = Evidencia(
        contenedor_id=c.id,
        inspeccion_id=insp.id,
        url="https://example.com/foto1.jpg",
        tipo="ingreso",
    )
    db_session.add(ev)
    await db_session.commit()

    assert insp.id is not None
    assert ev.id is not None
    assert ev.url == "https://example.com/foto1.jpg"
