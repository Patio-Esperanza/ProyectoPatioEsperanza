"use client";

import { useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { ROLES_POR_RUTA } from "@/lib/rutas";
import { PatioSelect } from "@/components/PatioSelect";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  createContenedor,
  type Contenedor,
  type TamanoContenedor,
  type TipoContenedor,
} from "@/lib/api";
import { Alert, Badge, Button, Card, Field, PageHeader } from "@/components/ui";
import styles from "./page.module.css";

function ContenedoresContent() {
  const { token } = useAuth();
  const [numero, setNumero] = useState("");
  const [tipo, setTipo] = useState<TipoContenedor>("lleno");
  const [tamano, setTamano] = useState<TamanoContenedor>("40");
  const [patioId, setPatioId] = useState("");
  const [pesoKg, setPesoKg] = useState("");
  const [creado, setCreado] = useState<Contenedor | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError(null);
    setCreado(null);
    try {
      const contenedor = await createContenedor(token, {
        numero_contenedor: numero,
        tipo,
        tamano,
        patio_id: patioId,
        peso_kg: Number(pesoKg),
      });
      setCreado(contenedor);
      setNumero("");
      setPesoKg("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el contenedor");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.main}>
      <PageHeader
        titulo="Contenedores"
        descripcion="Alta de contenedor en el patio. El número se valida contra el checksum ISO 6346."
      />

      {error && <Alert tone="danger">{error}</Alert>}

      {creado && (
        <Alert tone="success" titulo="Contenedor creado">
          <span className="mono">{creado.numero_contenedor}</span> — estado{" "}
          <Badge tone="info">{creado.estado}</Badge>
        </Alert>
      )}

      <Card className={styles.formulario}>
        <form onSubmit={handleSubmit} className={styles.campos}>
          <Field
            label="Número de contenedor"
            id="numero"
            value={numero}
            onChange={(e) => setNumero(e.target.value)}
            hint="Once caracteres, cuatro letras y siete dígitos. Por ejemplo CSQU3054383."
            required
            maxLength={11}
            // El número siempre va en mayúsculas y sin corrección del teclado móvil.
            autoCapitalize="characters"
            autoCorrect="off"
            spellCheck={false}
            className="mono"
          />

          <div className={styles.fila}>
            <div className={styles.selector}>
              <label className={styles.etiqueta} htmlFor="tipo">
                Tipo
              </label>
              <select
                id="tipo"
                className={styles.select}
                value={tipo}
                onChange={(e) => setTipo(e.target.value as TipoContenedor)}
              >
                <option value="lleno">Lleno</option>
                <option value="vacio">Vacío</option>
              </select>
            </div>

            <div className={styles.selector}>
              <label className={styles.etiqueta} htmlFor="tamano">
                Tamaño
              </label>
              <select
                id="tamano"
                className={styles.select}
                value={tamano}
                onChange={(e) => setTamano(e.target.value as TamanoContenedor)}
              >
                <option value="20">20&apos;</option>
                <option value="40">40&apos;</option>
                <option value="45">45&apos;</option>
              </select>
            </div>
          </div>

          <div className={styles.selector}>
            <label className={styles.etiqueta} htmlFor="patio_id">
              Patio
            </label>
            <PatioSelect id="patio_id" value={patioId} onChange={setPatioId} />
          </div>

          <Field
            label="Peso (kg)"
            id="peso_kg"
            type="number"
            inputMode="numeric"
            value={pesoKg}
            onChange={(e) => setPesoKg(e.target.value)}
            required
          />

          <Button type="submit" loading={submitting} className={styles.enviar}>
            Crear contenedor
          </Button>
        </form>
      </Card>
    </main>
  );
}

export default function ContenedoresPage() {
  return (
    <AuthGuard roles={ROLES_POR_RUTA["/contenedores"]}>
      <ContenedoresContent />
    </AuthGuard>
  );
}
