export function BackgroundFX() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {/* Soft Apple-like aurora orbs */}
      <div className="absolute -top-40 -left-32 h-[55vw] w-[55vw] rounded-full opacity-40 blur-[120px] animate-float-slow"
        style={{ background: "radial-gradient(circle, oklch(0.7 0.18 250 / 0.55), transparent 60%)" }} />
      <div className="absolute top-1/3 -right-40 h-[50vw] w-[50vw] rounded-full opacity-35 blur-[140px] animate-float-slower"
        style={{ background: "radial-gradient(circle, oklch(0.75 0.16 320 / 0.5), transparent 60%)" }} />
      <div className="absolute bottom-0 left-1/4 h-[45vw] w-[45vw] rounded-full opacity-30 blur-[140px] animate-float-slow"
        style={{ background: "radial-gradient(circle, oklch(0.78 0.14 180 / 0.45), transparent 60%)" }} />
      {/* Subtle grain */}
      <div
        className="absolute inset-0 opacity-[0.05] mix-blend-overlay"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, currentColor 0 1px, transparent 1px 3px)",
        }}
      />
    </div>
  );
}
