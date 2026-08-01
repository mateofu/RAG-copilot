import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowRight,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { errorMessage } from "../../../core/http/api-error";
import { BrandLogo } from "../../../shared/components/BrandLogo";
import { useSession } from "./session-context";

const schema = z.object({
  email: z.email("Ingresa un correo válido."),
  password: z.string().min(1, "La contraseña es obligatoria."),
});
type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const { login } = useSession();
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function submit(values: FormValues) {
    setError(null);
    try {
      await login(values);
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  return (
    <main className="login-page">
      <section
        className="login-visual"
        aria-label="Documentos conectados mediante inteligencia semántica"
      >
        <div className="brand-row login-brand">
          <BrandLogo />
          <strong>RAG Copilot</strong>
        </div>
        <div className="login-visual-caption">
          <span>Conocimiento privado</span>
          <strong>Respuestas conectadas con evidencia.</strong>
        </div>
      </section>
      <section className="login-form-wrap">
        <form className="login-form" onSubmit={handleSubmit(submit)}>
          <div className="login-card-header">
            <span className="trust-badge">
              <ShieldCheck size={15} /> Espacio privado
            </span>
            <h1>Qué bueno verte</h1>
            <p>
              Ingresa para consultar tus documentos y continuar donde quedaste.
            </p>
          </div>
          {error && (
            <div className="inline-error" role="alert">
              {error}
            </div>
          )}
          <div className="login-field">
            <label htmlFor="login-email">Correo electrónico</label>
            <span className="login-input">
              <Mail size={18} />
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                placeholder="tu@empresa.com"
                {...register("email")}
              />
            </span>
            {errors.email && <small>{errors.email.message}</small>}
          </div>
          <div className="login-field">
            <label htmlFor="login-password">Contraseña</label>
            <span className="login-input">
              <LockKeyhole size={18} />
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                placeholder="••••••••"
                {...register("password")}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((visible) => !visible)}
                aria-label={
                  showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                }
                aria-pressed={showPassword}
              >
                {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </span>
            {errors.password && <small>{errors.password.message}</small>}
          </div>
          <button className="button primary wide" disabled={isSubmitting}>
            {isSubmitting ? (
              "Ingresando…"
            ) : (
              <>
                Ingresar <ArrowRight size={18} />
              </>
            )}
          </button>
          <p className="privacy-note">
            <ShieldCheck size={13} /> Tu sesión se guarda únicamente en esta
            pestaña.
          </p>
        </form>
      </section>
    </main>
  );
}
