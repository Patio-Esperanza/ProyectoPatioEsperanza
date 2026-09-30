"use client";

import { useEffect, useState } from "react";
import type {
  FrecuenciaReporte,
  ReporteProgramadoPayload,
  ReporteTipo,
} from "@/lib/api";
import { Alert, Button, Field } from "@/components/ui";
import styles from "./ModalProgramarReporte.module.css";

interface ModalProgramarReporteProps {
  abierto: boolean;
  tipo: ReporteTipo;
  tituloReporte: string;
  patioId?: string | null;
  guardando?: boolean;
  error?: string | null;
  onCerrar: () => void;
  onGuardar: (payload: ReporteProgramadoPayload) => void;
}

/** APScheduler numera los días con 0 = lunes. */
const DIAS_SEMANA = [
  { valor: 0, texto: "Lunes" },
  { valor: 1, texto: "Martes" },
  { valor: 2, texto: "Miércoles" },
  { valor: 3, texto: "Jueves" },
  { valor: 4, texto: "Viernes" },
  { valor: 5, texto: "Sábado" },
  { valor: 6, texto: "Domingo" },
];

export function ModalProgramarReporte({
  abierto,
  tipo,
  tituloReporte,
  patioId = null,
  guardando = false,
  error = null,
  onCerrar,
  onGuardar,
}: ModalProgramarReporteProps) {
  const [nombre, setNombre] = useState("");
  const [frecuencia, setFrecuencia] = useState<FrecuenciaReporte>("diario");
  const [hora, setHora] = useState("08:00");
  const [diaSemana, setDiaSemana] = useState(0);
  const [diaMes, setDiaMes] = useState(1);
  const [destinatarios, setDestinatarios] = useState("");
  const [asunto, setAsunto] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [errorLocal, setErrorLocal] = useState<string | null>(null);

  // Al abrirse el modal se repuebla con el reporte que el usuario está viendo, para que no
  // arrastre el nombre ni el asunto de la vez anterior.
  useEffect(() => {
    if (!abierto) return;
    setNombre(`Envío de ${tituloReporte}`);
    setAsunto(`Reporte: ${tituloReporte}`);
    setFrecuencia("diario");
    setHora("08:00");
    setDiaSemana(0);
    setDiaMes(1);
    setDestinatarios("");
    setMensaje("");
    setErrorLocal(null);
  }, [abierto, tituloReporte]);

  if (!abierto) return null;

  function enviar() {
    const listaCorreos = destinatarios
      .split(/[,\n;]/)
      .map((correo) => correo.trim())
      .filter(Boolean);

    if (listaCorreos.length === 0) {
      setErrorLocal("Agrega al menos un destinatario.");
      return;
    }
    const invalido = listaCorreos.find((correo) => !correo.includes("@"));
    if (invalido) {
      setErrorLocal(`Correo inválido: ${invalido}`);
      return;
    }

    const [horaTexto, minutoTexto] = hora.split(":");
    setErrorLocal(null);

    onGuardar({
      nombre,
      tipo_reporte: tipo,
      patio_id: patioId,
      frecuencia,
      hora: Number(horaTexto),
      minuto: Number(minutoTexto),
      dia_semana: frecuencia === "semanal" ? diaSemana : null,
      dia_mes: frecuencia === "mensual" ? diaMes : null,
      destinatarios: listaCorreos,
      asunto,
      mensaje: mensaje.trim() || null,
      activo: true,
    });
  }

  return (
    <div className={styles.fondo} role="presentation" onClick={onCerrar}>
      <div
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-modal-programar"
        onClick={(evento) => evento.stopPropagation()}
      >
        <header className={styles.cabecera}>
          <h2 id="titulo-modal-programar" className={styles.titulo}>
            Programar envío automático
          </h2>
          <p className={styles.subtitulo}>{tituloReporte}</p>
        </header>

        {(errorLocal || error) && <Alert tone="danger">{errorLocal ?? error}</Alert>}

        <div className={styles.formulario}>
          <Field
            id="programar-nombre"
            label="Nombre de la tarea"
            value={nombre}
            required
            onChange={(evento) => setNombre(evento.target.value)}
          />

          <div className={styles.fila}>
            <div className={styles.campo}>
              <label className={styles.etiqueta} htmlFor="programar-frecuencia">
                Frecuencia
              </label>
              <select
                id="programar-frecuencia"
                className={styles.select}
                value={frecuencia}
                onChange={(evento) =>
                  setFrecuencia(evento.target.value as FrecuenciaReporte)
                }
              >
                <option value="diario">Diaria</option>
                <option value="semanal">Semanal</option>
                <option value="mensual">Mensual</option>
              </select>
            </div>

            <Field
              id="programar-hora"
              label="Hora de envío"
              type="time"
              value={hora}
              required
              onChange={(evento) => setHora(evento.target.value)}
            />
          </div>

          {frecuencia === "semanal" && (
            <div className={styles.campo}>
              <label className={styles.etiqueta} htmlFor="programar-dia-semana">
                Día de la semana
              </label>
              <select
                id="programar-dia-semana"
                className={styles.select}
                value={diaSemana}
                onChange={(evento) => setDiaSemana(Number(evento.target.value))}
              >
                {DIAS_SEMANA.map((dia) => (
                  <option key={dia.valor} value={dia.valor}>
                    {dia.texto}
                  </option>
                ))}
              </select>
            </div>
          )}

          {frecuencia === "mensual" && (
            <Field
              id="programar-dia-mes"
              label="Día del mes"
              type="number"
              min={1}
              max={31}
              value={diaMes}
              onChange={(evento) => setDiaMes(Number(evento.target.value))}
            />
          )}

          <div className={styles.campo}>
            <label className={styles.etiqueta} htmlFor="programar-destinatarios">
              Destinatarios
            </label>
            <textarea
              id="programar-destinatarios"
              className={styles.textarea}
              rows={3}
              placeholder="operaciones@empresa.com, gerencia@empresa.com"
              value={destinatarios}
              onChange={(evento) => setDestinatarios(evento.target.value)}
            />
            <p className={styles.ayuda}>Separa los correos con coma o salto de línea.</p>
          </div>

          <Field
            id="programar-asunto"
            label="Asunto del correo"
            value={asunto}
            required
            onChange={(evento) => setAsunto(evento.target.value)}
          />

          <div className={styles.campo}>
            <label className={styles.etiqueta} htmlFor="programar-mensaje">
              Mensaje (opcional)
            </label>
            <textarea
              id="programar-mensaje"
              className={styles.textarea}
              rows={3}
              value={mensaje}
              onChange={(evento) => setMensaje(evento.target.value)}
            />
          </div>
        </div>

        <footer className={styles.acciones}>
          <Button variant="ghost" onClick={onCerrar} disabled={guardando}>
            Cancelar
          </Button>
          <Button onClick={enviar} loading={guardando}>
            Guardar tarea
          </Button>
        </footer>
      </div>
    </div>
  );
}
