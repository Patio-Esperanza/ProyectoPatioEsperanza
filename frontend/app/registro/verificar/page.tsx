import { Suspense } from "react";
import VerificarForm from "./VerificarForm";

export const dynamic = "force-static";

export default function Page() {
  return (
    <Suspense fallback={<p>Cargando...</p>}>
      <VerificarForm />
    </Suspense>
  );
}