import { CheckCircle2, CircleAlert, Info, X } from "lucide-react";
import { useCallback, useMemo, useState, type PropsWithChildren } from "react";
import { ToastContext, type ToastKind } from "./toast-context";

type Toast = { id: number; message: string; kind: ToastKind };
const icons = { success: CheckCircle2, error: CircleAlert, info: Info };

export function ToastProvider({ children }: PropsWithChildren) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const notify = useCallback((message: string, kind: ToastKind = "info") => {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { id, message, kind }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 5000);
  }, []);
  const value = useMemo(() => notify, [notify]);
  const dismiss = (id: number) =>
    setToasts((current) => current.filter((toast) => toast.id !== id));

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="toast-region"
        aria-live="polite"
        aria-label="Notificaciones"
      >
        {toasts.map((toast) => {
          const Icon = icons[toast.kind];
          return (
            <div
              className={`toast ${toast.kind}`}
              key={toast.id}
              role={toast.kind === "error" ? "alert" : "status"}
            >
              <Icon size={18} />
              <span>{toast.message}</span>
              <button
                onClick={() => dismiss(toast.id)}
                aria-label="Cerrar notificación"
              >
                <X size={15} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
