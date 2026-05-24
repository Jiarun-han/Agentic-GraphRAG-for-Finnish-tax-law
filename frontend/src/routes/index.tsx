import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Toaster, toast } from "sonner";
import { askTaxxa, type TaxxaResponse } from "@/lib/taxxa-api";
import { Header } from "@/components/taxxa/Header";
import { ChatInput } from "@/components/taxxa/ChatInput";
import { AnswerCard } from "@/components/taxxa/AnswerCard";
import { CitationsCard } from "@/components/taxxa/CitationsCard";
import { SearchStrategyCard } from "@/components/taxxa/SearchStrategyCard";
import { WarningsBanner } from "@/components/taxxa/WarningsBanner";
import { AssumptionBadge } from "@/components/taxxa/AssumptionBadge";
import { Footer } from "@/components/taxxa/Footer";
import { BackgroundFX } from "@/components/taxxa/BackgroundFX";
import { ThinkingIndicator } from "@/components/taxxa/ThinkingIndicator";

export const Route = createFileRoute("/")({
  component: Index,
});

interface Turn {
  id: number;
  question: string;
  data?: TaxxaResponse;
  error?: string;
  pending: boolean;
}

const EXAMPLES = [
  "What is the capital income tax rate for income exceeding 30,000 euros?",
  "What withholding tax rate applies to a foreign specialist with key-personnel status?",
  "What is the gift tax threshold in Finland?",
];

function Index() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const pending = turns.some((t) => t.pending);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  const handleAsk = async (q: string) => {
    const id = Date.now();
    setTurns((prev) => [...prev, { id, question: q, pending: true }]);
    try {
      const data = await askTaxxa(q);
      setTurns((prev) =>
        prev.map((t) => (t.id === id ? { ...t, data, pending: false } : t)),
      );
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Request failed";
      toast.error(msg);
      setTurns((prev) =>
        prev.map((t) => (t.id === id ? { ...t, error: msg, pending: false } : t)),
      );
    }
  };

  const isEmpty = turns.length === 0;

  return (
    <div className="relative min-h-screen bg-background text-foreground">
      <BackgroundFX />
      <Toaster position="top-right" theme="dark" />
      <Header />

      {isEmpty ? (
        <main className="mx-auto max-w-[1100px] px-6 sm:px-10">
          <section className="py-16 sm:py-24">
            <h1 className="text-center text-[12vw] font-light leading-[0.95] tracking-[-0.04em] sm:text-[6.5vw] animate-fade-up uppercase">
              Finnish tax law,
              <br />
              <span className="italic text-muted-foreground">researched &amp; cited.</span>
            </h1>
          </section>

          <ChatInput onAsk={handleAsk} loading={pending} />

          <section className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 animate-fade-up">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => handleAsk(ex)}
                className="link-underline text-left text-xs text-muted-foreground hover:text-foreground"
              >
                {ex}
              </button>
            ))}
          </section>

          <section className="mt-12 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between animate-fade-up">
            <p className="max-w-md text-sm font-light leading-relaxed text-muted-foreground">
              An agentic GraphRAG system over Finlex and Verohallinto.
              Every answer is grounded in primary sources, traced and verifiable.
            </p>
            <div className="sm:text-right">
              <div className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                Demo · Hackathon 2026
              </div>
              <div className="mt-1 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                GraphRAG · DeepSeek
              </div>
            </div>
          </section>

          <div className="h-32" />
          <Footer />
        </main>
      ) : (
        <div className="flex min-h-[calc(100vh-4rem)] flex-col">
          {/* Messages */}
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-[900px] px-4 py-10 sm:px-8">
              <div className="space-y-10">
                {turns.map((turn) => (
                  <ChatTurn key={turn.id} turn={turn} />
                ))}
                <div ref={bottomRef} />
              </div>
            </div>
          </main>

          {/* Sticky input */}
          <div className="sticky bottom-0 z-20 bg-gradient-to-t from-background via-background/90 to-transparent pb-6 pt-8">
            <div className="mx-auto max-w-[900px] px-4 sm:px-8">
              <ChatInput onAsk={handleAsk} loading={pending} compact />
              <div className="mt-2 text-center font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                Taxxa can be wrong. Always verify with primary sources.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ChatTurn({ turn }: { turn: Turn }) {
  return (
    <div className="space-y-6">
      {/* User bubble */}
      <div className="flex justify-end animate-fade-up">
        <div className="glass-subtle max-w-[80%] px-5 py-3 text-lg font-light leading-snug">
          {turn.question}
        </div>
      </div>

      {/* Assistant */}
      {turn.pending && <ThinkingIndicator />}

      {turn.error && (
        <div className="glass-subtle p-6 animate-fade-up">
          <div className="text-sm font-medium text-destructive">{turn.error}</div>
          <div className="mt-1 text-xs font-light text-muted-foreground">
            Check that the API is running at{" "}
            <code className="font-mono">
              {import.meta.env.VITE_API_URL || "http://localhost:8000"}
            </code>
            .
          </div>
        </div>
      )}

      {turn.data && (
        <div className="stagger space-y-4">
          {turn.data.assumption && <AssumptionBadge assumption={turn.data.assumption} />}
          <WarningsBanner
            unverified={turn.data.unverified_claims}
            conflicts={turn.data.conflicts}
          />
          <AnswerCard
            answer={turn.data.answer}
            citations={turn.data.citations}
            onAskAnother={() => {}}
          />
          {turn.data.citations.length > 0 && (
            <CitationsCard citations={turn.data.citations} />
          )}
          {/* Reasoning transparency */}
          <details className="glass-subtle p-4 rounded-md text-sm">
            <summary className="cursor-pointer text-muted-foreground font-medium">
              Show reasoning · {turn.data.context_node_count} documents analyzed · {turn.data.sub_queries.length} search queries
            </summary>
            <div className="mt-3 space-y-2">
              <div>
                <span className="text-xs uppercase tracking-wider text-muted-foreground">Search strategy:</span>
                <div className="mt-1 flex flex-wrap gap-2">
                  {turn.data.sub_queries.map((q, i) => (
                    <span key={i} className="inline-block px-2 py-1 text-xs bg-foreground/5 rounded">{q}</span>
                  ))}
                </div>
              </div>
              {turn.data.confidence_label && (
                <div className="text-xs text-muted-foreground">
                  Confidence: <span className="font-medium text-foreground">{turn.data.confidence_label}</span>
                </div>
              )}
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
