import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AppHeader } from "@/components/AppHeader";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useAuth } from "@/hooks/useAuth";
import type { Board, Lang } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const BOARDS: { id: Board; label: string }[] = [
  { id: "cbse", label: "CBSE" },
  { id: "gseb", label: "GSEB" },
];
const CLASSES = [6, 7, 8, 9, 10, 11, 12];
const LANGS: { id: Lang; label: string }[] = [
  { id: "en", label: "English" },
  { id: "hi", label: "हिन्दी" },
  { id: "gu", label: "ગુજરાતી" },
];

export default function Settings() {
  const { user, updateUser, logout } = useAuth();
  const navigate = useNavigate();

  const [nameDraft, setNameDraft] = useState(user?.name ?? "");
  const [savedFlash, setSavedFlash] = useState(false);
  const [logoutOpen, setLogoutOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  useEffect(() => {
    setNameDraft(user?.name ?? "");
  }, [user?.name]);

  if (!user) return null;

  const isDirty = nameDraft.trim() !== (user.name ?? "");
  const initial = (user.name ?? "").trim().charAt(0).toUpperCase();
  const maskedPhone = `+91 XXXXXX${user.phone.slice(-4)}`;

  const handleSaveName = () => {
    updateUser({ name: nameDraft.trim() || undefined });
    setSavedFlash(true);
    setTimeout(() => setSavedFlash(false), 2000);
  };

  const setBoard = (b: Board) => {
    if (b === user.board) return;
    updateUser({ board: b });
    toast("✓ Updated");
  };

  const setClassNum = (c: number) => {
    if (c === user.classNum) return;
    updateUser({ classNum: c });
    toast("✓ Updated");
  };

  const toggleLang = (l: Lang) => {
    const cur = user.languages ?? [];
    const has = cur.includes(l);
    const next = has ? cur.filter((x) => x !== l) : [...cur, l];
    if (next.length === 0) {
      toast.error("Keep at least one language");
      return;
    }
    updateUser({ languages: next });
    toast("✓ Updated");
  };

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const handleDelete = () => {
    // Mocked: clear everything for this phone, log out, redirect to login.
    try {
      localStorage.removeItem(`javaab.chat.${user.phone}`);
    } catch {
      /* noop */
    }
    logout();
    navigate("/");
  };


  return (
    <div className="min-h-screen bg-background pb-24">
      <AppHeader />
      <main className="mx-auto max-w-[600px] px-4 pt-6 sm:px-6 sm:pt-10">
        <div className="sm:rounded-3xl sm:border sm:border-border sm:bg-card sm:p-8 sm:shadow-sm">
          <h1 className="font-display text-3xl font-extrabold tracking-tight">
            Profile &amp; Settings
          </h1>

          {/* SECTION 1 — YOUR PROFILE */}
          <Section label="Your profile" first>
            <div className="flex items-center gap-4">
              <div
                className={cn(
                  "flex h-16 w-16 items-center justify-center rounded-full text-2xl font-black",
                  initial
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground",
                )}
                aria-hidden
              >
                {initial || <span className="text-xl">👤</span>}
              </div>
              <div className="text-sm text-muted-foreground">
                <p className="font-semibold text-foreground">{user.name || "Add your name"}</p>
                <p className="text-xs">{maskedPhone}</p>
              </div>
            </div>

            <FieldLabel className="mt-6">What should we call you?</FieldLabel>
            <div className="relative">
              <Input
                value={nameDraft}
                maxLength={20}
                onChange={(e) => setNameDraft(e.target.value)}
                placeholder="e.g. Rahul, Priya..."
                className="h-12 rounded-2xl border-border px-4 py-3 pr-16 text-base"
              />
              <span className="pointer-events-none absolute bottom-2 right-3 text-[11px] text-muted-foreground">
                {nameDraft.length}/20
              </span>
            </div>

            <div className="mt-3 flex h-9 items-center gap-3">
              {isDirty && (
                <Button
                  size="sm"
                  onClick={handleSaveName}
                  className="rounded-pill bg-primary px-6 font-bold text-primary-foreground hover:bg-primary/90"
                >
                  Save
                </Button>
              )}
              {savedFlash && (
                <span className="text-sm font-semibold text-primary">
                  ✓ Saved
                </span>
              )}
            </div>

            <FieldLabel className="mt-6">Mobile Number</FieldLabel>
            <div className="rounded-2xl bg-muted px-4 py-3 text-muted-foreground">
              {maskedPhone}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              To change your number, contact support.
            </p>
          </Section>

          {/* SECTION 2 — STUDY SETTINGS */}
          <Section label="Study settings">
            <p className="-mt-2 mb-4 text-sm text-muted-foreground">
              Update these if your class or board changes.
            </p>

            <FieldLabel>Board</FieldLabel>
            <div className="flex flex-wrap gap-2">
              {BOARDS.map((b) => (
                <Chip key={b.id} active={user.board === b.id} onClick={() => setBoard(b.id)}>
                  {b.label}
                </Chip>
              ))}
            </div>

            <FieldLabel className="mt-6">Class</FieldLabel>
            <div className="flex flex-wrap gap-2">
              {CLASSES.map((c) => (
                <Chip key={c} active={user.classNum === c} onClick={() => setClassNum(c)}>
                  {c}
                </Chip>
              ))}
            </div>

            <FieldLabel className="mt-6">Answer language</FieldLabel>
            <div className="flex flex-wrap gap-2">
              {LANGS.map((l) => (
                <Chip
                  key={l.id}
                  active={(user.languages ?? []).includes(l.id)}
                  onClick={() => toggleLang(l.id)}
                >
                  {l.label}
                </Chip>
              ))}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              You can type in any language — this controls how Javaab replies.
            </p>
          </Section>

          {/* SECTION 4 — APPEARANCE */}
          <Section label="Appearance">
            <FieldLabel>Theme</FieldLabel>
            <ThemeToggle variant="segmented" />
            <p className="mt-2 text-xs text-muted-foreground">
              "System" follows your device setting.
            </p>
          </Section>

          {/* SECTION 5 — ACCOUNT */}
          <Section label="Account">
            <Button
              variant="outline"
              onClick={() => setLogoutOpen(true)}
              className="w-full rounded-pill border-border font-bold"
            >
              Log out
            </Button>
            <button
              type="button"
              onClick={() => setDeleteOpen(true)}
              className="mx-auto mt-4 block text-sm text-destructive hover:underline"
            >
              Delete my account
            </button>
          </Section>
        </div>
      </main>

      {/* Logout dialog */}
      <AlertDialog open={logoutOpen} onOpenChange={setLogoutOpen}>
        <AlertDialogContent className="rounded-3xl">
          <AlertDialogHeader>
            <AlertDialogTitle>Log out of Javaab?</AlertDialogTitle>
            <AlertDialogDescription>
              You'll need your phone number to sign back in.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-pill">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleLogout}
              className="rounded-pill bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Log out
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete account dialog */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent className="rounded-3xl">
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete your account and all your conversation history. This cannot
              be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-pill">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="rounded-pill bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Yes, delete my account
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

/* -------------------- helpers -------------------- */

function Section({
  label,
  children,
  first,
}: {
  label: string;
  children: React.ReactNode;
  first?: boolean;
}) {
  return (
    <section
      className={cn(
        "mt-8 pt-8",
        first ? "mt-6 border-t-0 pt-0" : "border-t border-border",
      )}
    >
      <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        {label}
      </p>
      {children}
    </section>
  );
}

function FieldLabel({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p className={cn("mb-2 text-sm font-semibold", className)}>{children}</p>
  );
}

function Chip({
  active,
  onClick,
  children,
}: {
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "rounded-pill border px-4 py-2 text-sm font-semibold transition-colors",
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border bg-background text-foreground hover:bg-muted",
      )}
    >
      {children}
    </button>
  );
}

