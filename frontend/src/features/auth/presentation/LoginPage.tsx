import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, CheckCircle2, LockKeyhole } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { errorMessage } from "../../../core/http/api-error";
import { useSession } from "./session-context";

const schema = z.object({
  email: z.email("Ingresa un correo válido."),
  password: z.string().min(1, "La contraseña es obligatoria."),
});
type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const { login } = useSession();
  const [error, setError] = useState<string | null>(null);
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
      <section className="login-story">
        <div className="brand-row login-brand">
          <div className="brand-mark">R</div>
          <strong>RAG Copilot</strong>
        </div>
        <div className="story-content">
          <span className="eyebrow light">Inteligencia documental privada</span>
          <h1>
            Pregunta con confianza.
            <br />
            Responde con evidencia.
          </h1>
          <p>
            Convierte tus documentos en conocimiento consultable, manteniendo
            cada respuesta conectada con su fuente original.
          </p>
          <ul>
            <li>
              <CheckCircle2 />
              Modelos locales, sin costo por consulta
            </li>
            <li>
              <CheckCircle2 />
              Aislamiento seguro entre organizaciones
            </li>
            <li>
              <CheckCircle2 />
              Citas verificables por página y documento
            </li>
          </ul>
        </div>
        <p className="story-footer">
          Tus documentos permanecen bajo tu control.
        </p>
      </section>
      <section className="login-form-wrap">
        <form className="login-form" onSubmit={handleSubmit(submit)}>
          <div className="login-icon">
            <LockKeyhole />
          </div>
          <span className="eyebrow">Acceso seguro</span>
          <h2>Bienvenido de nuevo</h2>
          <p>Ingresa a tu espacio de conocimiento.</p>
          {error && (
            <div className="inline-error" role="alert">
              {error}
            </div>
          )}
          <label>
            Correo electrónico
            <input
              type="email"
              autoComplete="email"
              placeholder="tu@empresa.com"
              {...register("email")}
            />
            {errors.email && <small>{errors.email.message}</small>}
          </label>
          <label>
            Contraseña
            <input
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              {...register("password")}
            />
            {errors.password && <small>{errors.password.message}</small>}
          </label>
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
            La sesión se conserva únicamente en esta pestaña.
          </p>
        </form>
      </section>
    </main>
  );
}
