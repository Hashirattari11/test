// AutoFix brand logo — rounded square with the brand gradient + bolt.
// Replaces scattered inline "dot + text" logos.
type LogoProps = {
  size?: number;
  withWordmark?: boolean;
  className?: string;
};

export function LogoMark({ size = 32, withWordmark = false, className }: LogoProps) {
  return (
    <span className={className} style={{ display: "inline-flex", alignItems: "center", gap: 9 }}>
      <span
        aria-hidden="true"
        style={{
          width: size,
          height: size,
          borderRadius: Math.round(size * 0.28),
          background: "linear-gradient(135deg, #635bff 0%, #8b5cf6 55%, #06b6d4 130%)",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          boxShadow: "0 2px 8px rgba(99, 91, 255, 0.35)",
        }}
      >
        <svg width={size * 0.58} height={size * 0.58} viewBox="0 0 24 24" fill="none">
          <path
            d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"
            fill="#fff"
            stroke="#fff"
            strokeWidth="1"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      {withWordmark && (
        <span style={{ fontWeight: 800, fontSize: Math.round(size * 0.55), letterSpacing: "-0.01em", color: "inherit" }}>
          AutoFix API
        </span>
      )}
    </span>
  );
}