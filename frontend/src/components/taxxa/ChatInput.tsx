import { useState, forwardRef } from "react";
import { ArrowUp } from "lucide-react";

interface Props {
  onAsk: (q: string) => void;
  loading: boolean;
  compact?: boolean;
}

export const ChatInput = forwardRef<HTMLDivElement, Props>(function ChatInput(
  { onAsk, loading, compact = false },
  ref,
) {
  const [value, setValue] = useState("");

  const submit = () => {
    const q = value.trim();
    if (!q || loading) return;
    onAsk(q);
    setValue("");
  };

  return (
    <div ref={ref} className={compact ? "glass-strong p-3 sm:p-4" : "glass-strong glass-hover p-6 sm:p-8"}>
      <div className="flex items-end gap-3">
        <textarea
          rows={compact ? 1 : 2}
          placeholder={compact ? "Ask a follow-up…" : "Ask a question about Finnish tax law…"}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          className={
            "flex-1 resize-none border-0 bg-transparent text-foreground placeholder:text-muted-foreground/60 focus:outline-none " +
            (compact
              ? "py-2 text-base font-light leading-snug"
              : "border-b border-foreground/20 pb-3 text-xl font-light leading-snug tracking-tight sm:text-2xl")
          }
        />
        <button
          onClick={submit}
          disabled={loading || !value.trim()}
          aria-label="Send"
          className="group inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-foreground/30 bg-foreground/5 backdrop-blur transition hover:bg-foreground hover:text-background disabled:opacity-40 disabled:hover:bg-foreground/5 disabled:hover:text-foreground"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </div>
      {!compact && (
        <div className="mt-3 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          ↵ to send · Shift + ↵ for new line
        </div>
      )}
    </div>
  );
});
