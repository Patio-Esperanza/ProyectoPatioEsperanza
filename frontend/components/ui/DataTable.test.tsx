import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { DataTable } from "./DataTable";

interface Fila { id: string; nombre: string; cantidad: number }
const rows: Fila[] = [{ id: "1", nombre: "Contenedor A", cantidad: 12 }];
const columns = [{ key: "nombre", header: "Nombre" }, { key: "cantidad", header: "Cantidad", align: "end" as const, mono: true }];
const getRowKey = (row: Fila) => row.id;
const renderCell = (row: Fila, key: string) => key === "nombre" ? row.nombre : row.cantidad;

describe("DataTable", () => {
  it("renders semantic headers and cells with an accessible caption", () => {
    render(<DataTable columns={columns} rows={rows} getRowKey={getRowKey} renderCell={renderCell} caption="Inventario" />);
    const table = screen.getByRole("table", { name: "Inventario" });
    expect(within(table).getAllByRole("rowgroup")).toHaveLength(2);
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    expect(within(table).getByRole("columnheader", { name: "Nombre" })).toHaveAttribute("scope", "col");
    expect(within(table).getByRole("columnheader", { name: "Cantidad" })).toHaveAttribute("scope", "col");
    expect(within(table).getByRole("cell", { name: "Contenedor A" })).toBeInTheDocument();
    expect(within(table).getByRole("cell", { name: "12" })).toBeInTheDocument();
  });

  it("renders the default empty message across all columns", () => {
    render(<DataTable columns={columns} rows={[]} getRowKey={getRowKey} renderCell={renderCell} />);
    expect(screen.getByRole("cell", { name: "No hay registros para mostrar." })).toHaveAttribute("colspan", "2");
  });

  it("renders a custom empty message", () => {
    render(<DataTable columns={columns} rows={[]} getRowKey={getRowKey} renderCell={renderCell} emptyMessage="No hay contenedores" />);
    expect(screen.getByRole("cell", { name: "No hay contenedores" })).toHaveAttribute("colspan", "2");
  });

  it("supports explicit start alignment and rich cell content", () => {
    render(<DataTable columns={[{ key: "nombre", header: "Nombre", align: "start", mono: false }]}
      rows={rows} getRowKey={getRowKey} renderCell={(row) => <a href={`/contenedores/${row.id}`}>{row.nombre}</a>} />);
    expect(screen.getByRole("link", { name: "Contenedor A" })).toHaveAttribute("href", "/contenedores/1");
  });

  it("keeps a valid empty cell when there are no columns", () => {
    render(<DataTable columns={[]} rows={[]} getRowKey={getRowKey} renderCell={renderCell} />);
    expect(screen.getByRole("cell")).toHaveAttribute("colspan", "1");
  });
});
