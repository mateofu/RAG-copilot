import { Redirect, Route, Switch } from "wouter";
import { LoginPage } from "../features/auth/presentation/LoginPage";
import { useSession } from "../features/auth/presentation/session-context";
import { ConversationsPage } from "../features/conversations/presentation/ConversationsPage";
import { DocumentsPage } from "../features/documents/presentation/DocumentsPage";
import { SearchPage } from "../features/documents/presentation/SearchPage";
import { AppShell } from "./AppShell";

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
    </AppShell>
  );
}
