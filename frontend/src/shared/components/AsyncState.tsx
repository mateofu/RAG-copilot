import { AlertCircle, Inbox } from "lucide-react";
import { errorMessage } from "../../core/http/api-error";

export function LoadingState({ label = "Cargando…" }: { label?: string }) {
  return (
    <div className="state-panel" role="status">
      <span className="spinner" />
      {label}
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: unknown;
  retry?: () => void;
}) {
  return (
    <div className="state-panel error" role="alert">
      <AlertCircle />
      <strong>No pudimos completar la solicitud</strong>
      <p>{errorMessage(error)}</p>
      {retry && (
        <button className="button secondary" onClick={retry}>
          Reintentar
        </button>
      )}
    </div>
  );
}
export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="state-panel">
      <Inbox />
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  );
}
