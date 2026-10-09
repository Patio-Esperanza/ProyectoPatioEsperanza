import datetime
import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.models.contenedor import Contenedor, Movimiento
from app.models.enums import (
    EstadoContenedor,
    RolUsuario,
    TamanoContenedor,
    TipoCliente,
    TipoContenedor,
    TipoMovimiento,
)
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
from app.models.usuario import Usuario
from app.schemas.reportes import FiltrosReporte, ReporteTipo
from app.services.reportes_datos import (
    COLUMNAS_POR_REPORTE,
    _formatear_fecha,
    obtener_datos_reporte,
    obtener_preview_reporte,
)


@pytest_asyncio.fixture
async def datos_prueba_reportes(db_session: AsyncSession):
    # Crear Patio
    patio = Patio(
        id=uuid.uuid4(),
        nombre="Patio Central",
        codigo="PAT01",
        timezone="America/Mexico_City",
        activo=True,
    )
    db_session.add(patio)
    await db_session.flush()

    # Crear Cliente
    cliente = Cliente(
        id=uuid.uuid4(),
        razon_social="Logística Internacional SA",
        rfc="LIN901201ABC",
        tipo=TipoCliente.IMPORTADOR_EXPORTADOR,
        activo=True,
    )
    db_session.add(cliente)
    await db_session.flush()

    # Crear Usuario
    usuario = Usuario(
        id=uuid.uuid4(),
        email="operador@patio.mx",
        nombre="Juan Pérez",
        tipo=RolUsuario.OPERADOR,
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()

    # Crear jerarquía de ubicación
    carril = Carril(id=uuid.uuid4(), patio_id=patio.id, codigo="C01", orden=1)
    db_session.add(carril)
    await db_session.flush()

    tramo = Tramo(id=uuid.uuid4(), carril_id=carril.id, codigo="T01", orden=1)
    db_session.add(tramo)
    await db_session.flush()

    tira = Tira(id=uuid.uuid4(), tramo_id=tramo.id, codigo="R01", orden=1)
    db_session.add(tira)
    await db_session.flush()

    ubicacion = Ubicacion(
        id=uuid.uuid4(),
        tira_id=tira.id,
        nivel=2,
        codigo="C01-T01-R01-N2",
        capacidad_peso_kg=30000,
        activo=True,
    )
    db_session.add(ubicacion)
    await db_session.flush()

    # Crear Contenedor activo con ubicación
    contenedor1 = Contenedor(
        id=uuid.uuid4(),
        numero_contenedor="MSKU1234567",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        cliente_id=cliente.id,
        patio_id=patio.id,
        ubicacion_id=ubicacion.id,
        estado=EstadoContenedor.UBICADO,
        peso_kg=22000,
        created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5),
    )
    db_session.add(contenedor1)

    # Crear Contenedor vacío sin ubicación (en ingreso)
    contenedor2 = Contenedor(
        id=uuid.uuid4(),
        numero_contenedor="TGHU9876543",
        tipo=TipoContenedor.VACIO,
        tamano=TamanoContenedor.VEINTE,
        cliente_id=cliente.id,
        patio_id=patio.id,
        ubicacion_id=None,
        estado=EstadoContenedor.INGRESADO,
        peso_kg=3800,
        created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2),
    )
    db_session.add(contenedor2)
    await db_session.flush()

    # Crear Movimientos
    mov_ingreso1 = Movimiento(
        id=uuid.uuid4(),
        contenedor_id=contenedor1.id,
        patio_id=patio.id,
        tipo=TipoMovimiento.INGRESO,
        operador_id=usuario.id,
        ts=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5),
    )
    db_session.add(mov_ingreso1)

    mov_ingreso2 = Movimiento(
        id=uuid.uuid4(),
        contenedor_id=contenedor2.id,
        patio_id=patio.id,
        tipo=TipoMovimiento.INGRESO,
        operador_id=usuario.id,
        ts=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2),
    )
    db_session.add(mov_ingreso2)

    mov_salida = Movimiento(
        id=uuid.uuid4(),
        contenedor_id=contenedor1.id,
        patio_id=patio.id,
        tipo=TipoMovimiento.SALIDA,
        operador_id=usuario.id,
        ts=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1),
    )
    db_session.add(mov_salida)

    mov_servicio = Movimiento(
        id=uuid.uuid4(),
        contenedor_id=contenedor1.id,
        patio_id=patio.id,
        tipo=TipoMovimiento.SERVICIO,
        operador_id=usuario.id,
        motivo_override="LAVADO Y SANITIZADO",
        ts=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3),
    )
    db_session.add(mov_servicio)

    await db_session.flush()

    return {
        "patio": patio,
        "cliente": cliente,
        "usuario": usuario,
        "contenedor1": contenedor1,
        "contenedor2": contenedor2,
        "ubicacion": ubicacion,
    }


@pytest.mark.asyncio
async def test_reporte_contenedores_en_patio(db_session: AsyncSession, datos_prueba_reportes):
    filtros = FiltrosReporte(page=1, page_size=25)
    filas, total, kpis = await obtener_datos_reporte(
        db=db_session,
        tipo=ReporteTipo.CONTAINERS_IN_YARD,
        filtros=filtros,
        patios_ids=[datos_prueba_reportes["patio"].id],
    )
    assert total >= 2
    assert len(filas) >= 2
    assert any(f["contenedor"] == "MSKU1234567" for f in filas)
    assert any(f["contenedor"] == "TGHU9876543" for f in filas)
    assert any(k.label == "Total Contenedores" for k in kpis)


@pytest.mark.asyncio
async def test_la_estadia_se_mide_desde_el_movimiento_de_ingreso(
    db_session: AsyncSession, datos_prueba_reportes
):
    """La estadía cuenta días en el patio, no días desde que se registró el contenedor.

    Un contenedor puede registrarse semanas antes de llegar físicamente, así que
    `created_at` sobreestima la estadía. La fecha real de entrada es el `ts` del
    primer movimiento de tipo `ingreso`.
    """
    ahora = datetime.datetime.now(datetime.timezone.utc)
    patio = datos_prueba_reportes["patio"]

    contenedor = Contenedor(
        id=uuid.uuid4(),
        numero_contenedor="HLXU1112223",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        cliente_id=datos_prueba_reportes["cliente"].id,
        patio_id=patio.id,
        ubicacion_id=None,
        estado=EstadoContenedor.INGRESADO,
        peso_kg=20000,
        # Registrado hace 30 días, pero entró hace 3.
        created_at=ahora - datetime.timedelta(days=30),
    )
    db_session.add(contenedor)
    await db_session.flush()

    db_session.add(
        Movimiento(
            id=uuid.uuid4(),
            contenedor_id=contenedor.id,
            patio_id=patio.id,
            tipo=TipoMovimiento.INGRESO,
            operador_id=datos_prueba_reportes["usuario"].id,
            ts=ahora - datetime.timedelta(days=3),
        )
    )
    await db_session.flush()

    filtros = FiltrosReporte(page=1, page_size=25)
    filas, _, _ = await obtener_datos_reporte(
        db=db_session,
        tipo=ReporteTipo.CONTAINERS_IN_YARD,
        filtros=filtros,
        patios_ids=[patio.id],
    )

    fila = next(f for f in filas if f["contenedor"] == "HLXU1112223")
    assert fila["estadia"] == 3
    assert fila["fecha_entrada"] == _formatear_fecha(ahora - datetime.timedelta(days=3))


@pytest.mark.asyncio
async def test_sin_movimiento_de_ingreso_la_estadia_es_cero(
    db_session: AsyncSession, datos_prueba_reportes
):
    """Un contenedor sin movimiento de ingreso no ha entrado al patio.

    Contar días desde `created_at` inventaría una estadía que nunca ocurrió.
    """
    ahora = datetime.datetime.now(datetime.timezone.utc)
    patio = datos_prueba_reportes["patio"]

    contenedor = Contenedor(
        id=uuid.uuid4(),
        numero_contenedor="HLXU4445556",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        cliente_id=datos_prueba_reportes["cliente"].id,
        patio_id=patio.id,
        ubicacion_id=None,
        estado=EstadoContenedor.INGRESADO,
        peso_kg=20000,
        created_at=ahora - datetime.timedelta(days=30),
    )
    db_session.add(contenedor)
    await db_session.flush()

    filtros = FiltrosReporte(page=1, page_size=25)
    filas, _, _ = await obtener_datos_reporte(
        db=db_session,
        tipo=ReporteTipo.CONTAINERS_IN_YARD,
        filtros=filtros,
        patios_ids=[patio.id],
    )

    fila = next(f for f in filas if f["contenedor"] == "HLXU4445556")
    assert fila["estadia"] == 0
    assert fila["fecha_entrada"] == ""


@pytest.mark.asyncio
async def test_reporte_movimientos_entrada(db_session: AsyncSession, datos_prueba_reportes):
    filtros = FiltrosReporte(page=1, page_size=25)
    filas, total, kpis = await obtener_datos_reporte(
        db=db_session,
        tipo=ReporteTipo.ENTRY_MOVEMENTS,
        filtros=filtros,
        patios_ids=[datos_prueba_reportes["patio"].id],
    )
    assert total >= 2
    assert len(filas) >= 2
    assert all("numero_viaje" in f for f in filas)
    assert any(f["contenedor"] == "MSKU1234567" for f in filas)


@pytest.mark.asyncio
async def test_reporte_movimientos_salida(db_session: AsyncSession, datos_prueba_reportes):
    filtros = FiltrosReporte(page=1, page_size=25)
    filas, total, kpis = await obtener_datos_reporte(
        db=db_session,
        tipo=ReporteTipo.DEPARTURE_MOVEMENTS,
        filtros=filtros,
        patios_ids=[datos_prueba_reportes["patio"].id],
    )
    assert total >= 1
    assert len(filas) >= 1
    assert filas[0]["contenedor"] == "MSKU1234567"
    assert filas[0]["estado"] == "Completado"


@pytest.mark.asyncio
async def test_la_salida_reporta_el_ingreso_previo_no_el_registro(
    db_session: AsyncSession, datos_prueba_reportes
):
    """La fecha de entrada de una salida es el ingreso que la precede.

    Si el contenedor entró, salió y volvió a entrar, cada salida debe mostrar
    el ingreso con el que inició esa estadía, no la fecha de registro ni un
    ingreso posterior.
    """
    ahora = datetime.datetime.now(datetime.timezone.utc)
    patio = datos_prueba_reportes["patio"]
    usuario = datos_prueba_reportes["usuario"]

    contenedor = Contenedor(
        id=uuid.uuid4(),
        numero_contenedor="HLXU7778889",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        cliente_id=datos_prueba_reportes["cliente"].id,
        patio_id=patio.id,
        ubicacion_id=None,
        estado=EstadoContenedor.DESPACHADO,
        peso_kg=20000,
        created_at=ahora - datetime.timedelta(days=30),
    )
    db_session.add(contenedor)
    await db_session.flush()

    entrada = ahora - datetime.timedelta(days=9)
    salida = ahora - datetime.timedelta(days=7)
    # Reingreso posterior a la salida: no debe aparecer en esa fila.
    reingreso = ahora - datetime.timedelta(days=2)

    for tipo, ts in (
        (TipoMovimiento.INGRESO, entrada),
        (TipoMovimiento.SALIDA, salida),
        (TipoMovimiento.INGRESO, reingreso),
    ):
        db_session.add(
            Movimiento(
                id=uuid.uuid4(),
                contenedor_id=contenedor.id,
                patio_id=patio.id,
                tipo=tipo,
                operador_id=usuario.id,
                ts=ts,
            )
        )
    await db_session.flush()

    filtros = FiltrosReporte(page=1, page_size=25)
    filas, _, _ = await obtener_datos_reporte(
        db=db_session,
        tipo=ReporteTipo.DEPARTURE_MOVEMENTS,
        filtros=filtros,
        patios_ids=[patio.id],
    )

    fila = next(f for f in filas if f["contenedor"] == "HLXU7778889")
    assert fila["fecha_entrada"] == _formatear_fecha(entrada)
    assert fila["fecha_salida"] == _formatear_fecha(salida)


@pytest.mark.asyncio
async def test_reporte_posiciones(db_session: AsyncSession, datos_prueba_reportes):
    filtros = FiltrosReporte(page=1, page_size=25)
    filas, total, kpis = await obtener_datos_reporte(
        db=db_session,
        tipo=ReporteTipo.POSITIONS,
        filtros=filtros,
        patios_ids=[datos_prueba_reportes["patio"].id],
    )
    assert total >= 1
    assert len(filas) >= 1
    pos_row = next(f for f in filas if f["contenedor"] == "MSKU1234567")
    assert pos_row["posicion"] != ""
    assert pos_row["altura"] == "2"


@pytest.mark.asyncio
async def test_posiciones_reporta_los_codigos_del_layout(
    db_session: AsyncSession, datos_prueba_reportes
):
    """El reporte debe decir la posición igual que el mapa del patio.

    `orden` es el índice interno del layout y empieza en cero, así que no se
    puede mostrar al operador: la ubicación que el mapa rotula `C01-T01-R01-N2`
    saldría como `0-0-0`. El código de cada nivel ya está en `Ubicacion.codigo`.
    """
    filtros = FiltrosReporte(page=1, page_size=25)
    filas, _, _ = await obtener_datos_reporte(
        db=db_session,
        tipo=ReporteTipo.POSITIONS,
        filtros=filtros,
        patios_ids=[datos_prueba_reportes["patio"].id],
    )

    fila = next(f for f in filas if f["contenedor"] == "MSKU1234567")
    assert fila["posicion"] == "C01-T01-R01-N2"
    assert fila["carril"] == "C01"
    assert fila["tramo"] == "T01"
    assert fila["tira"] == "R01"
    assert fila["altura"] == "2"


@pytest.mark.asyncio
async def test_posiciones_usa_la_fecha_del_movimiento_de_ingreso(
    db_session: AsyncSession, datos_prueba_reportes
):
    """La columna de fecha es cuándo entró al patio, no cuándo se registró."""
    ahora = datetime.datetime.now(datetime.timezone.utc)
    patio = datos_prueba_reportes["patio"]
    entrada = ahora - datetime.timedelta(days=4)

    ubicacion = Ubicacion(
        id=uuid.uuid4(),
        tira_id=datos_prueba_reportes["ubicacion"].tira_id,
        nivel=1,
        codigo="C01-T01-R01-N1",
        capacidad_peso_kg=30000,
        activo=True,
    )
    db_session.add(ubicacion)
    await db_session.flush()

    contenedor = Contenedor(
        id=uuid.uuid4(),
        numero_contenedor="HLXU2223334",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        cliente_id=datos_prueba_reportes["cliente"].id,
        patio_id=patio.id,
        ubicacion_id=ubicacion.id,
        estado=EstadoContenedor.UBICADO,
        peso_kg=20000,
        # Registrado hace 30 días, pero entró hace 4.
        created_at=ahora - datetime.timedelta(days=30),
    )
    db_session.add(contenedor)
    await db_session.flush()

    db_session.add(
        Movimiento(
            id=uuid.uuid4(),
            contenedor_id=contenedor.id,
            patio_id=patio.id,
            tipo=TipoMovimiento.INGRESO,
            operador_id=datos_prueba_reportes["usuario"].id,
            ts=entrada,
        )
    )
    await db_session.flush()

    filtros = FiltrosReporte(page=1, page_size=25)
    filas, _, _ = await obtener_datos_reporte(
        db=db_session,
        tipo=ReporteTipo.POSITIONS,
        filtros=filtros,
        patios_ids=[patio.id],
    )

    fila = next(f for f in filas if f["contenedor"] == "HLXU2223334")
    assert fila["fecha"] == _formatear_fecha(entrada)
    assert fila["posicion"] == "C01-T01-R01-N1"


@pytest.mark.asyncio
async def test_reporte_servicios_especiales(db_session: AsyncSession, datos_prueba_reportes):
    filtros = FiltrosReporte(page=1, page_size=25)
    filas, total, kpis = await obtener_datos_reporte(
        db=db_session,
        tipo=ReporteTipo.SPECIAL_SERVICES,
        filtros=filtros,
        patios_ids=[datos_prueba_reportes["patio"].id],
    )
    assert total >= 1
    assert len(filas) >= 1
    assert filas[0]["servicio"] == "LAVADO Y SANITIZADO"
    assert filas[0]["cantidad"] == 1


@pytest.mark.asyncio
async def test_obtener_preview_reporte_completo(db_session: AsyncSession, datos_prueba_reportes):
    filtros = FiltrosReporte(page=1, page_size=10)
    preview = await obtener_preview_reporte(
        db=db_session,
        tipo=ReporteTipo.CONTAINERS_IN_YARD,
        filtros=filtros,
        patios_ids=[datos_prueba_reportes["patio"].id],
    )
    assert preview.tipo == ReporteTipo.CONTAINERS_IN_YARD
    assert preview.titulo == "Contenedores en Patio"
    assert len(preview.columnas) == len(COLUMNAS_POR_REPORTE[ReporteTipo.CONTAINERS_IN_YARD])
    assert preview.total_registros >= 2
    assert len(preview.filas) >= 2
