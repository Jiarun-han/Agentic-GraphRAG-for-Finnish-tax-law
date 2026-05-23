import type { Citation } from "@/lib/taxxa-api";
import { ExternalLink } from "lucide-react";

function publisherIcon(sourceId: string): string {
  const id = sourceId.toLowerCase();
  if (id.startsWith("finlex")) return "📜";
  if (id.startsWith("vero")) return "🏛️";
  return "📄";
}

function publisherLabel(sourceId: string): string {
  const id = sourceId.toLowerCase();
  if (id.startsWith("finlex")) return "Finlex (Finnish Law)";
  if (id.startsWith("vero")) return "Verohallinto (Tax Admin)";
  return "Source";
}

export function CitationsCard({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;

  return (
    <section className="glass glass-hover p-6 sm:p-8">
      <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-muted-foreground">
        Sources
      </h2>
      <ul className="space-y-3">
        {citations.map((c, i) => (
          <li
            key={`${c.source_id}-${i}`}
            id={`cite-${c.source_id}`}
            className="glass-subtle p-4 rounded-md"
          >
            <div className="flex items-start gap-3">
              <span className="text-base mt-0.5">{publisherIcon(c.source_id)}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium leading-snug truncate">
                  {c.doc_title}
                </div>
                {c.section && (
                  <div className="mt-0.5 text-xs text-muted-foreground">
                    § {c.section}
                  </div>
                )}
                <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{publisherLabel(c.source_id)}</span>
                  {c.url && (
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 hover:text-foreground transition-colors"
                    >
                      <ExternalLink className="h-3 w-3" />
                      View source
                    </a>
                  )}
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
