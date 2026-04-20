import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./i18n.ts";
import "@fontsource/noto-sans";
import "@fontsource/noto-sans-devanagari";
import "@fontsource/noto-sans-gujarati";
import "./index.css";

createRoot(document.getElementById("root")!).render(<App />);
