import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import HomePage from "./page";

describe("HomePage", () => {
  it("renders the app name", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: "Patio Esperanza" })).toBeInTheDocument();
  });
});
