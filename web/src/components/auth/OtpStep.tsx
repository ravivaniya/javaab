import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp";

interface OtpStepProps {
  phone: string;
  onVerify: (code: string) => Promise<void>;
  onResend: () => Promise<void>;
  onBack: () => void;
}

/** Mask the phone like +91 XXXXXX1234 */
function maskPhone(p: string) {
  if (p.length !== 10) return `+91 ${p}`;
  return `+91 XXXXXX${p.slice(-4)}`;
}

/** Step 2 of /login — 6-digit OTP entry with countdown. */
export function OtpStep({ phone, onVerify, onResend, onBack }: OtpStepProps) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [seconds, setSeconds] = useState(45);
  const [resending, setResending] = useState(false);
  const otpRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Autofocus the OTP input when this step mounts
    const t = setTimeout(() => otpRef.current?.focus(), 80);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (seconds <= 0) return;
    const t = setInterval(() => setSeconds((s) => s - 1), 1000);
    return () => clearInterval(t);
  }, [seconds]);

  const handleVerify = async (codeToCheck = code) => {
    if (codeToCheck.length !== 6) return;
    setLoading(true);
    setError(null);
    try {
      await onVerify(codeToCheck);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid OTP");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    setError(null);
    try {
      await onResend();
      setSeconds(45);
      setCode("");
    } finally {
      setResending(false);
    }
  };

  const mm = Math.floor(seconds / 60);
  const ss = String(seconds % 60).padStart(2, "0");

  return (
    <div className="space-y-6">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Change number
      </button>

      <header className="space-y-2">
        <h2 className="font-display text-3xl font-black tracking-tight">
          Enter the OTP
        </h2>
        <p className="text-base text-muted-foreground">
          Sent to{" "}
          <span className="font-semibold text-foreground">
            {maskPhone(phone)}
          </span>
        </p>
      </header>

      <div className="space-y-3">
        <InputOTP
          ref={otpRef}
          maxLength={6}
          autoFocus
          value={code}
          onChange={(v) => {
            setCode(v);
            setError(null);
            if (v.length === 6) void handleVerify(v);
          }}
          containerClassName="justify-between"
        >
          <InputOTPGroup className="gap-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <InputOTPSlot
                key={i}
                index={i}
                className="h-14 w-12 rounded-2xl border border-input text-xl font-semibold first:rounded-l-2xl last:rounded-r-2xl"
              />
            ))}
          </InputOTPGroup>
        </InputOTP>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        <div className="text-sm">
          {seconds > 0 ? (
            <span className="text-muted-foreground">
              Resend OTP in{" "}
              <span className="font-mono font-semibold text-foreground">
                {mm}:{ss}
              </span>
            </span>
          ) : (
            <button
              type="button"
              disabled={resending}
              onClick={handleResend}
              className="font-semibold text-primary hover:underline"
            >
              {resending ? "Sending…" : "Resend OTP"}
            </button>
          )}
        </div>
      </div>

      <Button
        type="button"
        size="lg"
        disabled={loading || code.length !== 6}
        onClick={() => handleVerify()}
        className="h-14 w-full rounded-pill text-base font-semibold shadow-glow"
      >
        {loading ? <Loader2 className="animate-spin" /> : "Verify & Continue"}
      </Button>
    </div>
  );
}
