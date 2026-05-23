import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/hooks/use-theme";

export function Header() {
  const { theme, toggle } = useTheme();
  return (
    <header className="sticky top-0 z-30 border-b border-foreground/10 bg-background/40 backdrop-blur-2xl backdrop-saturate-150">
      <div className="mx-auto grid max-w-[1400px] grid-cols-3 items-center px-6 py-4 sm:px-10">
        <div className="text-sm font-medium tracking-tight uppercase">Taxxa AI</div>
        <div></div>
        <div className="flex items-center justify-end gap-6 text-sm">
          <span className="hidden font-mono text-xs text-muted-foreground sm:inline">
            HEL · FI · 2026
          </span>
          <button
            onClick={toggle}
            aria-label="Toggle theme"
            className="link-underline inline-flex items-center gap-1.5 text-xs uppercase tracking-wider"
          >
            {theme === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </div>
    </header>
  );
}
