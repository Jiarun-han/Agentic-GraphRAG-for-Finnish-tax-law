import { Sparkles } from "lucide-react";

interface Props {
  question?: string;
}

const STEPS = [
  "Parsing your question",
  "Searching Finlex & Verohallinto",
  "Traversing knowledge graph",
  "Synthesizing grounded answer",
];

export function ThinkingIndicator({ question }: Props) {
  return (
    <div className="mt-8 space-y-6 animate-fade-up">
      {question && (
        <div className="flex justify-end">
          <div className="glass-subtle max-w-[80%] px-5 py-3 text-base font-light leading-snug">
            {question}
          </div>
        </div>
      )}

      <div className="flex items-start gap-4">
        <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full glass-subtle">
          <Sparkles className="h-4 w-4 animate-pulse-dot" />
          <span className="absolute inset-0 rounded-full border border-foreground/20 animate-ping-slow" />
        </div>

        <div className="glass-subtle flex-1 px-6 py-5">
          <div className="flex items-center gap-2 text-sm font-light text-foreground">
            <span>Thinking</span>
            <span className="inline-flex gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-foreground animate-bounce-dot [animation-delay:-0.32s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-foreground animate-bounce-dot [animation-delay:-0.16s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-foreground animate-bounce-dot" />
            </span>
          </div>

          <ul className="mt-4 space-y-2 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {STEPS.map((s, i) => (
              <li
                key={s}
                className="flex items-center gap-2 animate-fade-up"
                style={{ animationDelay: `${i * 0.6}s` }}
              >
                <span className="h-1 w-1 rounded-full bg-foreground/60" />
                {s}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
