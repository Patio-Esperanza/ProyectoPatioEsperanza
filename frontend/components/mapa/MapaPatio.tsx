"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { MapaPatio as MapaPatioData } from "@/lib/api";
import { CeldaTira } from "./CeldaTira";
import styles from "./MapaPatio.module.css";

interface MapaPatioProps {
  mapa: MapaPatioData;
  tiraSeleccionadaId: string | null;
  tiraSugeridaId: string | null;
  onSeleccionarTira: (tiraId: string) => void;
}

export function MapaPatio({
  mapa,
  tiraSeleccionadaId,
  tiraSugeridaId,
  onSeleccionarTira,
}: MapaPatioProps) {
  const filtroId = useId();
  const [carrilFiltrado, setCarrilFiltrado] = useState("");
  const [indiceActivo, setIndiceActivo] = useState(0);
  const contenedorRef = useRef<HTMLDivElement>(null);

  const carriles = useMemo(
    () => (carrilFiltrado ? mapa.carriles.filter((c) => c.id === carrilFiltrado) : mapa.carriles),
    [mapa.carriles, carrilFiltrado]
  );

  // Orden de recorrido con teclado: el mismo en el que se dibujan las celdas.
  const idsEnOrden = useMemo(
    () => carriles.flatMap((c) => c.tramos.flatMap((t) => t.tiras.map((tira) => tira.id))),
    [carriles]
  );

  useEffect(() => {
    setIndiceActivo(0);
  }, [carrilFiltrado]);

  function moverFoco(siguiente: number) {
    const acotado = Math.max(0, Math.min(siguiente, idsEnOrden.length - 1));
    setIndiceActivo(acotado);
    const celdas = contenedorRef.current?.querySelectorAll<HTMLElement>('[role="gridcell"]');
    celdas?.[acotado]?.focus();
  }

  return (
    <section className={styles.contenedor}>
      <ul className={styles.leyenda}>
        <li>
          <span className={`${styles.muestra} ${styles.vacia}`} /> Vacía
        </li>
        <li>
          <span className={`${styles.muestra} ${styles.parcial}`} /> Parcial
        </li>
        <li>
          <span className={`${styles.muestra} ${styles.llena}`} /> Llena
        </li>
        <li>
          <span className={`${styles.muestra} ${styles.inactiva}`} /> Inactiva
        </li>
      </ul>

      <div
        ref={contenedorRef}
        role="grid"
        aria-label="Mapa del patio"
        className={styles.mapa}
        onKeyDown={(event) => {
          // Roving tabindex: la cuadricula es un solo tab stop y las flechas mueven el foco.
          // Con 1,440 celdas, un tab stop por celda dejaria la pantalla inutilizable.
          if (event.key === "ArrowRight") {
            event.preventDefault();
            moverFoco(indiceActivo + 1);
          } else if (event.key === "ArrowLeft") {
            event.preventDefault();
            moverFoco(indiceActivo - 1);
          } else if (event.key === "Home") {
            event.preventDefault();
            moverFoco(0);
          } else if (event.key === "End") {
            event.preventDefault();
            moverFoco(idsEnOrden.length - 1);
          }
        }}
      >
        {carriles.map((carril) => (
          <div
            key={carril.id}
            role="group"
            aria-label={`Carril ${carril.codigo}`}
            className={styles.carril}
          >
            <h3 className={styles.carrilTitulo}>
              Carril {carril.codigo}
              {carril.tipo_teorico && (
                <span className={styles.carrilTipo}> · {carril.tipo_teorico}</span>
              )}
            </h3>
            <div className={styles.tramos}>
              {carril.tramos.map((tramo) => (
                <div key={tramo.id} className={styles.tramo}>
                  <p className={styles.tramoTitulo}>{tramo.codigo}</p>
                  <div role="row" className={styles.tiras}>
                    {tramo.tiras.map((tira) => (
                      <CeldaTira
                        key={tira.id}
                        tira={tira}
                        carrilCodigo={carril.codigo}
                        tramoCodigo={tramo.codigo}
                        seleccionada={tira.id === tiraSeleccionadaId}
                        sugerida={tira.id === tiraSugeridaId}
                        tabIndex={idsEnOrden[indiceActivo] === tira.id ? 0 : -1}
                        onSeleccionar={onSeleccionarTira}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className={styles.barra}>
        <p className={styles.resumen}>
          {mapa.resumen.ocupadas} de {mapa.resumen.ubicaciones_activas} ubicaciones ocupadas
        </p>
        <div className={styles.filtro}>
          <label htmlFor={filtroId}>Filtrar por carril</label>
          <select
            id={filtroId}
            value={carrilFiltrado}
            onChange={(event) => setCarrilFiltrado(event.target.value)}
          >
            <option value="">Todos los carriles</option>
            {mapa.carriles.map((carril) => (
              <option key={carril.id} value={carril.id}>
                {carril.codigo}
              </option>
            ))}
          </select>
        </div>
      </div>
    </section>
  );
}
