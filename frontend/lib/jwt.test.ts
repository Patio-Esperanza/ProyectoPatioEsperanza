import { describe, expect, it } from "vitest";
import { decodeJwtPayload } from "./jwt";

describe("decodeJwtPayload", () => {
  it("decodes the payload segment of a JWT", () => {
    const payload = { sub: "usr-1", rol: "admin", patios: ["patio-1"], iat: 0, exp: 9999999999 };
    const token = `${btoa("{}")}.${btoa(JSON.stringify(payload))}.signature`;

    expect(decodeJwtPayload(token)).toEqual(payload);
  });
});
