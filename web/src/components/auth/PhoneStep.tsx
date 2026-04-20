import { useState } from "react";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2 } from "lucide-react";

const phoneSchema = z
  .string()
  .regex(/^\d{10}$/, "Enter a valid 10-digit mobile number");

interface PhoneStepProps {
  onSubmit: (phone: string) => Promise<void>;
}

/** Step 1 of /login — collect 10-digit phone number. */
export function PhoneStep({ onSubmit }: PhoneStepProps) {
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (v: string) => {
    const digits = v.replace(/\D/g, "").slice(0, 10);
    setPhone(digits);
    if (error) setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = phoneSchema.safeParse(phone);
    if (!parsed.success) {
      setError(parsed.error.issues[0].message);
      return;
    }
    setLoading(true);
    try {
      await onSubmit(phone);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <header className="space-y-2">
        <h2 className="font-display text-3xl font-black tracking-tight">
          Enter your mobile number
        </h2>
        <p className="text-base text-muted-foreground">
          We'll send you a 6-digit OTP. No password needed.
        </p>
      </header>

      <div className="space-y-2">
        <label htmlFor="phone" className="text-sm font-medium">
          Mobile number
        </label>
        <div className="flex items-stretch overflow-hidden rounded-2xl border border-input bg-background focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background">
          <span className="inline-flex select-none items-center gap-2 border-r border-input bg-secondary px-4 text-base font-semibold">
            <span aria-hidden>🇮🇳</span> +91
          </span>
          <Input
            id="phone"
            inputMode="numeric"
            autoComplete="tel-national"
            placeholder="98765 43210"
            value={phone}
            onChange={(e) => handleChange(e.target.value)}
            className="h-14 flex-1 border-0 bg-transparent text-lg tracking-wider focus-visible:ring-0 focus-visible:ring-offset-0"
            aria-invalid={!!error}
            aria-describedby={error ? "phone-err" : undefined}
          />
        </div>
        {error ? (
          <p id="phone-err" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
      </div>

      <Button
        type="submit"
        size="lg"
        disabled={loading || phone.length !== 10}
        className="h-14 w-full rounded-pill text-base font-semibold shadow-glow"
      >
        {loading ? <Loader2 className="animate-spin" /> : "Send OTP"}
      </Button>

      <p className="text-center text-xs text-muted-foreground">
        By continuing you agree to our{" "}
        <a href="#" className="font-medium text-foreground underline-offset-4 hover:underline">
          Terms
        </a>{" "}
        &{" "}
        <a href="#" className="font-medium text-foreground underline-offset-4 hover:underline">
          Privacy Policy
        </a>
        .
      </p>
    </form>
  );
}
