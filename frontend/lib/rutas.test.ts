import { describe, expect, it } from "vitest";
import { ROLES_POR_RUTA, ROLES_STAFF, homePorRol } from "./rutas";

/** Espejo de `RolUsuario` en `backend/app/models/enums.py`. */
const TODOS_LOS_ROLES = [
  "cliente",
  "operador",
  "supervisor",
  "admin",
  "guardia",
  "despachador",
  "operador_grua",
  "cuadrilla",
];

describe("homePorRol", () => {
  it.each([
    ["cliente", "/mis-contenedores"],
    ["cuadrilla", "/servicios"],
    ["guardia", "/porteria"],
    ["despachador", "/salidas"],
    ["operador", "/patios"],
    ["supervisor", "/patios"],
    ["admin", "/patios"],
    ["operador_grua", "/inicio"],
    ["desconocido", "/inicio"],
  ])("sends %s to %s", (rol, ruta) => {
    expect(homePorRol(rol)).toBe(ruta);
  });

  it.each(TODOS_LOS_ROLES)("lands %s on a route it can see", (rol) => {
    const permitidos = ROLES_POR_RUTA[homePorRol(rol)];
    expect(permitidos === undefined || permitidos.includes(rol)).toBe(true);
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

  it("gives the plain staff routes the three writing roles of the backend", () => {
    for (const ruta of ["/patios", "/contenedores", "/movimientos", "/ubicaciones/sugerir", "/mapa"]) {
      expect(ROLES_POR_RUTA[ruta]).toEqual([...ROLES_STAFF]);
    }
  });

  it("matches the backend for the operational routes", () => {
    expect(ROLES_POR_RUTA["/porteria"]).toEqual(["guardia", ...ROLES_STAFF]);
    expect(ROLES_POR_RUTA["/salidas"]).toEqual(["despachador", ...ROLES_STAFF]);
    expect(ROLES_POR_RUTA["/servicios"]).toEqual(["cuadrilla", "supervisor", "admin"]);
  });

  it("never lets a cliente into a staff route", () => {
    for (const roles of Object.values(ROLES_POR_RUTA)) {
      if (roles.includes("operador") || roles.includes("supervisor")) {
        if (roles !== ROLES_POR_RUTA["/reportes"]) {
          expect(roles).not.toContain("cliente");
        }
      }
    }
  });
});
