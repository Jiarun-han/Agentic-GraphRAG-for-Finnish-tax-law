import { useMemo, useState } from "react";
import { Copy, Check, RefreshCw } from "lucide-react";
import type { Citation } from "@/lib/taxxa-api";

interface Props {
  answer: string;
  citations: Citation[];
  onAskAnother: () => void;
}

export function AnswerCard({ answer, citations, onAskAnother }: Props) {
  const [copied, setCopied] = useState(false);

  // Strip all [source_id] references from the answer text for clean display
  const cleanAnswer = useMemo(() => {
    let text = answer.replace(/\s*\[[^\]]+::[^\]]+\]\s*/g, " ").trim();
    // Ensure first letter is capitalized
    if (text.length > 0 && text[0] === text[0].toLowerCase()) {
      text = text[0].toUpperCase() + text.slice(1);
    }
    return text;
  }, [answer]);

  const copy = async () => {
    await navigator.clipboard.writeText(cleanAnswer);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <section className="glass glass-hover p-8 sm:p-12">
      <p className="text-lg font-light leading-relaxed text-foreground">
        {cleanAnswer}
      </p>

      <div className="mt-8 flex items-center gap-6 text-xs uppercase tracking-wider">
        <button onClick={copy} className="link-underline inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
        <button onClick={onAskAnother} className="link-underline inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
          <RefreshCw className="h-3.5 w-3.5" />
          Ask another
        </button>
      </div>
    </section>
  );
}
