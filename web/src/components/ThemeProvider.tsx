import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ComponentProps } from "react";

type Props = ComponentProps<typeof NextThemesProvider>;

/**
 * App-wide theme provider. Persists choice in localStorage and respects the
 * system preference for first-time visitors. Toggles the `class="dark"` on
 * `<html>`, which Tailwind reads via the `darkMode: ["class"]` config.
 */
export function ThemeProvider({ children, ...props }: Props) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
      storageKey="javaab.theme"
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
}
