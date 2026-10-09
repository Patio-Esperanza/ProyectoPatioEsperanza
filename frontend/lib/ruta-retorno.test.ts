import { beforeEach, describe, expect, it } from "vitest";
import { guardarRutaRetorno, rutaSegura, tomarRutaRetorno } from "./ruta-retorno";

beforeEach(() => {
  sessionStorage.clear();
});

describe("rutaSegura", () => {
  it("accepts an internal path with its query string", () => {
    expect(rutaSegura("/contenedores?patio=p1")).toBe("/contenedores?patio=p1");
  });

  it("rejects a protocol-relative path that would leave the site", () => {
    expect(rutaSegura("//evil.com")).toBeNull();
  });

  it("rejects an absolute external URL", () => {
    expect(rutaSegura("https://evil.com/x")).toBeNull();
  });

  it("rejects a backslash path that some browsers read as external", () => {
    expect(rutaSegura("/\\evil.com")).toBeNull();
  });

  it("rejects control characters", () => {
    expect(rutaSegura("/patios\n/x")).toBeNull();
  });

  it("rejects /login so the user is not sent back to the form", () => {
    expect(rutaSegura("/login")).toBeNull();
    expect(rutaSegura("/login?x=1")).toBeNull();
  });

  it("rejects empty and missing values", () => {
    expect(rutaSegura("")).toBeNull();
    expect(rutaSegura(null)).toBeNull();
    expect(rutaSegura(undefined)).toBeNull();
  });
});

describe("guardarRutaRetorno / tomarRutaRetorno", () => {
  it("returns the stored route", () => {
    guardarRutaRetorno("/mapa?patio=p1");
    expect(tomarRutaRetorno()).toBe("/mapa?patio=p1");
  });

  it("consumes the route so it does not reappear on the next login", () => {
    guardarRutaRetorno("/mapa");
    tomarRutaRetorno();
    expect(tomarRutaRetorno()).toBeNull();
  });

  it("does not store an unsafe route", () => {
    guardarRutaRetorno("//evil.com");
    expect(tomarRutaRetorno()).toBeNull();
  });

  it("returns null when nothing was stored", () => {
    expect(tomarRutaRetorno()).toBeNull();
  });

  it("ignores an unsafe value injected directly into sessionStorage", () => {
    sessionStorage.setItem("patio_esperanza_ruta_retorno", "https://evil.com");
    expect(tomarRutaRetorno()).toBeNull();
  });
});
