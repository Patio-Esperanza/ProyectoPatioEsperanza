"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { ROLES_POR_RUTA } from "@/lib/rutas";
import { useAuth } from "@/lib/auth-context";
import { ApiError, actualizarPatio, createPatio, listPatios, type Patio } from "@/lib/api";
import {
  Alert,
  Button,
  Card,
  DataTable,
  EmptyState,
  Field,
  PageHeader,
  SkeletonText,
} from "@/components/ui";
import styles from "./page.module.css";

function PatiosContent() {
  const { token, user } = useAuth();
  const [patios, setPatios] = useState<Patio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nombre, setNombre] = useState("");
  const [codigo, setCodigo] = useState("");
  const [creating, setCreating] = useState(false);

  const esAdmin = user?.rol === "admin";

  const cargarPatios = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await listPatios(token);
      setPatios(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los patios");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    cargarPatios();
  }, [cargarPatios]);

  async function handleCrear(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setCreating(true);
    setError(null);
    try {
      await createPatio(token, { nombre, codigo });
      setNombre("");
      setCodigo("");
      await cargarPatios();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el patio");
    } finally {
      setCreating(false);
    }
  }

  async function handleActualizarAnticipacion(patioId: string, valor: number) {
    if (!token || Number.isNaN(valor) || valor <= 0) return;
    try {
      await actualizarPatio(token, patioId, valor);
      await cargarPatios();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar la anticipación");
    }
  }

  const columnas = [
    { key: "codigo", header: "Código", mono: true },
    { key: "nombre", header: "Nombre" },
    ...(esAdmin
      ? [{ key: "anticipacion", header: "Anticipación mínima (h)", align: "end" as const }]
      : []),
  ];

  function renderCelda(patio: Patio, key: string) {
    if (key === "codigo") return patio.codigo;
    if (key === "nombre") return patio.nombre;
    return (
      // El envoltorio de Field es un bloque y llenaría la celda, dejando el campo pegado
      // a la izquierda aunque la columna esté alineada a la derecha.
      <span className={styles.celdaAnticipacion}>
        <Field
          // La etiqueta lleva el código del patio porque hay un campo por fila y, sin él,
          // un lector de pantalla oiría la misma etiqueta repetida en toda la tabla.
          label={`Anticipación mínima (h) — ${patio.codigo}`}
          // El encabezado de la columna ya muestra el nombre del campo: repetirlo en cada
          // fila sería ruido. Sigue anunciándose a los lectores de pantalla.
          labelHidden
          id={`anticipacion-${patio.id}`}
          type="number"
          min={1}
          defaultValue={patio.anticipacion_minima_horas}
          onBlur={(e) => handleActualizarAnticipacion(patio.id, Number(e.target.value))}
          className={styles.anticipacion}
        />
      </span>
    );
  }

  return (
    <main className={styles.main}>
      <PageHeader
        titulo="Patios"
        descripcion="Patios registrados y su tiempo mínimo de anticipación para solicitar salida."
      />

      {error && (
        <Alert tone="danger">
          {error}{" "}
          <Button variant="ghost" size="sm" onClick={cargarPatios}>
            Reintentar
          </Button>
        </Alert>
      )}

      {loading ? (
        <Card>
          <p className="sr-only" role="status">
            Cargando patios
          </p>
          <SkeletonText lines={4} />
        </Card>
      ) : error ? (
        /*
         * Con la carga fallida no se sabe si hay patios o no. Mostrar aquí el estado
         * vacío afirmaría algo falso: la alerta de arriba ya explica qué pasó.
         */
        null
      ) : patios.length === 0 ? (
        <EmptyState
          titulo="Todavía no hay patios"
          descripcion={
            esAdmin
              ? "Crea el primero con el formulario de abajo."
              : "Pídele a un administrador que registre el primer patio."
          }
        />
      ) : (
        <Card>
          <DataTable
            columns={columnas}
            rows={patios}
            getRowKey={(patio) => patio.id}
            renderCell={renderCelda}
            caption="Patios registrados"
          />
        </Card>
      )}

      {esAdmin && (
        <Card className={styles.formulario}>
          <h2 className={styles.tituloFormulario}>Nuevo patio</h2>
          <form className={styles.campos} onSubmit={handleCrear}>
            <Field
              label="Nombre"
              id="nombre"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              required
            />
            <Field
              label="Código"
              id="codigo"
              value={codigo}
              onChange={(e) => setCodigo(e.target.value)}
              hint="Identificador corto del patio, por ejemplo PN."
              required
            />
            <Button type="submit" loading={creating} className={styles.enviar}>
              Crear patio
            </Button>
          </form>
        </Card>
      )}
    </main>
  );
}

export default function PatiosPage() {
  return (
    <AuthGuard roles={ROLES_POR_RUTA["/patios"]}>
      <PatiosContent />
    </AuthGuard>
  );
}
