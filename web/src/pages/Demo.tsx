import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { widgetConfig, demoConfig } from "@/config/widget.config";
import { Logo } from "@/components/brand/Logo";

/**
 * /demo — sales demo mode.
 * Temporarily overrides the widget config with the demoConfig sandbox key,
 * so prospects can try the full widget during a call without seeing the real API key.
 *
 * This page is always accessible regardless of feature flags.
 */

// Apply demo branding CSS vars while on /demo
function applyDemoVars() {
  const root = document.documentElement;
  root.style.setProperty("--primary", "24 98% 54%"); // Javaab orange always in demo
  root.style.setProperty("--ring", "24 98% 54%");
}

export default function Demo() {
  const navigate = useNavigate();
  const [entered, setEntered] = useState(false);
  const [activeFeature, setActiveFeature] = useState<"chat" | "qpg" | "dpp">("chat");

  const hasDemoKey = !!demoConfig.apiKey;

  function startDemo(feature: "chat" | "qpg" | "dpp") {
    // Patch global config for the session (no page reload needed)
    widgetConfig.apiKey = demoConfig.apiKey;
    widgetConfig.institute.name = "Demo Institute";
    widgetConfig.features.chat = true;
    widgetConfig.features.qpg = true;
    widgetConfig.features.dpp = true;
    widgetConfig.branding.show_javaab_credit = true;
    applyDemoVars();
    setEntered(true);
    setActiveFeature(feature);
    navigate(feature === "chat" ? "/chat" : feature === "qpg" ? "/question-paper" : "/dpp");
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-lg space-y-8">
        {/* Header */}
        <div className="text-center space-y-3">
          <Logo className="justify-center" />
          <h1 className="font-display text-3xl font-black tracking-tight text-foreground">
            Widget Demo
          </h1>
          <p className="text-muted-foreground text-sm leading-relaxed max-w-sm mx-auto">
            Try the full Javaab B2B widget experience. This sandbox uses a demo
            API key — no credits are consumed.
          </p>
        </div>

        {!hasDemoKey && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800">
            <strong>Demo API key not configured.</strong> Set{" "}
            <code className="font-mono text-xs bg-amber-100 px-1 py-0.5 rounded">
              VITE_DEMO_API_KEY
            </code>{" "}
            in your .env to enable this page.
          </div>
        )}

        {/* Feature cards */}
        <div className="grid gap-4">
          <DemoCard
            emoji="💬"
            title="AI Chat"
            description="NCERT & GSEB curriculum-aligned Q&A with SSE streaming. Try asking about Chapter 1 of Class 10 Science."
            disabled={!hasDemoKey}
            onStart={() => startDemo("chat")}
          />
          <DemoCard
            emoji="📄"
            title="Question Paper Generator"
            description="Generate a full question paper in under 60 seconds. Multiple sets, difficulty control, auto marking scheme."
            disabled={!hasDemoKey}
            onStart={() => startDemo("qpg")}
          />
          <DemoCard
            emoji="📝"
            title="Daily Practice Problems"
            description="Generate chapter-specific DPPs, worksheets, and MCQ drills with answer keys."
            disabled={!hasDemoKey}
            onStart={() => startDemo("dpp")}
          />
        </div>

        {/* Footer note */}
        <p className="text-center text-xs text-muted-foreground">
          Demo mode · Powered by <span className="font-semibold">Javaab</span>
        </p>
      </div>
    </div>
  );
}

function DemoCard({
  emoji,
  title,
  description,
  disabled,
  onStart,
}: {
  emoji: string;
  title: string;
  description: string;
  disabled: boolean;
  onStart: () => void;
}) {
  return (
    <div className="rounded-3xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-start gap-4">
        <span className="text-3xl">{emoji}</span>
        <div className="flex-1 min-w-0">
          <h3 className="font-display font-bold text-lg text-foreground">{title}</h3>
          <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{description}</p>
        </div>
      </div>
      <div className="mt-4 flex justify-end">
        <button
          onClick={onStart}
          disabled={disabled}
          className="inline-flex items-center gap-2 bg-primary text-primary-foreground rounded-full font-bold px-5 py-2 text-sm hover:opacity-90 hover:-translate-y-0.5 transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:translate-y-0"
        >
          Try {title} →
        </button>
      </div>
    </div>
  );
}
