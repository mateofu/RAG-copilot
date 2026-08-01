import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

function BrokenView(): never {
  throw new Error("render failed");
}

describe("ErrorBoundary", () => {
  beforeEach(() =>
    vi.spyOn(console, "error").mockImplementation(() => undefined),
  );

  it("contains an unhandled render failure and offers recovery", () => {
    render(
      <ErrorBoundary>
        <BrokenView />
      </ErrorBoundary>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "No pudimos mostrar esta pantalla",
    );
    expect(
      screen.getByRole("button", { name: "Recargar aplicación" }),
    ).toBeVisible();
  });
});
