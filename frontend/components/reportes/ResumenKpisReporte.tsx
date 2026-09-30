import type { ReporteKpi } from "@/lib/api";
import styles from "./ResumenKpisReporte.module.css";

interface ResumenKpisReporteProps {
  kpis: ReporteKpi[];
}

export function ResumenKpisReporte({ kpis }: ResumenKpisReporteProps) {
  if (kpis.length === 0) return null;

  return (
    <section className={styles.rejilla} aria-label="Resumen del reporte">
      {kpis.map((kpi) => (
        <article key={kpi.label} className={`${styles.tarjeta} ${styles[kpi.tone]}`}>
          <p className={styles.etiqueta}>{kpi.label}</p>
          <p className={`${styles.valor} mono`}>{kpi.value}</p>
          {kpi.subtext && <p className={styles.subtexto}>{kpi.subtext}</p>}
        </article>
      ))}
    </section>
  );
}
