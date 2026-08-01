import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ToastProvider } from "./ToastProvider";
import { useToast } from "./toast-context";

function Trigger() {
  const notify = useToast();
  return (
    <button onClick={() => notify("Documento listo", "success")}>Notify</button>
  );
}

describe("ToastProvider", () => {
  it("announces and dismisses notifications", async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Notify" }));
    expect(screen.getByRole("status")).toHaveTextContent("Documento listo");
    await user.click(
      screen.getByRole("button", { name: "Cerrar notificación" }),
    );
    expect(screen.queryByText("Documento listo")).not.toBeInTheDocument();
  });
});
