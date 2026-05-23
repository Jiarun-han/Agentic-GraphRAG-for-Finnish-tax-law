export function AssumptionBadge({ assumption }: { assumption: string }) {
  return (
    <div className="glass-subtle p-6">
      <div className="mb-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
        Assumption
      </div>
      <div className="text-sm font-light text-foreground">{assumption}</div>
    </div>
  );
}
