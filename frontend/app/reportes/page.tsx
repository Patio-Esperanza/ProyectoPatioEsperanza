"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import {
  CatalogoReportes,
  REPORTES_DISPONIBLES,
} from "@/components/reportes/CatalogoReportes";
import { FiltrosReporteBar } from "@/components/reportes/FiltrosReporteBar";
import { ResumenKpisReporte } from "@/components/reportes/ResumenKpisReporte";
import { TablaPreviewReporte } from "@/components/reportes/TablaPreviewReporte";
import { ModalProgramarReporte } from "@/components/reportes/ModalProgramarReporte";
import { PanelReportesProgramados } from "@/components/reportes/PanelReportesProgramados";
import { Alert, PageHeader } from "@/components/ui";
import { ROLES_POR_RUTA } from "@/lib/rutas";
import { useAuth } from "@/lib/auth-context";
import { usePatiosDisponibles } from "@/lib/use-patios-disponibles";
import {
  ApiError,
  actualizarReporteProgramado,
  crearReporteProgramado,
  descargarReporteExcel,
  ejecutarReporteProgramadoManual,
  eliminarReporteProgramado,
  listarReportesProgramados,
  obtenerPreviewReporte,
  type FiltrosReportePayload,
  type ReportePreview,
  type ReporteProgramado,
  type ReporteProgramadoPayload,
  type ReporteTipo,
} from "@/lib/api";
import styles from "./page.module.css";

const FILTROS_INICIALES: FiltrosReportePayload = { page: 1, page_size: 25 };

function mensajeError(err: unknown, respaldo: string): string {
  return err instanceof ApiError ? err.message : respaldo;
}

function ReportesContent() {
  const { token } = useAuth();
  const { patios } = usePatiosDisponibles();

  const [tipo, setTipo] = useState<ReporteTipo>(REPORTES_DISPONIBLES[0].tipo);
  const [filtros, setFiltros] = useState<FiltrosReportePayload>(FILTROS_INICIALES);
  const [preview, setPreview] = useState<ReportePreview | null>(null);
  const [cargando, setCargando] = useState(false);
  const [descargando, setDescargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const [programados, setProgramados] = useState<ReporteProgramado[]>([]);
  const [cargandoProgramados, setCargandoProgramados] = useState(false);
  const [ocupadoId, setOcupadoId] = useState<string | null>(null);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [errorModal, setErrorModal] = useState<string | null>(null);

  const definicion = useMemo(
    () => REPORTES_DISPONIBLES.find((reporte) => reporte.tipo === tipo),
    [tipo]
  );
  const tituloReporte = preview?.titulo ?? definicion?.titulo ?? "Reporte";

  const cargarPreview = useCallback(async () => {
    if (!token) return;
    setCargando(true);
    setError(null);
    try {
      setPreview(await obtenerPreviewReporte(token, tipo, filtros));
    } catch (err) {
      setPreview(null);
      setError(mensajeError(err, "No se pudo cargar el reporte"));
    } finally {
      setCargando(false);
    }
  }, [token, tipo, filtros]);

  const cargarProgramados = useCallback(async () => {
    if (!token) return;
    setCargandoProgramados(true);
    try {
      setProgramados(await listarReportesProgramados(token));
    } catch (err) {
      setError(mensajeError(err, "No se pudieron cargar los envíos automáticos"));
    } finally {
      setCargandoProgramados(false);
    }
  }, [token]);

  useEffect(() => {
    void cargarPreview();
  }, [cargarPreview]);

  useEffect(() => {
    void cargarProgramados();
  }, [cargarProgramados]);

  function elegirReporte(nuevoTipo: ReporteTipo) {
    setTipo(nuevoTipo);
    // Los filtros de fecha y búsqueda no se comparten entre reportes: cada uno tiene su
    // propio universo de registros y arrastrarlos deja la tabla vacía sin explicación.
    setFiltros(FILTROS_INICIALES);
    setAviso(null);
  }

  async function descargar() {
    if (!token) return;
    setDescargando(true);
    setError(null);
    try {
      const marca = new Date().toISOString().slice(0, 10);
      await descargarReporteExcel(
        token,
        tipo,
        filtros,
        `${tituloReporte.replace(/\s+/g, "_")}_${marca}.xlsx`
      );
    } catch (err) {
      setError(mensajeError(err, "No se pudo descargar el archivo"));
    } finally {
      setDescargando(false);
    }
  }

  async function guardarProgramado(payload: ReporteProgramadoPayload) {
    if (!token) return;
    setGuardando(true);
    setErrorModal(null);
    try {
      await crearReporteProgramado(token, payload);
      setModalAbierto(false);
      setAviso("Envío automático programado.");
      await cargarProgramados();
    } catch (err) {
      setErrorModal(mensajeError(err, "No se pudo guardar la tarea"));
    } finally {
      setGuardando(false);
    }
  }

  async function probarEnvio(id: string) {
    if (!token) return;
    setOcupadoId(id);
    setError(null);
    try {
      const respuesta = await ejecutarReporteProgramadoManual(token, id);
      setAviso(respuesta.detail);
      await cargarProgramados();
    } catch (err) {
      setError(mensajeError(err, "No se pudo enviar el reporte"));
    } finally {
      setOcupadoId(null);
    }
  }

  async function alternarActivo(programado: ReporteProgramado) {
    if (!token) return;
    setOcupadoId(programado.id);
    setError(null);
    try {
      await actualizarReporteProgramado(token, programado.id, {
        activo: !programado.activo,
      });
      await cargarProgramados();
    } catch (err) {
      setError(mensajeError(err, "No se pudo actualizar la tarea"));
    } finally {
      setOcupadoId(null);
    }
  }

  async function eliminar(id: string) {
    if (!token) return;
    setOcupadoId(id);
    setError(null);
    try {
      await eliminarReporteProgramado(token, id);
      await cargarProgramados();
    } catch (err) {
      setError(mensajeError(err, "No se pudo eliminar la tarea"));
    } finally {
      setOcupadoId(null);
    }
  }

  return (
    <main className={styles.main}>
      <PageHeader
        titulo="Reportes"
        descripcion="Consulta, exporta a Excel y programa envíos automáticos por correo."
      />

      {error && <Alert tone="danger">{error}</Alert>}
      {aviso && <Alert tone="success">{aviso}</Alert>}

      <div className={styles.columnas}>
        <aside className={styles.lateral}>
          <CatalogoReportes seleccionado={tipo} onSeleccionar={elegirReporte} />
          <PanelReportesProgramados
            programados={programados}
            cargando={cargandoProgramados}
            ocupadoId={ocupadoId}
            onProbar={(id) => void probarEnvio(id)}
            onAlternarActivo={(programado) => void alternarActivo(programado)}
            onEliminar={(id) => void eliminar(id)}
          />
        </aside>

        <section className={styles.detalle}>
          <FiltrosReporteBar
            filtros={filtros}
            patios={patios}
            onCambiar={setFiltros}
            onDescargar={() => void descargar()}
            onProgramar={() => {
              setErrorModal(null);
              setModalAbierto(true);
            }}
            descargando={descargando}
            deshabilitado={cargando}
          />

          {preview && <ResumenKpisReporte kpis={preview.kpis} />}

          <TablaPreviewReporte
            preview={preview}
            cargando={cargando}
            onCambiarPagina={(page) => setFiltros((actual) => ({ ...actual, page }))}
          />
        </section>
      </div>

      <ModalProgramarReporte
        abierto={modalAbierto}
        tipo={tipo}
        tituloReporte={tituloReporte}
        patioId={filtros.patio_id ?? null}
        guardando={guardando}
        error={errorModal}
        onCerrar={() => setModalAbierto(false)}
        onGuardar={(payload) => void guardarProgramado(payload)}
      />
    </main>
  );
}

export default function ReportesPage() {
  return (
    <AuthGuard roles={ROLES_POR_RUTA["/reportes"]}>
      <ReportesContent />
    </AuthGuard>
  );
}
