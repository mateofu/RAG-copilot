import { Redirect, Route, Switch } from "wouter";
import { lazy, Suspense } from "react";
import { LoginPage } from "../features/auth/presentation/LoginPage";
import { useSession } from "../features/auth/presentation/session-context";
import { AppShell } from "./AppShell";

const ConversationsPage = lazy(() =>
  import("../features/conversations/presentation/ConversationsPage").then(
    (module) => ({ default: module.ConversationsPage }),
  ),
);
const DocumentsPage = lazy(() =>
  import("../features/documents/presentation/DocumentsPage").then((module) => ({
    default: module.DocumentsPage,
  })),
);
const SearchPage = lazy(() =>
  import("../features/documents/presentation/SearchPage").then((module) => ({
    default: module.SearchPage,
  })),
);

export function App() {
  const { status } = useSession();
  if (status === "loading")
    return (
      <div className="app-loader" aria-label="Cargando sesión">
        <span />
      </div>
    );
  if (status === "anonymous") return <LoginPage />;

  return (
    <AppShell>
      <Suspense
        fallback={
          <div className="route-loader" role="status">
            <span className="spinner" />
            Cargando módulo…
          </div>
        }
      >
        <Switch>
          <Route path="/chat/:conversationId">
            {(params) => (
              <ConversationsPage conversationId={params.conversationId} />
            )}
          </Route>
          <Route path="/chat">
            <ConversationsPage />
          </Route>
          <Route path="/documents">
            <DocumentsPage />
          </Route>
          <Route path="/search">
            <SearchPage />
          </Route>
          <Route path="/login">
            <Redirect to="/chat" replace />
          </Route>
          <Route>
            <Redirect to="/chat" replace />
          </Route>
        </Switch>
      </Suspense>
    </AppShell>
  );
}
