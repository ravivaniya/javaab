import { describe, expect, it } from "vitest";
import { normalizeLatexDelimiters } from "./markdown-utils";

describe("normalizeLatexDelimiters", () => {
  it("converts common AI LaTeX delimiters to remark-math delimiters", () => {
    expect(normalizeLatexDelimiters(String.raw`Use \(x^2\) here.`)).toBe("Use $x^2$ here.");
    expect(normalizeLatexDelimiters(String.raw`Show \[\frac{a}{b}\] now.`)).toBe(
      "Show $$\\frac{a}{b}$$ now.",
    );
  });
});
