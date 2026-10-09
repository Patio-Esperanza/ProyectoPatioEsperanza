"""reinterpreta la hora de reportes_programados como hora local de Mexico

Antes de este cambio el scheduler corria sin zona horaria, asi que tomaba la del
contenedor, que es UTC: una fila con hora=8 enviaba el correo a las 08:00 UTC,
que en Mexico son las 02:00. Ahora el scheduler interpreta `hora` en la zona de
la aplicacion, asi que esa misma fila enviaria a las 08:00 de Mexico y el correo
llegaria seis horas tarde.

Esta migracion resta el desplazamiento para que los reportes ya programados
sigan llegando en el mismo instante real que hoy. Se usa el desplazamiento fijo
de -6 h (CST) porque es el que estuvo vigente mientras las filas se crearon:
Mexico elimino el horario de verano en 2022, asi que ninguna fila se guardo bajo
CDT.

Cuando la resta cruza la medianoche el dia tambien retrocede, o el reporte
semanal llegaria el dia equivocado. Por eso los dias se ajustan antes que la
hora: la condicion se evalua sobre la hora original.

El caso mensual con dia_mes = 1 no tiene equivalente en cron, porque el dia
anterior es el ultimo del mes previo y su numero cambia cada mes. Esas filas se
quedan en el dia 1, asi que se adelantan un dia respecto al instante que tenian.
Es la unica perdida de precision de la migracion y solo afecta reportes
mensuales programados entre las 00:00 y las 05:59 UTC.

Revision ID: 0013_hora_reportes_a_tz_mexico
Revises: 0012_reportes_programados
Create Date: 2026-10-09
"""
from alembic import op

revision = "0013_hora_reportes_a_tz_mexico"
down_revision = "0012_reportes_programados"
branch_labels = None
depends_on = None

# UTC-6: diferencia entre la zona en que se guardo la hora (UTC) y la zona en
# que ahora se lee (America/Mexico_City).
DESPLAZAMIENTO_HORAS = 6


def upgrade() -> None:
    # Semanal: la vispera en la convencion 0..6 de APScheduler (0 = lunes).
    op.execute(
        f"""
        UPDATE reportes_programados
        SET dia_semana = CASE
            WHEN dia_semana >= 1 THEN dia_semana - 1
            ELSE 6
        END
        WHERE frecuencia = 'semanal'
          AND dia_semana IS NOT NULL
          AND hora < {DESPLAZAMIENTO_HORAS}
        """
    )
    # Mensual: el dia 1 se queda donde esta, ver la nota del encabezado.
    op.execute(
        f"""
        UPDATE reportes_programados
        SET dia_mes = dia_mes - 1
        WHERE frecuencia = 'mensual'
          AND dia_mes IS NOT NULL
          AND dia_mes > 1
          AND hora < {DESPLAZAMIENTO_HORAS}
        """
    )
    op.execute(
        f"""
        UPDATE reportes_programados
        SET hora = CASE
            WHEN hora >= {DESPLAZAMIENTO_HORAS} THEN hora - {DESPLAZAMIENTO_HORAS}
            ELSE hora + 24 - {DESPLAZAMIENTO_HORAS}
        END
        """
    )


def downgrade() -> None:
    # La hora se restaura primero para que las condiciones de dia vuelvan a
    # evaluarse sobre la hora en UTC, igual que en upgrade().
    op.execute(
        f"""
        UPDATE reportes_programados
        SET hora = CASE
            WHEN hora >= (24 - {DESPLAZAMIENTO_HORAS}) THEN hora - (24 - {DESPLAZAMIENTO_HORAS})
            ELSE hora + {DESPLAZAMIENTO_HORAS}
        END
        """
    )
    op.execute(
        f"""
        UPDATE reportes_programados
        SET dia_semana = CASE
            WHEN dia_semana <= 5 THEN dia_semana + 1
            ELSE 0
        END
        WHERE frecuencia = 'semanal'
          AND dia_semana IS NOT NULL
          AND hora < {DESPLAZAMIENTO_HORAS}
        """
    )
    op.execute(
        f"""
        UPDATE reportes_programados
        SET dia_mes = dia_mes + 1
        WHERE frecuencia = 'mensual'
          AND dia_mes IS NOT NULL
          AND hora < {DESPLAZAMIENTO_HORAS}
        """
    )
