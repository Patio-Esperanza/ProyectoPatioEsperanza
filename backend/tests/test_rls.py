import pytest
from sqlalchemy import select, text

from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, RolUsuario, TamanoContenedor, TipoContenedor
from app.models.ubicacion import Patio


@pytest.mark.anyio
async def test_operador_solo_ve_contenedores_de_su_patio(db_session):
    patio_1 = Patio(nombre="Patio Uno", codigo="RLS1")
    patio_2 = Patio(nombre="Patio Dos", codigo="RLS2")
    db_session.add_all([patio_1, patio_2])
    await db_session.flush()

    db_session.add_all(
        [
            Contenedor(
                numero_contenedor="CSQU3054383", tipo=TipoContenedor.LLENO, tamano=TamanoContenedor.CUARENTA,
                patio_id=patio_1.id, estado=EstadoContenedor.SOLICITUD_INGRESO, peso_kg=18000,
            ),
            Contenedor(
                numero_contenedor="TRHU1866154", tipo=TipoContenedor.LLENO, tamano=TamanoContenedor.CUARENTA,
                patio_id=patio_2.id, estado=EstadoContenedor.SOLICITUD_INGRESO, peso_kg=15000,
            ),
        ]
    )
    await db_session.commit()

    await db_session.execute(
        text("SELECT set_config('app.rol', :rol, false)"), {"rol": RolUsuario.OPERADOR.value}
    )
    await db_session.execute(
        text("SELECT set_config('app.patios_asignados', :patios, false)"), {"patios": str(patio_1.id)}
    )
    result = await db_session.execute(select(Contenedor))
    visibles = result.scalars().all()

    assert len(visibles) == 1
    assert visibles[0].patio_id == patio_1.id


@pytest.mark.anyio
async def test_admin_ve_todos_los_patios(db_session):
    patio_1 = Patio(nombre="Patio Tres", codigo="RLS3")
    patio_2 = Patio(nombre="Patio Cuatro", codigo="RLS4")
    db_session.add_all([patio_1, patio_2])
    await db_session.flush()

    db_session.add_all(
        [
            Contenedor(
                numero_contenedor="CSQU3054383", tipo=TipoContenedor.LLENO, tamano=TamanoContenedor.CUARENTA,
                patio_id=patio_1.id, estado=EstadoContenedor.SOLICITUD_INGRESO, peso_kg=18000,
            ),
            Contenedor(
                numero_contenedor="TRHU1866154", tipo=TipoContenedor.LLENO, tamano=TamanoContenedor.CUARENTA,
                patio_id=patio_2.id, estado=EstadoContenedor.SOLICITUD_INGRESO, peso_kg=15000,
            ),
        ]
    )
    await db_session.commit()

    await db_session.execute(
        text("SELECT set_config('app.rol', :rol, false)"), {"rol": RolUsuario.ADMIN.value}
    )
    await db_session.execute(
        text("SELECT set_config('app.patios_asignados', :patios, false)"), {"patios": ""}
    )
    result = await db_session.execute(select(Contenedor))
    visibles = result.scalars().all()

    assert len(visibles) >= 2
