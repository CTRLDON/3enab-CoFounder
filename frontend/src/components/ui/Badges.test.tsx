import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { applyTheme } from "../../hooks/useVentureTheme";
import { EconomicBadge, EvidenceBadge, MockedLabel, OutcomeBadge } from "./Badges";

describe("labels", () => {
  it("never relies on colour alone", () => {
    render(<><EvidenceBadge value="ASSUMPTION" /><EvidenceBadge value="VERIFIED" compact /><EconomicBadge value="expense" /><OutcomeBadge outcome="STOP" /><MockedLabel /></>);
    expect(screen.getByText("ASSUMPTION")).toBeInTheDocument();
    expect(screen.getByText("VERIFIED")).toHaveClass("sr-only");
    expect(screen.getByText("Expense")).toBeInTheDocument();
    expect(screen.getByText("Stop")).toBeInTheDocument();
    expect(screen.getByText("MOCKED")).toBeInTheDocument();
  });

  it("applies and clears theme tokens as CSS variables", () => {
    applyTheme({ accent: "#123456" });
    expect(document.documentElement.style.getPropertyValue("--c-accent")).toBe("#123456");
    applyTheme(null);
    expect(document.documentElement.style.getPropertyValue("--c-accent")).toBe("");
  });
});
