import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { useState } from "react";
import { Modal } from "./Modal";

describe("Modal", () => {
  it("moves focus inside, closes with Escape and restores previous focus", async () => {
    const user = userEvent.setup();
    const close = vi.fn();
    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button onClick={() => setOpen(true)}>Launcher</button>
          {open && (
            <Modal
              titleId="title"
              onClose={() => {
                close();
                setOpen(false);
              }}
            >
              <h2 id="title">Dialog title</h2>
              <input aria-label="First field" />
            </Modal>
          )}
        </>
      );
    }
    render(<Harness />);
    const launcher = screen.getByRole("button", { name: "Launcher" });
    await user.click(launcher);

    expect(screen.getByRole("button", { name: "Cerrar" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(close).toHaveBeenCalledOnce();
    expect(launcher).toHaveFocus();
  });
});
