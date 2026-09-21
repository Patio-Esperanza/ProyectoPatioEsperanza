import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PatioSelect } from "./PatioSelect";
import { usePatiosDisponibles } from "@/lib/use-patios-disponibles";

vi.mock("@/lib/use-patios-disponibles", () => ({ usePatiosDisponibles: vi.fn() }));

beforeEach(() => {
  vi.mocked(usePatiosDisponibles).mockReset();
});

describe("PatioSelect", () => {
  it("shows a loading message while patios load", () => {
    vi.mocked(usePatiosDisponibles).mockReturnValue({ patios: [], loading: true });

    render(<PatioSelect id="patio_id" value="" onChange={vi.fn()} />);

    expect(screen.getByText("Cargando patios...")).toBeInTheDocument();
  });

  it("shows a message when there are no patios available", () => {
    vi.mocked(usePatiosDisponibles).mockReturnValue({ patios: [], loading: false });

    render(<PatioSelect id="patio_id" value="" onChange={vi.fn()} />);

    expect(screen.getByText("No tienes patios asignados.")).toBeInTheDocument();
  });

  it("auto-selects and disables the select when there is exactly one patio", () => {
    const onChange = vi.fn();
    vi.mocked(usePatiosDisponibles).mockReturnValue({
      patios: [{ id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 }],
      loading: false,
    });

    render(<PatioSelect id="patio_id" value="" onChange={onChange} />);

    expect(onChange).toHaveBeenCalledWith("p1");
    expect(screen.getByRole("combobox")).toBeDisabled();
  });

  it("lets the user pick among multiple patios", async () => {
    const onChange = vi.fn();
    vi.mocked(usePatiosDisponibles).mockReturnValue({
      patios: [
        { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
        { id: "p2", nombre: "Patio Sur", codigo: "PS", activo: true, anticipacion_minima_horas: 24 },
      ],
      loading: false,
    });

    const user = userEvent.setup();
    render(<PatioSelect id="patio_id" value="" onChange={onChange} />);

    expect(screen.getByRole("combobox")).not.toBeDisabled();
    await user.selectOptions(screen.getByRole("combobox"), "p2");
    expect(onChange).toHaveBeenCalledWith("p2");
  });
});
