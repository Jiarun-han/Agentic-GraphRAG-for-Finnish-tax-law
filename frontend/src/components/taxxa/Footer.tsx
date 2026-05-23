export function Footer() {
  return (
    <footer id="about" className="mt-20 border-t border-foreground/10 bg-background/30 backdrop-blur-xl">
      <div className="mx-auto grid max-w-[1400px] grid-cols-12 gap-6 px-6 py-12 sm:px-10">
        <div className="col-span-12 sm:col-span-4">
          <div className="text-lg font-medium tracking-tight">Taxxa</div>
          <p className="mt-2 max-w-xs text-sm font-light text-muted-foreground">
            Agentic GraphRAG for Finnish tax and accounting research.
          </p>
        </div>
        <div className="col-span-6 sm:col-span-4">
          <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Corpus</div>
          <ul className="mt-3 space-y-1 text-sm">
            <li>Finlex</li>
            <li>Verohallinto</li>
          </ul>
        </div>
        <div className="col-span-6 sm:col-span-4">
          <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Built for</div>
          <ul className="mt-3 space-y-1 text-sm">
            <li>Prompt Finance Hackathon 2026</li>
            <li>Aalto University</li>
          </ul>
        </div>
        <div className="col-span-12 pt-6 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
          © 2026 · Helsinki · All rights reserved
        </div>
      </div>
    </footer>
  );
}
