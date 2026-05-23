import { useState, forwardRef } from "react";
import { ArrowRight } from "lucide-react";

const EXAMPLES = [
  "What is the capital income tax rate for income exceeding 30,000 euros?",
  "What withholding tax rate applies to a foreign specialist with key-personnel status?",
  "What is the gift tax threshold in Finland?",
];

interface Props {
  onAsk: (q: string) => void;
  loading: boolean;
}

export const QuestionForm = forwardRef<HTMLDivElement, Props>(function QuestionForm(
  { onAsk, loading },
  ref,
) {
  const [value, setValue] = useState("");

  const submit = () => {
    const q = value.trim();
    if (!q || loading) return;
    onAsk(q);
  };

  return (
    <div ref={ref} id="ask" className="glass-strong glass-hover p-8 sm:p-12">
      <textarea
        rows={3}
        placeholder="Ask a question about Finnish tax law…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
        }}
        className="w-full resize-none border-0 border-b border-foreground/20 bg-transparent pb-3 text-2xl font-light leading-snug tracking-tight text-foreground placeholder:text-muted-foreground/60 transition-colors focus:border-foreground focus:outline-none sm:text-3xl"
      />

      <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-3">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => setValue(ex)}
            className="link-underline text-left text-xs text-muted-foreground hover:text-foreground"
          >
            {ex}
          </button>
        ))}
      </div>

      <div className="mt-8 flex items-center justify-between">
        <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
          {loading ? (
            <span className="inline-flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-foreground animate-pulse-dot" />
              Analyzing sources<span className="animate-caret">▍</span>
            </span>
          ) : (
            <>⌘ + ↵ to submit</>
          )}
        </div>
        <button
          onClick={submit}
          disabled={loading || !value.trim()}
          className="group inline-flex items-center gap-3 text-sm font-medium tracking-tight disabled:opacity-40"
        >
          <span className="link-underline">{loading ? "Asking" : "Ask"}</span>
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-foreground/30 bg-foreground/5 backdrop-blur transition group-hover:bg-foreground group-hover:text-background">
            <ArrowRight className="h-4 w-4" />
          </span>
        </button>
      </div>
    </div>
  );
});
