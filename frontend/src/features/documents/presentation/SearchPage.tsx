import { useQuery } from "@tanstack/react-query";
import { FileSearch, Search } from "lucide-react";
import { useState, type FormEvent } from "react";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../../shared/components/AsyncState";
import { PageHeader } from "../../../shared/components/PageHeader";
import { useSession } from "../../auth/presentation/session-context";
import { HttpDocumentRepository } from "../infrastructure/http-document-repository";

const repository = new HttpDocumentRepository();

export function SearchPage() {
  const { organization } = useSession();
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const results = useQuery({
    queryKey: ["search", organization?.organizationId, submitted],
    queryFn: () => repository.search(organization!.organizationId, submitted),
    enabled: Boolean(organization && submitted),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(query.trim());
  }
  return (
    <div className="page">
      <PageHeader
        eyebrow="Recuperación semántica"
        title="Explorar conocimiento"
        description="Encuentra los fragmentos más relevantes antes de conversar con el copiloto."
      />
      <form className="search-bar" onSubmit={submit}>
        <Search />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          minLength={1}
          maxLength={1000}
          placeholder="Busca conceptos, políticas o procedimientos…"
          aria-label="Consulta"
        />
        <button className="button primary" disabled={!query.trim()}>
          Buscar
        </button>
      </form>
      {!submitted ? (
        <div className="search-intro">
          <FileSearch />
          <h2>Busca en toda tu biblioteca</h2>
          <p>
            La búsqueda semántica encuentra contenido relacionado aunque no uses
            exactamente las mismas palabras.
          </p>
        </div>
      ) : results.isLoading ? (
        <LoadingState label="Buscando fragmentos…" />
      ) : results.isError ? (
        <ErrorState
          error={results.error}
          retry={() => void results.refetch()}
        />
      ) : !results.data?.length ? (
        <EmptyState
          title="Sin coincidencias"
          description="Prueba con otra pregunta o revisa que tus documentos estén disponibles."
        />
      ) : (
        <section className="search-results">
          <div className="results-heading">
            <span>{results.data.length} resultados para</span>
            <strong>“{submitted}”</strong>
          </div>
          {results.data.map((item, index) => (
            <article className="result-card" key={item.chunkId}>
              <div className="result-rank">
                {String(index + 1).padStart(2, "0")}
              </div>
              <div>
                <div className="result-meta">
                  <strong>{item.documentTitle}</strong>
                  <span>Página {item.pageNumber}</span>
                  <span>{Math.round(item.score * 100)}% relevancia</span>
                </div>
                <p>{item.content}</p>
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
