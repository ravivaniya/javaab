import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface FloatingChipProps {
  text: string;
  lang: "en" | "hi" | "gu";
  className?: string;
  delay?: number;
  rotate?: number;
}

const langLabel: Record<FloatingChipProps["lang"], string> = {
  en: "EN",
  hi: "हि",
  gu: "ગુ",
};

/** Small floating chip showing a sample question on the auth branding panel. */
export function FloatingChip({ text, lang, className, delay = 0, rotate = 0 }: FloatingChipProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.6, ease: "easeOut" }}
      style={{ ["--r" as never]: `${rotate}deg`, transform: `rotate(${rotate}deg)` }}
      className={cn(
        "animate-float-soft inline-flex items-center gap-2 rounded-pill bg-white/95 px-4 py-2.5 text-sm shadow-soft backdrop-blur",
        className,
      )}
    >
      <span className="grid h-6 w-6 place-items-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground">
        {langLabel[lang]}
      </span>
      <span className="font-medium text-foreground">{text}</span>
    </motion.div>
  );
}
