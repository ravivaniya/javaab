import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./i18n.ts";
import "@fontsource/noto-sans";
import "@fontsource/noto-sans-devanagari";
import "@fontsource/noto-sans-gujarati";
import "./index.css";
import { widgetConfig } from "./config/widget.config.ts";

/** Convert a hex colour (#RRGGBB) to "H S% L%" (for CSS custom properties). */
function hexToHslString(hex: string): string {
  const clean = hex.replace(/^#/, "");
  const r = parseInt(clean.slice(0, 2), 16) / 255;
  const g = parseInt(clean.slice(2, 4), 16) / 255;
  const b = parseInt(clean.slice(4, 6), 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
      case g: h = ((b - r) / d + 2) / 6; break;
      case b: h = ((r - g) / d + 4) / 6; break;
    }
  }
  return `${Math.round(h * 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`;
}

function applyBranding() {
  const { primary_color } = widgetConfig.institute;
  if (!primary_color.startsWith("#")) return; // skip if not a plain hex

  const hsl = hexToHslString(primary_color);
  const [h, s, l] = hsl.split(" "); // e.g. "24", "98%", "54%"
  const lightness = parseFloat(l);

  const root = document.documentElement;
  root.style.setProperty("--primary", hsl);
  root.style.setProperty("--ring", hsl);
  root.style.setProperty("--sidebar-primary", hsl);
  root.style.setProperty("--sidebar-ring", hsl);
  // Accent = very light tint of primary
  root.style.setProperty("--accent", `${h} ${s} ${Math.min(lightness + 42, 97)}%`);
  root.style.setProperty("--accent-foreground", `${h} ${s} ${Math.max(lightness - 24, 15)}%`);
}

applyBranding();

createRoot(document.getElementById("root")!).render(<App />);
