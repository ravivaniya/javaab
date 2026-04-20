import { FloatingChip } from "./FloatingChip";
import { Logo } from "@/components/brand/Logo";

/** Left branding panel for /login (orange, sample-question chips). */
export function BrandPanel() {
  return (
    <div className="relative hidden h-full overflow-hidden bg-primary text-primary-foreground lg:flex lg:flex-col lg:justify-between lg:p-12">
      <div className="absolute inset-0 bg-dot-pattern opacity-60" aria-hidden />
      <div
        className="absolute -right-32 -top-32 h-96 w-96 rounded-full bg-white/10 blur-3xl"
        aria-hidden
      />
      <div
        className="absolute -bottom-40 -left-20 h-96 w-96 rounded-full bg-black/10 blur-3xl"
        aria-hidden
      />

      <div className="relative">
        <Logo variant="light" />
      </div>

      <div className="relative space-y-6">
        <h1 className="font-display text-5xl font-black leading-[1.05] tracking-tight xl:text-6xl">
          Sawaal kuch <br /> bhi ho.
        </h1>
        <p className="font-display text-3xl font-medium text-white/85 xl:text-4xl">
          Javaab turant milega.
        </p>
        <p className="max-w-md text-base text-white/80">
          AI study help for CBSE & GSEB students, Class 6–12. Ask in any
          language — हिन्दी, ગુજરાતી or English.
        </p>
      </div>

      <div className="relative flex flex-wrap gap-3">
        <FloatingChip
          lang="en"
          text="What is photosynthesis?"
          delay={0.1}
          rotate={-3}
        />
        <FloatingChip
          lang="gu"
          text="ન્યૂટનના નિયમ સમજાવો"
          delay={0.25}
          rotate={2}
          className="ml-8"
        />
        <FloatingChip
          lang="hi"
          text="त्रिकोणमिति का सूत्र"
          delay={0.4}
          rotate={-1}
        />
      </div>
    </div>
  );
}
