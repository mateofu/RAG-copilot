import {
  BookOpenText,
  Building2,
  LogOut,
  Menu,
  MessageSquareText,
  Search,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type PropsWithChildren,
} from "react";
import { Link, useLocation } from "wouter";
import { useQueryClient } from "@tanstack/react-query";
import { useSession } from "../features/auth/presentation/session-context";
import { BrandLogo } from "../shared/components/BrandLogo";

const links = [
  { to: "/chat", label: "Copiloto", icon: MessageSquareText },
  { to: "/documents", label: "Documentos", icon: BookOpenText },
  { to: "/search", label: "Explorar", icon: Search },
];

export function AppShell({ children }: PropsWithChildren) {
  const [open, setOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const [location] = useLocation();
  const { identity, organization, selectOrganization, logout } = useSession();
  const queryClient = useQueryClient();

  const closeMobileMenu = useCallback(() => {
    setOpen(false);
    window.setTimeout(() => menuButtonRef.current?.focus());
  }, []);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeMobileMenu();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open, closeMobileMenu]);

  function changeOrganization(id: string) {
    selectOrganization(id);
    queryClient.clear();
  }

  return (
    <div className="app-frame">
      <button
        ref={menuButtonRef}
        className="mobile-menu"
        onClick={() => setOpen(true)}
        aria-label="Abrir menú"
        aria-expanded={open}
        aria-controls="application-sidebar"
      >
        <Menu />
      </button>
      {open && (
        <button
          className="sidebar-backdrop"
          onClick={closeMobileMenu}
          aria-label="Cerrar menú"
        />
      )}
      <aside
        id="application-sidebar"
        className={`sidebar ${open ? "sidebar-open" : ""}`}
      >
        <div className="brand-row">
          <BrandLogo />
          <div>
            <strong>RAG Copilot</strong>
            <span>Knowledge workspace</span>
          </div>
          <button
            className="close-menu"
            onClick={closeMobileMenu}
            aria-label="Cerrar menú"
          >
            <X />
          </button>
        </div>

        <div className="organization-select">
          <Building2 size={17} />
          <label>
            <span>Organización</span>
            <select
              value={organization?.organizationId ?? ""}
              onChange={(event) => changeOrganization(event.target.value)}
            >
              {identity?.memberships.map((item) => (
                <option key={item.organizationId} value={item.organizationId}>
                  {item.organizationName}
                </option>
              ))}
            </select>
          </label>
        </div>

        <nav aria-label="Navegación principal">
          {links.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              href={to}
              onClick={() => setOpen(false)}
              aria-current={location.startsWith(to) ? "page" : undefined}
              className={
                location.startsWith(to) ? "nav-link active" : "nav-link"
              }
            >
              <Icon size={19} />
              {label}
            </Link>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="avatar">
            {identity?.displayName.slice(0, 2).toUpperCase()}
          </div>
          <div className="user-copy">
            <strong>{identity?.displayName}</strong>
            <span>{organization?.role}</span>
          </div>
          <button
            className="icon-button"
            onClick={() => void logout()}
            title="Cerrar sesión"
            aria-label="Cerrar sesión"
          >
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
