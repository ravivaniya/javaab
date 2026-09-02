/**
 * Widget configuration — edit this file before deploying to a client.
 * All values can be overridden via environment variables (VITE_*).
 * See DEPLOYMENT.md for the full guide.
 */

export interface InstituteConfig {
  /** Display name shown in header and documents. */
  name: string;
  /** Absolute URL to the institute logo (PNG/SVG). Null = Javaab default logo. */
  logo_url: string | null;
  /** Brand primary colour — used for buttons, links, active states. Hex or CSS colour. */
  primary_color: string;
  /** Light tint of primary — used for chip/badge backgrounds. */
  secondary_color: string;
}

export interface WidgetDefaults {
  /** Default curriculum board pre-selected for students. */
  board: "CBSE" | "GSEB";
  /** Default class level (6–12). */
  class_level: number;
  /** Default UI language. */
  language: "en" | "hi" | "gu";
}

export interface FeatureFlags {
  /** Show the AI chat tab. */
  chat: boolean;
  /** Show the Question Paper Generator tab. */
  qpg: boolean;
  /** Show the Daily Practice Problem / DPP tab. */
  dpp: boolean;
}

export interface BrandingConfig {
  /** Show "Powered by Javaab" in the footer. Required by free-tier ToS; paid plans can disable. */
  show_javaab_credit: boolean;
}

export interface WidgetConfig {
  /** Base URL of the Javaab B2B API. */
  apiBaseUrl: string;
  /** Client's Javaab API key — sent as X-API-Key on every request. Never expose in public git. */
  apiKey: string;
  institute: InstituteConfig;
  defaults: WidgetDefaults;
  features: FeatureFlags;
  branding: BrandingConfig;
}

// ─── Runtime config (env vars override everything) ───────────────────────────

export const widgetConfig: WidgetConfig = {
  apiBaseUrl:
    import.meta.env.VITE_API_URL ||
    "https://api.javaab.ai",

  apiKey:
    import.meta.env.VITE_API_KEY || "",

  institute: {
    name:
      import.meta.env.VITE_INSTITUTE_NAME || "Javaab",
    logo_url:
      import.meta.env.VITE_LOGO_URL || null,
    primary_color:
      import.meta.env.VITE_PRIMARY_COLOR || "#FC8019",
    secondary_color:
      import.meta.env.VITE_SECONDARY_COLOR || "#FFF3E9",
  },

  defaults: {
    board:
      (import.meta.env.VITE_DEFAULT_BOARD as "CBSE" | "GSEB") || "CBSE",
    class_level:
      Number(import.meta.env.VITE_DEFAULT_CLASS) || 10,
    language:
      (import.meta.env.VITE_DEFAULT_LANGUAGE as "en" | "hi" | "gu") || "en",
  },

  features: {
    chat: import.meta.env.VITE_FEATURE_CHAT !== "false",
    qpg: import.meta.env.VITE_FEATURE_QPG === "true",
    dpp: import.meta.env.VITE_FEATURE_DPP === "true",
  },

  branding: {
    show_javaab_credit:
      import.meta.env.VITE_SHOW_JAVAAB_CREDIT !== "false",
  },
};

// ─── Demo-mode sandbox config (used by /demo route) ──────────────────────────

export const demoConfig: WidgetConfig = {
  ...widgetConfig,
  apiKey: import.meta.env.VITE_DEMO_API_KEY || widgetConfig.apiKey,
  institute: {
    ...widgetConfig.institute,
    name: "Demo Institute",
  },
  features: { chat: true, qpg: true, dpp: true },
  branding: { show_javaab_credit: true },
};
