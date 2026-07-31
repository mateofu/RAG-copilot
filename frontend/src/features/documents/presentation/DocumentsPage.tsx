import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Plus, RefreshCw, UploadCloud, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { errorMessage } from "../../../core/http/api-error";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../../shared/components/AsyncState";
import { PageHeader } from "../../../shared/components/PageHeader";
import { formatBytes, formatDate } from "../../../shared/format";
import { useSession } from "../../auth/presentation/session-context";
import { HttpDocumentRepository } from "../infrastructure/http-document-repository";

const repository = new HttpDocumentRepository();
const statusLabel = {
  pending: "Pendiente",
  processing: "Procesando",
  ready: "Disponible",
  failed: "Falló",
};

export function DocumentsPage() {
  const { organization } = useSession();
  const organizationId = organization?.organizationId ?? "";
  const [uploadOpen, setUploadOpen] = useState(false);
  const queryClient = useQueryClient();
  const documents = useQuery({
    queryKey: ["documents", organizationId],
    queryFn: () => repository.list(organizationId),
    enabled: Boolean(organizationId),
    refetchInterval: 10_000,
  });
  const upload = useMutation({
    mutationFn: ({ title, file }: { title: string; file: File }) =>
      repository.upload(organizationId, title, file),
    onSuccess: async () => {
      setUploadOpen(false);
      await queryClient.invalidateQueries({
        queryKey: ["documents", organizationId],
      });
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const file = data.get("file");
    if (!(file instanceof File) || !file.size) return;
    upload.mutate({ title: String(data.get("title") ?? ""), file });
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Biblioteca"
        title="Documentos"
        description="Administra las fuentes que alimentan las respuestas de tu copiloto."
        action={
          <button
            className="button primary"
            onClick={() => setUploadOpen(true)}
          >
            <Plus size={18} />
            Subir documento
          </button>
        }
      />
      <div className="metric-strip">
        <div>
          <span>Total</span>
          <strong>{documents.data?.total ?? "—"}</strong>
        </div>
        <div>
          <span>Disponibles</span>
          <strong>
            {documents.data?.items.filter((item) => item.status === "ready")
              .length ?? "—"}
          </strong>
        </div>
        <button
          className="button ghost"
          onClick={() => void documents.refetch()}
        >
          <RefreshCw size={16} />
          Actualizar
        </button>
      </div>
      {documents.isLoading ? (
        <LoadingState label="Cargando documentos…" />
      ) : documents.isError ? (
        <ErrorState
          error={documents.error}
          retry={() => void documents.refetch()}
        />
      ) : !documents.data?.items.length ? (
        <EmptyState
          title="Tu biblioteca está vacía"
          description="Sube un PDF para comenzar a consultar su contenido."
        />
      ) : (
        <div className="document-grid">
          {documents.data.items.map((document) => (
            <article className="document-card" key={document.documentId}>
              <div className="file-icon">
                <FileText />
              </div>
              <div className="document-body">
                <div className="document-title-row">
                  <h2>{document.title}</h2>
                  <span className={`status ${document.status}`}>
                    {statusLabel[document.status]}
                  </span>
                </div>
                <p>{document.originalFilename}</p>
                <dl>
                  <div>
                    <dt>Tamaño</dt>
                    <dd>{formatBytes(document.sizeBytes)}</dd>
                  </div>
                  <div>
                    <dt>Versión</dt>
                    <dd>v{document.versionNumber}</dd>
                  </div>
                  <div>
                    <dt>Creado</dt>
                    <dd>{formatDate(document.createdAt)}</dd>
                  </div>
                </dl>
              </div>
            </article>
          ))}
        </div>
      )}
      {uploadOpen && (
        <div className="modal-layer" role="presentation">
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="upload-title"
          >
            <button
              className="modal-close"
              onClick={() => setUploadOpen(false)}
              aria-label="Cerrar"
            >
              <X />
            </button>
            <div className="upload-mark">
              <UploadCloud />
            </div>
            <h2 id="upload-title">Subir documento</h2>
            <p>
              El PDF se procesará localmente y estará disponible al terminar la
              indexación.
            </p>
            <form onSubmit={submit}>
              <label>
                Título
                <input
                  name="title"
                  required
                  maxLength={240}
                  placeholder="Ej. Manual de vacaciones"
                />
              </label>
              <label>
                Archivo PDF
                <input
                  name="file"
                  type="file"
                  required
                  accept="application/pdf,.pdf"
                />
              </label>
              {upload.isError && (
                <div className="inline-error">{errorMessage(upload.error)}</div>
              )}
              <div className="modal-actions">
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => setUploadOpen(false)}
                >
                  Cancelar
                </button>
                <button className="button primary" disabled={upload.isPending}>
                  {upload.isPending ? "Subiendo…" : "Subir PDF"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
