import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.iso6346 import validar_iso6346
from app.models.cliente import Cliente
from app.models.contenedor import Contenedor, Movimiento
from app.models.enums import EstadoContenedor, TamanoContenedor, TipoCliente, TipoContenedor, TipoMovimiento
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion


def test_validar_iso6346_numero_valido():
    assert validar_iso6346("CSQU3054383") is True


def test_validar_iso6346_digito_verificador_incorrecto():
    assert validar_iso6346("CSQU3054380") is False


def test_validar_iso6346_formato_invalido():
    assert validar_iso6346("ABC123") is False


@pytest.mark.anyio
async def test_crea_contenedor_y_lo_ubica(db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN")
    db_session.add(patio)
    await db_session.flush()
    carril = Carril(patio_id=patio.id, codigo="A1", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()
    ubicacion = Ubicacion(tira_id=tira.id, nivel=1, codigo="A1-T1-S1-N1")
    db_session.add(ubicacion)
    await db_session.flush()

    cliente = Cliente(razon_social="Importadora X", rfc="IMX010101AA1", tipo=TipoCliente.IMPORTADOR_EXPORTADOR)
    db_session.add(cliente)
    await db_session.flush()

    contenedor = Contenedor(
        numero_contenedor="CSQU3054383",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        cliente_id=cliente.id,
        patio_id=patio.id,
        ubicacion_id=ubicacion.id,
        estado=EstadoContenedor.UBICADO,
        peso_kg=18000,
    )
    db_session.add(contenedor)
    await db_session.flush()

    db_session.add(
        Movimiento(
            contenedor_id=contenedor.id,
            patio_id=patio.id,
            tipo=TipoMovimiento.INGRESO,
            ubicacion_origen_id=None,
            ubicacion_destino_id=ubicacion.id,
            operador_id=None,
            override_manual=False,
        )
    )
    await db_session.flush()

    result = await db_session.execute(select(Contenedor).where(Contenedor.id == contenedor.id))
    assert result.scalar_one().estado == EstadoContenedor.UBICADO


@pytest.mark.anyio
async def test_no_permite_dos_contenedores_en_misma_ubicacion(db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN2")
    db_session.add(patio)
    await db_session.flush()
    carril = Carril(patio_id=patio.id, codigo="A1", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()
    ubicacion = Ubicacion(tira_id=tira.id, nivel=1, codigo="A1-T1-S1-N1")
    db_session.add(ubicacion)
    await db_session.flush()

    db_session.add(
        Contenedor(
            numero_contenedor="CSQU3054383",
            tipo=TipoContenedor.LLENO,
            tamano=TamanoContenedor.CUARENTA,
            patio_id=patio.id,
            ubicacion_id=ubicacion.id,
            estado=EstadoContenedor.UBICADO,
            peso_kg=18000,
        )
    )
    await db_session.flush()

    db_session.add(
        Contenedor(
            numero_contenedor="TRHU1866154",
            tipo=TipoContenedor.LLENO,
            tamano=TamanoContenedor.CUARENTA,
            patio_id=patio.id,
            ubicacion_id=ubicacion.id,
            estado=EstadoContenedor.UBICADO,
            peso_kg=15000,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
