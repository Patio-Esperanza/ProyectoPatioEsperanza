import pytest

from app.models.cliente import Cliente
from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, TamanoContenedor, TipoCliente, TipoContenedor
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
from app.services.ubicacion_algoritmo import sugerir_ubicacion


async def _crear_estructura(db_session, *, carril_a_orden, carril_a_tipo, carril_b_orden, carril_b_tipo):
    patio = Patio(nombre="Patio Test", codigo=f"PT-{carril_a_orden}-{carril_b_orden}")
    db_session.add(patio)
    await db_session.flush()

    carril_a = Carril(patio_id=patio.id, codigo="A1", orden=carril_a_orden, tipo_teorico=carril_a_tipo)
    carril_b = Carril(patio_id=patio.id, codigo="A2", orden=carril_b_orden, tipo_teorico=carril_b_tipo)
    db_session.add_all([carril_a, carril_b])
    await db_session.flush()

    tramo_a = Tramo(carril_id=carril_a.id, codigo="T1", orden=0)
    tramo_b = Tramo(carril_id=carril_b.id, codigo="T1", orden=0)
    db_session.add_all([tramo_a, tramo_b])
    await db_session.flush()

    tira_a = Tira(tramo_id=tramo_a.id, codigo="S1", orden=0)
    tira_b = Tira(tramo_id=tramo_b.id, codigo="S1", orden=0)
    db_session.add_all([tira_a, tira_b])
    await db_session.flush()

    ubicacion_a = Ubicacion(tira_id=tira_a.id, nivel=1, codigo="A1-T1-S1-N1")
    ubicacion_b = Ubicacion(tira_id=tira_b.id, nivel=1, codigo="A2-T1-S1-N1")
    db_session.add_all([ubicacion_a, ubicacion_b])
    await db_session.flush()

    return patio, ubicacion_a, ubicacion_b


@pytest.mark.anyio
async def test_prefiere_slot_mas_cercano_aunque_sea_zona_teorica_distinta(db_session):
    patio, ubicacion_a1_lleno, ubicacion_a2_vacio = await _crear_estructura(
        db_session,
        carril_a_orden=0,
        carril_a_tipo=TipoContenedor.LLENO,
        carril_b_orden=3,
        carril_b_tipo=TipoContenedor.VACIO,
    )

    cliente = Cliente(razon_social="Importadora X", rfc="IMX010101AA1", tipo=TipoCliente.IMPORTADOR_EXPORTADOR)
    db_session.add(cliente)
    await db_session.flush()

    contenedor_lleno = Contenedor(
        numero_contenedor="CSQU3054383",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        cliente_id=cliente.id,
        patio_id=patio.id,
        estado=EstadoContenedor.INGRESADO,
        peso_kg=18000,
    )
    db_session.add(contenedor_lleno)
    await db_session.flush()

    resultado = await sugerir_ubicacion(
        db_session,
        patio_id=patio.id,
        contenedor=contenedor_lleno,
        punto_referencia_ubicacion_id=ubicacion_a2_vacio.id,
    )

    assert resultado.ubicacion_id == ubicacion_a2_vacio.id


@pytest.mark.anyio
async def test_no_sugiere_nivel_sin_base(db_session):
    patio, ubicacion_a1, _ = await _crear_estructura(
        db_session, carril_a_orden=0, carril_a_tipo=None, carril_b_orden=1, carril_b_tipo=None
    )
    nivel2 = Ubicacion(tira_id=ubicacion_a1.tira_id, nivel=2, codigo="A1-T1-S1-N2")
    db_session.add(nivel2)
    await db_session.flush()

    cliente = Cliente(razon_social="Importadora X", rfc="IMX020202AA1", tipo=TipoCliente.IMPORTADOR_EXPORTADOR)
    db_session.add(cliente)
    await db_session.flush()

    contenedor = Contenedor(
        numero_contenedor="CSQU3054383",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        cliente_id=cliente.id,
        patio_id=patio.id,
        estado=EstadoContenedor.INGRESADO,
        peso_kg=18000,
    )
    db_session.add(contenedor)
    await db_session.flush()

    resultado = await sugerir_ubicacion(
        db_session, patio_id=patio.id, contenedor=contenedor, punto_referencia_ubicacion_id=ubicacion_a1.id
    )
    assert resultado.ubicacion_id == ubicacion_a1.id
