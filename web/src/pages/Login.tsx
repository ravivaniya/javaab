import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { BrandPanel } from "@/components/auth/BrandPanel";
import { PhoneStep } from "@/components/auth/PhoneStep";
import { OtpStep } from "@/components/auth/OtpStep";
import { Logo } from "@/components/brand/Logo";
import { useAuth } from "@/hooks/useAuth";
import { usePendingPlan } from "@/hooks/usePendingPlan";
import { getPendingPlan, clearPendingPlan } from "@/lib/auth";

/** /login — phone + OTP authentication. */
export default function Login() {
  usePendingPlan();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { sendOtp, verifyOtp } = useAuth();

  const [phone, setPhone] = useState<string | null>(null);

  const handlePhoneSubmit = async (p: string) => {
    await sendOtp(p);
    setPhone(p);
  };

  const handleVerify = async (code: string) => {
    if (!phone) return;
    const user = await verifyOtp(phone, code);

    // Routing decision after verify.
    const redirect = params.get("redirect");
    const pending = getPendingPlan();

    if (!user.isOnboarded) {
      // New user → onboarding (preserve plan via sessionStorage).
      navigate("/onboarding", { replace: true });
      return;
    }
    if (pending) {
      clearPendingPlan();
      navigate(`/subscribe?plan=${pending}`, { replace: true });
      return;
    }
    navigate(redirect || "/chat", { replace: true });
  };

  return (
    <main className="grid min-h-screen w-full bg-background lg:grid-cols-2">
      <BrandPanel />

      <section className="flex min-h-screen flex-col justify-between px-5 py-8 sm:px-8 lg:py-12 lg:px-12">
        <div className="lg:hidden">
          <Logo />
        </div>
        <div className="hidden lg:block">
          {/* Spacer; logo already on brand panel for desktop */}
        </div>

        <div className="mx-auto w-full max-w-md flex-1 lg:flex lg:items-center">
          <div className="w-full rounded-3xl bg-card p-6 shadow-soft sm:p-8 lg:border lg:border-border">
            {phone === null ? (
              <PhoneStep onSubmit={handlePhoneSubmit} />
            ) : (
              <OtpStep
                phone={phone}
                onVerify={handleVerify}
                onResend={() => sendOtp(phone)}
                onBack={() => setPhone(null)}
              />
            )}
          </div>
        </div>

        <p className="mt-8 text-center text-xs text-muted-foreground">
          Made with 🧡 for Indian students
        </p>
      </section>
    </main>
  );
}
