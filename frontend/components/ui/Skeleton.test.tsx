import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Skeleton, SkeletonText } from "./Skeleton";

describe("Skeleton", () => {
  it("is decorative and does not announce loading on its own", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstElementChild).toHaveAttribute("aria-hidden", "true");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("accepts dimensions and radius", () => {
    const { container } = render(<Skeleton width="var(--space-12)" height="var(--space-8)" radius="var(--radius-lg)" />);
    expect(container.firstElementChild).toHaveStyle({
      width: "var(--space-12)", height: "var(--space-8)", borderRadius: "var(--radius-lg)",
    });
  });
});

describe("SkeletonText", () => {
  it("renders three decorative lines by default", () => {
    const { container } = render(<SkeletonText />);
    const text = container.firstElementChild;
    expect(text).toHaveAttribute("aria-hidden", "true");
    expect(text?.children).toHaveLength(3);
    for (const line of Array.from(text?.children ?? [])) {
      expect(line).toHaveAttribute("aria-hidden", "true");
    }
  });

  it.each([0, 1, 5])("renders %s requested lines", (lines) => {
    const { container } = render(<SkeletonText lines={lines} />);
    expect(container.firstElementChild?.children).toHaveLength(lines);
  });

  it.each([[-1, 0], [2.5, 2], [Infinity, 3], [NaN, 3]])(
    "handles a line count of %s as %s", (lines, expected) => {
      const { container } = render(<SkeletonText lines={lines} />);
      expect(container.firstElementChild?.children).toHaveLength(expected);
    }
  );
});
