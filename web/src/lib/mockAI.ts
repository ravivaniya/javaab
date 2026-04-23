/**
 * Deterministic mocked AI replies for Phase-2 prototype.
 * Picks a response template based on keywords, mixes in markdown + LaTeX.
 */

import type { Confidence } from "./chat";

export interface MockReply {
  content: string;
  confidence: Confidence;
  source?: { book: string; chapter: string };
}

const TEMPLATES: Array<{ match: RegExp; reply: MockReply }> = [
  {
    match: /photosynth/i,
    reply: {
      content:
        `**Photosynthesis** is the process by which green plants convert light energy into chemical energy.\n\n` +
        `### The overall reaction\n\n` +
        `$$6\\,CO_2 + 6\\,H_2O \\xrightarrow{\\text{light}} C_6H_{12}O_6 + 6\\,O_2$$\n\n` +
        `**Steps:**\n` +
        `1. Light is absorbed by **chlorophyll** in the chloroplasts.\n` +
        `2. Water is split into hydrogen and oxygen (light reaction).\n` +
        `3. CO₂ is fixed into glucose using ATP and NADPH (Calvin cycle).\n\n` +
        `> 🌱 Tip: Photosynthesis happens mainly in the *mesophyll* cells of the leaf.`,
      confidence: "verified",
      source: { book: "NCERT Class 10 Science", chapter: "Ch. 6 — Life Processes" },
    },
  },
  {
    match: /quadratic|\bx\^2\b|equation/i,
    reply: {
      content:
        `For a quadratic equation $ax^2 + bx + c = 0$, the roots are given by the **quadratic formula**:\n\n` +
        `$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$\n\n` +
        `**Example:** Solve $2x^2 - 4x - 6 = 0$.\n\n` +
        `1. $a = 2,\\ b = -4,\\ c = -6$\n` +
        `2. Discriminant $= b^2 - 4ac = 16 + 48 = 64$\n` +
        `3. $x = \\dfrac{4 \\pm 8}{4} \\Rightarrow x = 3 \\text{ or } x = -1$\n`,
      confidence: "verified",
      source: { book: "NCERT Class 10 Math", chapter: "Ch. 4 — Quadratic Equations" },
    },
  },
  {
    match: /french revolution|revolution/i,
    reply: {
      content:
        `### Causes of the French Revolution (1789)\n\n` +
        `| # | Cause | Detail |\n|---|---|---|\n` +
        `| 1 | **Social inequality** | Three Estates; clergy & nobility tax-exempt |\n` +
        `| 2 | **Economic crisis** | Empty treasury after wars + bad harvests |\n` +
        `| 3 | **Enlightenment ideas** | Rousseau, Voltaire, Montesquieu |\n` +
        `| 4 | **Weak monarchy** | Louis XVI's indecision |\n\n` +
        `These pressures combined to spark the storming of the Bastille on **14 July 1789**.`,
      confidence: "ai",
      source: { book: "NCERT Class 9 History", chapter: "Ch. 1 — The French Revolution" },
    },
  },
  {
    match: /newton|न्यूटन|ન્યૂટન/i,
    reply: {
      content:
        `### Newton's Three Laws of Motion\n\n` +
        `1. **First Law (Inertia):** A body remains at rest or in uniform motion unless acted on by an external force.\n` +
        `2. **Second Law:** $F = ma$ — force equals mass times acceleration.\n` +
        `3. **Third Law:** Every action has an equal and opposite reaction.\n\n` +
        `**Worked example:** A 5 kg block pushed with 20 N → $a = \\dfrac{F}{m} = \\dfrac{20}{5} = 4\\,\\text{m/s}^2$.`,
      confidence: "verified",
      source: { book: "NCERT Class 9 Science", chapter: "Ch. 9 — Force and Laws of Motion" },
    },
  },
  {
    match: /trigonometry|त्रिकोणमिति|sin|cos|tan/i,
    reply: {
      content:
        `### Key Trigonometric Identities\n\n` +
        `$$\\sin^2\\theta + \\cos^2\\theta = 1$$\n` +
        `$$1 + \\tan^2\\theta = \\sec^2\\theta$$\n` +
        `$$\\sin(A+B) = \\sin A\\cos B + \\cos A\\sin B$$\n\n` +
        `Use these to simplify expressions or prove identities. Need a worked example? Just ask!`,
      confidence: "ai",
      source: { book: "NCERT Class 10 Math", chapter: "Ch. 8 — Trigonometry" },
    },
  },
];

const FALLBACK: MockReply = {
  content:
    `Great question! Here's a structured way to think about it:\n\n` +
    `1. **Identify** the key concept being asked.\n` +
    `2. **Recall** the relevant formula or principle from your textbook.\n` +
    `3. **Apply** it step-by-step to your problem.\n\n` +
    `_(This is a prototype response. The full Javaab AI will give you a complete, board-aligned answer with sources.)_`,
  confidence: "low",
};

/** Pick a mock reply based on the user's question. */
export function pickReply(
  question: string,
  opts?: { name?: string; isFirstReply?: boolean },
): MockReply {
  let reply: MockReply = FALLBACK;
  for (const t of TEMPLATES) {
    if (t.match.test(question)) {
      reply = t.reply;
      break;
    }
  }
  const name = opts?.name?.trim();
  if (opts?.isFirstReply && name) {
    return { ...reply, content: `Hi, **${name}** — ${reply.content}` };
  }
  return reply;
}

/** Simulate streaming-ish latency. */
export function fakeLatencyMs(): number {
  return 1200 + Math.random() * 1200;
}
