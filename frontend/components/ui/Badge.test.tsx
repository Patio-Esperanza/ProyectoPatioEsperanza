import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "./Badge";

describe("Badge", () => {
  it("renders its text with the default tone", () => {
    render(<Badge>Sin asignar</Badge>);
    expect(screen.getByText("Sin asignar")).toBeVisible();
  });

  it.each(["neutral", "info", "success", "warning", "danger"] as const)(
    "keeps meaningful text in the %s tone", (tone) => {
      render(<Badge tone={tone}>En patio</Badge>);
      expect(screen.getByText("En patio")).toBeVisible();
    }
  );
});
