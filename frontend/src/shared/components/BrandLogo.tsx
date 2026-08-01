export function BrandLogo() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 32 32" fill="none">
        <path
          d="M8.5 5.5h10l5 5v16h-15z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path
          d="M18.5 5.5v5h5"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path
          d="m12 20 3.8-4 4.3 4.2M12 20l8.1.2"
          stroke="currentColor"
          strokeWidth="1.45"
          strokeLinecap="round"
        />
        <circle cx="12" cy="20" r="1.55" fill="currentColor" />
        <circle cx="15.8" cy="16" r="1.55" fill="currentColor" />
        <circle cx="20.1" cy="20.2" r="1.55" fill="currentColor" />
      </svg>
    </span>
  );
}
