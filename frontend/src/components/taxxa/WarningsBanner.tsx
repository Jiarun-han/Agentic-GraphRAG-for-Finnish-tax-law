interface Props {
  unverified?: string[];
  conflicts?: string[];
}

export function WarningsBanner({ unverified, conflicts }: Props) {
  const hasU = unverified && unverified.length > 0;
  const hasC = conflicts && conflicts.length > 0;
  if (!hasU && !hasC) return null;

  return (
    <div className="glass-subtle space-y-4 p-6">
      <div className="font-mono text-xs uppercase tracking-wider text-warning">
        Caveats
      </div>
      {hasU && (
        <div>
          <div className="text-sm font-medium">Unverified claims</div>
          <ul className="mt-2 space-y-1 text-sm font-light text-muted-foreground">
            {unverified!.map((u, i) => (
              <li key={i}><span className="mr-2 font-mono text-xs">—</span>{u}</li>
            ))}
          </ul>
        </div>
      )}
      {hasC && (
        <div>
          <div className="text-sm font-medium text-destructive">Conflicting sources</div>
          <ul className="mt-2 space-y-1 text-sm font-light text-muted-foreground">
            {conflicts!.map((c, i) => (
              <li key={i}><span className="mr-2 font-mono text-xs">—</span>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
