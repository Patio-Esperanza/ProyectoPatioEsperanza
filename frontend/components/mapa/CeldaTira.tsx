import type { TiraMapa } from "@/lib/api";
import styles from "./CeldaTira.module.css";

interface CeldaTiraProps {
  tira: TiraMapa;
  carrilCodigo: string;
  tramoCodigo: string;
  seleccionada: boolean;
  sugerida: boolean;
  /** Roving tabindex: solo la celda activa vale 0, el resto -1. */
  tabIndex: number;
  onSeleccionar: (tiraId: string) => void;
}

type Llenado = "vacia" | "parcial" | "llena" | "inactiva";

function calcularLlenado(tira: TiraMapa): Llenado {
  if (tira.niveles_activos === 0) return "inactiva";
  if (tira.niveles_ocupados === 0) return "vacia";
  if (tira.niveles_ocupados >= tira.niveles_activos) return "llena";
  return "parcial";
}

export function CeldaTira({
  tira,
  carrilCodigo,
  tramoCodigo,
  seleccionada,
  sugerida,
  tabIndex,
  onSeleccionar,
}: CeldaTiraProps) {
  const llenado = calcularLlenado(tira);
  const inactiva = llenado === "inactiva";

  // El color nunca es el unico indicador: la celda siempre imprime su conteo, y el
  // aria-label lo repite en palabras para quien no ve la cuadricula.
  const etiqueta = `Carril ${carrilCodigo}, tramo ${tramoCodigo}, tira ${tira.codigo}, ${tira.niveles_ocupados} de ${tira.niveles_totales} niveles ocupados`;

  return (
    <div
      role="gridcell"
      aria-label={etiqueta}
      aria-selected={seleccionada}
      aria-disabled={inactiva}
      tabIndex={tabIndex}
      className={[
        styles.celda,
        styles[llenado],
        seleccionada ? styles.seleccionada : "",
        sugerida ? styles.sugerida : "",
      ]
        .filter(Boolean)
        .join(" ")}
      onClick={() => {
        if (!inactiva) onSeleccionar(tira.id);
      }}
      onKeyDown={(event) => {
        if (inactiva) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSeleccionar(tira.id);
        }
      }}
    >
      <span className={styles.conteo}>
        {tira.niveles_ocupados}/{tira.niveles_totales}
      </span>
      {sugerida && <span className={styles.sugerencia}>Sugerido</span>}
    </div>
  );
}
