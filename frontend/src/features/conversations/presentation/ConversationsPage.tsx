import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUp, FileText, MessageSquarePlus, Sparkles } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useLocation } from "wouter";
import { errorMessage } from "../../../core/http/api-error";
import {
  ErrorState,
  LoadingState,
} from "../../../shared/components/AsyncState";
import { formatDate } from "../../../shared/format";
import { useSession } from "../../auth/presentation/session-context";
import type { Citation } from "../domain/conversation";
import { HttpConversationRepository } from "../infrastructure/http-conversation-repository";

const repository = new HttpConversationRepository();
const suggestions = [
  "Resume los puntos principales de los documentos",
  "¿Qué políticas importantes debo conocer?",
  "Encuentra información sobre plazos y fechas",
];

export function ConversationsPage({
  conversationId,
}: {
  conversationId?: string;
}) {
  const [, navigate] = useLocation();
  const queryClient = useQueryClient();
  const { organization } = useSession();
  const organizationId = organization?.organizationId ?? "";
  const [question, setQuestion] = useState("");
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const conversations = useQuery({
    queryKey: ["conversations", organizationId],
    queryFn: () => repository.list(organizationId),
    enabled: Boolean(organizationId),
  });
  const detail = useQuery({
    queryKey: ["conversation", organizationId, conversationId],
    queryFn: () => repository.get(organizationId, conversationId!),
    enabled: Boolean(organizationId && conversationId),
  });
  const ask = useMutation({
    mutationFn: (value: string) =>
      repository.ask(organizationId, value, conversationId),
    onMutate: (value) => setPendingQuestion(value),
    onSuccess: async (answer) => {
      setQuestion("");
      if (!conversationId)
        navigate(`/chat/${answer.conversationId}`, { replace: true });
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["conversations", organizationId],
        }),
        queryClient.invalidateQueries({
          queryKey: ["conversation", organizationId, answer.conversationId],
        }),
      ]);
    },
    onSettled: () => setPendingQuestion(null),
  });
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [detail.data?.messages.length, pendingQuestion]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const value = question.trim();
    if (value && !ask.isPending) ask.mutate(value);
  }
  function newConversation() {
    setQuestion("");
    setPendingQuestion(null);
    navigate("/chat");
  }

  return (
    <div className="chat-layout">
      <aside className="conversation-list">
        <div className="conversation-list-head">
          <div>
            <span className="eyebrow">Historial</span>
            <strong>Conversaciones</strong>
          </div>
          <button
            className="icon-button filled"
            onClick={newConversation}
            title="Nueva conversación"
          >
            <MessageSquarePlus size={18} />
          </button>
        </div>
        {conversations.isLoading ? (
          <LoadingState />
        ) : conversations.isError ? (
          <ErrorState error={conversations.error} />
        ) : (
          <div className="conversation-items">
            {conversations.data?.map((item) => (
              <button
                key={item.conversationId}
                onClick={() => navigate(`/chat/${item.conversationId}`)}
                className={
                  item.conversationId === conversationId
                    ? "conversation-item selected"
                    : "conversation-item"
                }
              >
                <strong>{item.title}</strong>
                <span>
                  {item.messageCount} mensajes · {formatDate(item.updatedAt)}
                </span>
              </button>
            ))}
            {!conversations.data?.length && (
              <p className="muted-copy">Aún no tienes conversaciones.</p>
            )}
          </div>
        )}
      </aside>
      <section className="chat-main">
        <header className="chat-header">
          <div>
            <span className="online-dot" />
            Copiloto disponible
          </div>
          <span>{organization?.organizationName}</span>
        </header>
        <div className="messages" aria-live="polite">
          {!conversationId && !pendingQuestion ? (
            <Welcome onSuggestion={setQuestion} />
          ) : detail.isLoading && conversationId ? (
            <LoadingState label="Cargando conversación…" />
          ) : detail.isError ? (
            <ErrorState
              error={detail.error}
              retry={() => void detail.refetch()}
            />
          ) : (
            <>
              {detail.data?.messages.map((message) => (
                <article
                  key={message.messageId}
                  className={`message ${message.role}`}
                >
                  <div className="message-avatar">
                    {message.role === "assistant" ? (
                      <Sparkles size={17} />
                    ) : (
                      "Tú"
                    )}
                  </div>
                  <div className="message-content">
                    <span>
                      {message.role === "assistant" ? "RAG Copilot" : "Tú"}
                    </span>
                    <p>{message.content}</p>
                    {message.citations.length > 0 && (
                      <CitationList citations={message.citations} />
                    )}
                  </div>
                </article>
              ))}
              {pendingQuestion && (
                <>
                  <article className="message user">
                    <div className="message-avatar">Tú</div>
                    <div className="message-content">
                      <span>Tú</span>
                      <p>{pendingQuestion}</p>
                    </div>
                  </article>
                  <article className="message assistant">
                    <div className="message-avatar">
                      <Sparkles size={17} />
                    </div>
                    <div className="message-content">
                      <span>RAG Copilot</span>
                      <div className="thinking">
                        <i />
                        <i />
                        <i />
                      </div>
                    </div>
                  </article>
                </>
              )}
            </>
          )}
          <div ref={bottomRef} />
        </div>
        <div className="composer-wrap">
          {ask.isError && (
            <div className="composer-error">{errorMessage(ask.error)}</div>
          )}
          <form className="composer" onSubmit={submit}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              rows={1}
              maxLength={4000}
              placeholder="Pregunta sobre tus documentos…"
              aria-label="Pregunta"
            />
            <button
              aria-label="Enviar pregunta"
              disabled={!question.trim() || ask.isPending}
            >
              <ArrowUp />
            </button>
          </form>
          <p>
            Las respuestas pueden contener errores. Verifica siempre las citas.
          </p>
        </div>
      </section>
    </div>
  );
}

function Welcome({ onSuggestion }: { onSuggestion: (value: string) => void }) {
  return (
    <div className="welcome">
      <div className="welcome-mark">
        <Sparkles />
      </div>
      <span className="eyebrow">Tu conocimiento, listo para conversar</span>
      <h1>¿Qué quieres descubrir hoy?</h1>
      <p>
        Consulta tus documentos en lenguaje natural. Cada respuesta incluirá las
        fuentes utilizadas.
      </p>
      <div className="suggestions">
        {suggestions.map((item) => (
          <button key={item} onClick={() => onSuggestion(item)}>
            {item}
            <ArrowUp size={16} />
          </button>
        ))}
      </div>
    </div>
  );
}

function CitationList({ citations }: { citations: Citation[] }) {
  return (
    <div className="citations">
      <span>Fuentes consultadas</span>
      {citations.map((citation) => (
        <details key={`${citation.documentId}-${citation.index}`}>
          <summary>
            <FileText size={15} />
            <strong>
              [{citation.index}] {citation.documentTitle}
            </strong>
            <span>Pág. {citation.pageNumber}</span>
          </summary>
          <p>{citation.content}</p>
        </details>
      ))}
    </div>
  );
}
