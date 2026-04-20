import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, ChevronRight } from "lucide-react";
import { AppHeader } from "@/components/AppHeader";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { SubjectCard } from "@/components/subjects/SubjectCard";
import { useAuth } from "@/hooks/useAuth";
import {
  chaptersFor,
  getSubjectProgress,
  subjectsForBoard,
  type SubjectKey,
  type SubjectMeta,
} from "@/lib/subjects";
import type { Board } from "@/lib/auth";
import { cn } from "@/lib/utils";

/** Bento subject grid + chapter accordion. */
export default function Subjects() {
  const { user, updateUser } = useAuth();
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();

  const board: Board = (user?.board ?? "cbse") as Board;
  const classNum = user?.classNum ?? 10;
  const phone = user?.phone ?? "anon";

  const activeSubjectKey = (params.get("s") as SubjectKey | null) ?? null;

  const subjects = useMemo(() => subjectsForBoard(board), [board]);
  const activeSubject = subjects.find((s) => s.key === activeSubjectKey) ?? null;

  const totalAnswered = useMemo(
    () =>
      subjects.reduce(
        (sum, s) => sum + getSubjectProgress(phone, board, classNum, s.key).questionsAnswered,
        0,
      ),
    [subjects, phone, board, classNum],
  );

  const setBoard = (b: Board) => {
    updateUser({ board: b });
    setParams({}, { replace: true });
  };

  const setClass = (c: number) => updateUser({ classNum: c });

  const openSubject = (key: SubjectKey) => {
    setParams({ s: key });
    window.scrollTo({ top: 320, behavior: "smooth" });
  };

  const startChat = (subject: SubjectMeta, chapterNum: number, chapterTitle: string) => {
    const ctx = encodeURIComponent(`${subject.name} · Chapter ${chapterNum}: ${chapterTitle}`);
    nav(`/chat?subject=${subject.key}&chapter=${chapterNum}&ctx=${ctx}`);
  };

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        {/* Title + controls */}
        <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="font-display text-4xl font-black tracking-tight sm:text-5xl">
              Subjects
            </h1>
            <p className="mt-2 text-muted-foreground">
              Browse chapters, jump straight into focused chat.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Board pill toggle */}
            <div className="inline-flex rounded-pill bg-muted p-1">
              {(["cbse", "gseb"] as Board[]).map((b) => (
                <button
                  key={b}
                  onClick={() => setBoard(b)}
                  className={cn(
                    "rounded-pill px-4 py-1.5 text-sm font-semibold transition-all",
                    board === b
                      ? "bg-card text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {b.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Class dropdown */}
            <Select value={String(classNum)} onValueChange={(v) => setClass(Number(v))}>
              <SelectTrigger className="h-10 w-[130px] rounded-pill border-border bg-card font-semibold">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[6, 7, 8, 9, 10, 11, 12].map((c) => (
                  <SelectItem key={c} value={String(c)}>
                    Class {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Empty state hint */}
        {totalAnswered === 0 && (
          <div className="mb-6 rounded-3xl border border-dashed border-border bg-card/60 p-5 text-center">
            <p className="text-sm font-medium text-muted-foreground">
              🎯 Start asking questions to track your progress here!
            </p>
          </div>
        )}

        {/* Bento grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-4 sm:gap-5 lg:grid-cols-6">
          {subjects.map((s) => (
            <SubjectCard
              key={s.key}
              subject={s}
              progress={getSubjectProgress(phone, board, classNum, s.key)}
              onClick={() => openSubject(s.key)}
            />
          ))}
        </div>

        {/* Chapter view */}
        {activeSubject && (
          <section className="mt-12 animate-fade-in">
            <div className="mb-3 flex items-center gap-1.5 text-sm text-muted-foreground">
              <button
                onClick={() => setParams({}, { replace: true })}
                className="hover:text-foreground"
              >
                Subjects
              </button>
              <ChevronRight className="h-4 w-4" />
              <span className="font-semibold text-foreground">{activeSubject.name}</span>
            </div>

            <div className="rounded-3xl bg-card p-2 shadow-soft ring-1 ring-border sm:p-4">
              <Accordion type="single" collapsible className="w-full">
                {chaptersFor(activeSubject.key).map((ch) => {
                  const answered =
                    getSubjectProgress(phone, board, classNum, activeSubject.key).byChapter[
                      ch.num
                    ] ?? 0;
                  return (
                    <AccordionItem
                      key={ch.num}
                      value={`ch-${ch.num}`}
                      className="border-b border-border last:border-0"
                    >
                      <AccordionTrigger className="px-3 py-4 hover:no-underline sm:px-4">
                        <div className="flex flex-1 items-center justify-between gap-3 pr-3 text-left">
                          <div className="min-w-0">
                            <p className="truncate text-base font-semibold">
                              <span className="text-muted-foreground">Ch.{ch.num} —</span>{" "}
                              {ch.title}
                            </p>
                            <p className="mt-0.5 text-xs text-muted-foreground">
                              {answered === 0
                                ? "Not started"
                                : `${answered} question${answered === 1 ? "" : "s"} answered`}
                            </p>
                          </div>
                        </div>
                      </AccordionTrigger>
                      <AccordionContent className="px-3 pb-4 sm:px-4">
                        <div className="flex flex-col items-start gap-3 rounded-2xl bg-muted/40 p-4 sm:flex-row sm:items-center sm:justify-between">
                          <p className="text-sm text-muted-foreground">
                            Open chat focused on this chapter — Javaab will keep its answers within
                            the chapter context.
                          </p>
                          <Button
                            onClick={() => startChat(activeSubject, ch.num, ch.title)}
                            className="rounded-pill"
                          >
                            Ask
                            <ArrowRight className="h-4 w-4" />
                          </Button>
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  );
                })}
              </Accordion>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
