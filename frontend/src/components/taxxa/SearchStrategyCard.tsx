interface Props {
  subQueries: string[];
  contextNodeCount: number;
}

export function SearchStrategyCard({ subQueries, contextNodeCount }: Props) {
  return (
    <section className="glass glass-hover p-6 sm:p-8">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          Analyzed {contextNodeCount} legal documents across {subQueries.length} search queries
        </span>
      </div>
    </section>
  );
}
