import { Component, type ErrorInfo, type PropsWithChildren } from "react";
import { AlertTriangle } from "lucide-react";

type State = { failed: boolean };

export class ErrorBoundary extends Component<PropsWithChildren, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (import.meta.env.DEV) console.error("Unhandled UI error", error, info);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="fatal-error" role="alert">
        <div className="fatal-error-mark">
          <AlertTriangle />
        </div>
        <span className="eyebrow">Error inesperado</span>
        <h1>No pudimos mostrar esta pantalla</h1>
        <p>
          Tu información permanece segura. Recarga la aplicación para intentarlo
          nuevamente.
        </p>
        <button
          className="button primary"
          onClick={() => window.location.reload()}
        >
          Recargar aplicación
        </button>
      </main>
    );
  }
}
