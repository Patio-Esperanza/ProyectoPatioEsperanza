"use client";

import { useCallback, useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { PatioSelect } from "@/components/PatioSelect";
import { MapaPatio } from "@/components/mapa/MapaPatio";
import { DetalleTira } from "@/components/mapa/DetalleTira";
import { PanelPendientes } from "@/components/mapa/PanelPendientes";
import { Alert, Button, PageHeader } from "@/components/ui";
import { ROLES_POR_RUTA } from "@/lib/rutas";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  crearMovimiento,
  listarContenedores,
  obtenerDetalleTira,
  obtenerMapaPatio,
  sugerirUbicacion,
  type Contenedor,
  type DetalleTira as DetalleTiraData,
  type MapaPatio as MapaPatioData,
  type SugerenciaUbicacion,
} from "@/lib/api";
import styles from "./page.module.css";

const SIN_ENTRADA =
  "Este patio no tiene punto de entrada, así que no se puede sugerir una ubicación.";

function MapaContent() {
  const { token } = useAuth();
  const [patioId, setPatioId] = useState("");
  const [mapa, setMapa] = useState<MapaPatioData | null>(null);
  const [pendientes, setPendientes] = useState<Contenedor[]>([]);
  const [cargandoPendientes, setCargandoPendientes] = useState(false);
  const [contenedorId, setContenedorId] = useState<string | null>(null);
  const [sugerencia, setSugerencia] = useState<SugerenciaUbicacion | null>(null);
  const [tiraId, setTiraId] = useState<string | null>(null);
  const [detalle, setDetalle] = useState<DetalleTiraData | null>(null);
  const [colocando, setColocando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const cargarMapa = useCallback(async () => {
    if (!token || !patioId) return;
    try {
      setMapa(await obtenerMapaPatio(token, patioId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el mapa");
    }
  }, [token, patioId]);

  const cargarPendientes = useCallback(async () => {
    if (!token || !patioId) return;
    setCargandoPendientes(true);
    try {
      setPendientes(await listarContenedores(token, { patio_id: patioId, sin_ubicacion: true }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los pendientes");
    } finally {
      setCargandoPendientes(false);
    }
  }, [token, patioId]);

  useEffect(() => {
    setContenedorId(null);
    setSugerencia(null);
    setTiraId(null);
    setDetalle(null);
    setError(null);
    setAviso(null);
    void cargarMapa();
    void cargarPendientes();
  }, [patioId, cargarMapa, cargarPendientes]);

  async function elegirContenedor(id: string) {
    setContenedorId(id);
    setError(null);
    setAviso(null);
    setSugerencia(null);
    if (!token || !mapa) return;
    if (!mapa.ubicacion_entrada_id) {
      setAviso(SIN_ENTRADA);
      return;
    }
    try {
      const propuesta = await sugerirUbicacion(token, {
        patio_id: mapa.patio_id,
        contenedor_id: id,
        punto_referencia_ubicacion_id: mapa.ubicacion_entrada_id,
      });
      setSugerencia(propuesta);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo calcular la sugerencia");
    }
  }

  async function elegirTira(id: string) {
    setTiraId(id);
    setError(null);
    if (!token) return;
    try {
      setDetalle(await obtenerDetalleTira(token, id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la tira");
    }
  }

  async function colocar(ubicacionId: string, motivo: string | null) {
    if (!token || !contenedorId) return;
    setColocando(true);
    setError(null);
    try {
      await crearMovimiento(token, {
        contenedor_id: contenedorId,
        ubicacion_destino_id: ubicacionId,
        tipo: "ingreso",
        override_manual: motivo !== null,
        ...(motivo !== null ? { motivo_override: motivo } : {}),
        ...(sugerencia ? { score_sugerido: sugerencia.costo, score_elegido: sugerencia.costo } : {}),
      });
      setContenedorId(null);
      setSugerencia(null);
      setDetalle(null);
      setTiraId(null);
      await Promise.all([cargarMapa(), cargarPendientes()]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo colocar el contenedor");
      // El mapa que se estaba viendo ya no describe el patio: alguien mas gano la ubicacion.
      await cargarMapa();
    } finally {
      setColocando(false);
    }
  }

  return (
    <main className={styles.main}>
      <PageHeader
        titulo="Mapa del patio"
        accion={
          <Button variant="secondary" onClick={() => void cargarMapa()}>
            Actualizar
          </Button>
        }
      />

      <div className={styles.selector}>
        <label htmlFor="patio_id">Patio</label>
        <PatioSelect id="patio_id" value={patioId} onChange={setPatioId} />
      </div>

      {error && <Alert tone="danger">{error}</Alert>}
      {aviso && <Alert tone="info">{aviso}</Alert>}

      <div className={styles.columnas}>
        <PanelPendientes
          contenedores={pendientes}
          seleccionadoId={contenedorId}
          cargando={cargandoPendientes}
          onSeleccionar={(id) => void elegirContenedor(id)}
        />

        <div className={styles.central}>
          {mapa && (
            <MapaPatio
              mapa={mapa}
              tiraSeleccionadaId={tiraId}
              tiraSugeridaId={sugerencia?.tira_id ?? null}
              onSeleccionarTira={(id) => void elegirTira(id)}
            />
          )}
          {detalle && (
            <DetalleTira
              detalle={detalle}
              contenedorSeleccionado={contenedorId}
              ubicacionSugeridaId={sugerencia?.ubicacion_id ?? null}
              colocando={colocando}
              onColocar={(ubicacionId, motivo) => void colocar(ubicacionId, motivo)}
            />
          )}
        </div>
      </div>
    </main>
  );
}

export default function MapaPage() {
  return (
    <AuthGuard roles={ROLES_POR_RUTA["/mapa"]}>
      <MapaContent />
    </AuthGuard>
  );
}
