import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/brand/Logo";
import { ProgressBar } from "@/components/onboarding/ProgressBar";
import { BoardStep } from "@/components/onboarding/BoardStep";
import { ClassStep } from "@/components/onboarding/ClassStep";
import { LanguageStep } from "@/components/onboarding/LanguageStep";
import { StudyMethodStep } from "@/components/onboarding/StudyMethodStep";
import { StruggleStep } from "@/components/onboarding/StruggleStep";
import { DoneStep } from "@/components/onboarding/DoneStep";
import { useAuth } from "@/hooks/useAuth";
import {
  clearPendingPlan,
  getPendingPlan,
  type Board,
  type DifficultSubject,
  type InputMode,
  type Lang,
  type StudyMethod,
  type StudyStruggle,
} from "@/lib/auth";
import { cn } from "@/lib/utils";

const TOTAL = 6;

/** /onboarding — 6-step first-run flow. */
export default function Onboarding() {
  const navigate = useNavigate();
  const { user, updateUser } = useAuth();

  const [step, setStep] = useState(1);
  const [direction, setDirection] = useState<"forward" | "back">("forward");

  const [board, setBoard] = useState<Board | undefined>(user?.board);
  const [attendsCoaching, setAttendsCoaching] = useState<boolean | undefined>(user?.attendsCoaching);
  const [classNum, setClassNum] = useState<number | undefined>(user?.classNum);
  const [difficultSubjects, setDifficultSubjects] = useState<DifficultSubject[]>(
    user?.difficultSubjects ?? [],
  );
  const [languages, setLanguages] = useState<Lang[]>(user?.languages ?? []);
  const [studyMethod, setStudyMethod] = useState<StudyMethod | undefined>(user?.studyMethod);
  const [studyStruggle, setStudyStruggle] = useState<StudyStruggle | undefined>(user?.studyStruggle);
  const [preferredInputMode, setPreferredInputMode] = useState<InputMode | undefined>(
    user?.preferredInputMode,
  );

  const goNext = () => {
    setDirection("forward");
    setStep((s) => Math.min(TOTAL, s + 1));
  };
  const goBack = () => {
    setDirection("back");
    setStep((s) => Math.max(1, s - 1));
  };

  const finish = () => {
    if (!board || !classNum || languages.length === 0 || !studyMethod || !studyStruggle || !preferredInputMode) return;
    updateUser({
      board,
      classNum,
      languages,
      attendsCoaching,
      difficultSubjects,
      studyMethod,
      studyStruggle,
      preferredInputMode,
      isOnboarded: true,
    });
    setDirection("forward");
    setStep(6);
  };

  const handlePrimary = () => {
    const pending = getPendingPlan();
    if (pending) {
      clearPendingPlan();
      navigate(`/subscribe?plan=${pending}`, { replace: true });
    } else {
      navigate("/chat", { replace: true });
    }
  };

  const handleSecondary = () => navigate("/subjects", { replace: true });

  // Step 1: auto-advance after coaching chip selected
  const onSelectCoaching = (v: boolean) => {
    setAttendsCoaching(v);
    setTimeout(() => {
      setDirection("forward");
      setStep(2);
    }, 220);
  };

  // Step 4: auto-advance on study method selection
  const onSelectStudyMethod = (m: StudyMethod) => {
    setStudyMethod(m);
    setTimeout(() => {
      setDirection("forward");
      setStep(5);
    }, 220);
  };

  // Step 5: auto-advance after input mode chip
  const onSelectInputMode = (m: InputMode) => {
    setPreferredInputMode(m);
    setTimeout(() => {
      finish();
    }, 220);
  };

  // Disable rules for the explicit Next button
  const nextDisabled =
    (step === 2 && !classNum) ||
    (step === 3 && languages.length === 0);

  const showBackArrow = step >= 2 && step <= 5;
  const showNextButton = step === 2 || step === 3;

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex min-h-screen max-w-2xl flex-col px-5 py-6 sm:px-8 sm:py-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {showBackArrow ? (
              <button
                type="button"
                onClick={goBack}
                aria-label="Back"
                className="grid h-10 w-10 place-items-center rounded-full border border-border bg-card text-muted-foreground transition-colors hover:text-foreground"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            ) : null}
            <Logo />
          </div>
        </div>

        <div className="mt-8">
          <ProgressBar current={step} total={TOTAL} />
        </div>

        <div className="mt-10 flex-1 overflow-hidden">
          <StepFrame stepKey={step} direction={direction}>
            {step === 1 && (
              <BoardStep
                value={board}
                attendsCoaching={attendsCoaching}
                onSelectBoard={setBoard}
                onSelectCoaching={onSelectCoaching}
              />
            )}
            {step === 2 && (
              <ClassStep
                board={board}
                value={classNum}
                difficultSubjects={difficultSubjects}
                onSelectClass={setClassNum}
                onChangeSubjects={setDifficultSubjects}
              />
            )}
            {step === 3 && <LanguageStep value={languages} onChange={setLanguages} />}
            {step === 4 && <StudyMethodStep value={studyMethod} onSelect={onSelectStudyMethod} />}
            {step === 5 && (
              <StruggleStep
                value={studyStruggle}
                inputMode={preferredInputMode}
                onSelectStruggle={setStudyStruggle}
                onSelectInput={onSelectInputMode}
              />
            )}
            {step === 6 && board && classNum && (
              <DoneStep
                board={board}
                classNum={classNum}
                languages={languages}
                struggle={studyStruggle}
                onPrimary={handlePrimary}
                onSecondary={handleSecondary}
              />
            )}
          </StepFrame>
        </div>

        {showNextButton ? (
          <div className="mt-8">
            <Button
              size="lg"
              disabled={nextDisabled}
              onClick={step === 3 ? () => { setDirection("forward"); setStep(4); } : goNext}
              className={cn(
                "h-14 w-full rounded-pill text-base font-semibold transition-all",
                nextDisabled
                  ? "bg-muted text-muted-foreground shadow-none"
                  : "bg-primary text-primary-foreground shadow-glow hover:bg-primary/90",
              )}
            >
              Next <ArrowRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        ) : null}
      </div>
    </main>
  );
}

/** Wrapper that animates a horizontal slide whenever the step changes. */
function StepFrame({
  stepKey,
  direction,
  children,
}: {
  stepKey: number;
  direction: "forward" | "back";
  children: React.ReactNode;
}) {
  const [renderedKey, setRenderedKey] = useState(stepKey);
  const [animClass, setAnimClass] = useState("");
  const firstRender = useRef(true);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      setRenderedKey(stepKey);
      return;
    }
    setAnimClass(direction === "forward" ? "step-enter-from-right" : "step-enter-from-left");
    setRenderedKey(stepKey);
    const t = setTimeout(() => setAnimClass(""), 320);
    return () => clearTimeout(t);
  }, [stepKey, direction]);

  return (
    <div key={renderedKey} className={animClass}>
      {children}
    </div>
  );
}
