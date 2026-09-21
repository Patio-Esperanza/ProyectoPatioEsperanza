import { describe, expect, it } from "vitest";
import { ROLES_POR_RUTA, ROLES_STAFF, homePorRol } from "./rutas";

describe("homePorRol", () => {
  it("sends a cliente to Mis contenedores", () => {
    expect(homePorRol("cliente")).toBe("/mis-contenedores");
  });

  it("sends any staff role to Patios", () => {
    expect(homePorRol("operador")).toBe("/patios");
    expect(homePorRol("supervisor")).toBe("/patios");
    expect(homePorRol("admin")).toBe("/patios");
  });

  it("falls back to Patios for an unknown role", () => {
    expect(homePorRol("guardia")).toBe("/patios");
  });
});

describe("ROLES_POR_RUTA", () => {
  it("restricts the admin-only routes to admin", () => {
    expect(ROLES_POR_RUTA["/usuarios"]).toEqual(["admin"]);
    expect(ROLES_POR_RUTA["/clientes"]).toEqual(["admin"]);
  });

  it("restricts the cliente routes to cliente", () => {
    expect(ROLES_POR_RUTA["/solicitar"]).toEqual(["cliente"]);
    expect(ROLES_POR_RUTA["/mis-contenedores"]).toEqual(["cliente"]);
  });

  it("gives the staff routes the three writing roles of the backend", () => {
    for (const ruta of [
      "/patios",
      "/contenedores",
      "/movimientos",
      "/ubicaciones/sugerir",
      "/porteria",
      "/salidas",
    ]) {
      expect(ROLES_POR_RUTA[ruta]).toEqual([...ROLES_STAFF]);
    }
  });

  it("never lets a cliente into a staff route", () => {
    for (const roles of Object.values(ROLES_POR_RUTA)) {
      if (roles.includes("operador")) {
        expect(roles).not.toContain("cliente");
      }
    }
  });
});
