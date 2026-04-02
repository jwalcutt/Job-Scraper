"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import Nav from "@/components/Nav";
import { BookmarkIcon, ChevronLeftIcon } from "@/components/Icons";
import { api } from "@/lib/api";

interface Job {
  id: number;
  company: string;
  title: string;
  location: string | null;
  is_remote: boolean;
  salary_min: number | null;
  salary_max: number | null;
  url: string | null;
  source: string;
  posted_at: string | null;
  score: number | null;
  explanation: string | null;
  description_preview: string | null;
}

interface SkillsGap {
  matching: string[];
  missing: string[];
  error?: string | null;
}

function formatSalary(min: number | null, max: number | null): string {
  if (!min && !max) return "";
  const fmt = (n: number) => `$${(n / 1000).toFixed(0)}k`;
  if (min && max) return `${fmt(min)} - ${fmt(max)} / yr`;
  if (min) return `${fmt(min)}+ / yr`;
  return `up to ${fmt(max!)} / yr`;
}

function companyColor(name: string): string {
  const colors = [
    "bg-blue-500", "bg-emerald-500", "bg-violet-500", "bg-amber-500",
    "bg-rose-500", "bg-cyan-500", "bg-indigo-500", "bg-orange-500",
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

export default function JobDetailPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [gap, setGap] = useState<SkillsGap | null>(null);
  const [gapLoading, setGapLoading] = useState(false);
  const [gapUnavailable, setGapUnavailable] = useState(false);
  const [gapError, setGapError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Job>(`/jobs/${id}`)
      .then((j) => { setJob(j); setLoading(false); })
      .catch(() => router.push("/login"));
  }, [id, router]);

  async function toggleSave() {
    if (!job) return;
    if (saved) {
      await api.delete(`/jobs/${job.id}/save`);
      setSaved(false);
    } else {
      await api.post(`/jobs/${job.id}/save`, {});
      setSaved(true);
    }
  }

  async function loadSkillsGap() {
    if (!job || gap) return;
    setGapLoading(true);
    try {
      const result = await api.get<SkillsGap>(`/jobs/${job.id}/skills-gap`);
      if (result.error) {
        setGap(null);
        if (result.error === "insufficient_credits") {
          setGapError("Your Anthropic API account has insufficient credits. Add credits at console.anthropic.com.");
        } else if (result.error === "no_api_key" || result.error === "no_profile_data") {
          setGapUnavailable(true);
        } else {
          setGapError("Skills analysis failed. Try again later.");
        }
      } else if (result.matching.length === 0 && result.missing.length === 0) {
        setGap(null);
        setGapUnavailable(true);
      } else {
        setGap(result);
      }
    } catch {
      setGap(null);
      setGapUnavailable(true);
    } finally {
      setGapLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="flex items-center justify-center py-32 text-gray-400 text-sm">Loading...</div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="flex items-center justify-center py-32 text-gray-400 text-sm">Job not found.</div>
      </div>
    );
  }

  const salary = formatSalary(job.salary_min, job.salary_max);
  const pct = job.score !== null ? Math.round(job.score * 100) : null;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-2xl px-4 py-8">
        {/* Back nav */}
        <Link href="/jobs" className="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-gray-600 transition-colors mb-6">
          <ChevronLeftIcon className="w-4 h-4" />
          Back to matches
        </Link>

        {/* Header card */}
        <div className="rounded-xl bg-white p-6 mb-4 shadow-card animate-fade-in">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-white text-lg font-bold shrink-0 ${companyColor(job.company)}`}>
                {job.company.charAt(0).toUpperCase()}
              </div>
              <div>
                <h1 className="text-xl font-extrabold text-gray-900 tracking-tight">{job.title}</h1>
                <p className="text-gray-500 mt-0.5">
                  {job.company}
                  {job.location && <span className="text-gray-300"> / </span>}
                  {job.location}
                  {job.is_remote && <span className="ml-1.5 inline-flex items-center rounded bg-emerald-50 text-emerald-600 text-[10px] font-medium px-1.5 py-0.5">Remote</span>}
                </p>
                {salary && <p className="text-sm font-semibold text-gray-700 mt-1">{salary}</p>}
                <p className="text-[11px] text-gray-400 mt-1 uppercase tracking-wide">
                  via {job.source.replace("jobspy_", "").replace("_", " ")}
                  {job.posted_at && ` \u00B7 ${new Date(job.posted_at).toLocaleDateString()}`}
                </p>
              </div>
            </div>

            {/* Score badge */}
            {pct !== null && (
              <div className={`shrink-0 text-center rounded-xl px-5 py-3 animate-badge-pop ${
                pct >= 80 ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200" :
                pct >= 60 ? "bg-amber-50 text-amber-700 ring-1 ring-amber-200" :
                "bg-gray-50 text-gray-500 ring-1 ring-gray-200"
              }`}>
                <p className="text-2xl font-extrabold tabular-nums">{pct}%</p>
                <p className="text-[10px] font-medium uppercase tracking-wide">match</p>
              </div>
            )}
          </div>

          {/* LLM explanation */}
          {job.explanation && (
            <p className="mt-4 text-sm text-brand-700 bg-brand-50 rounded-lg px-4 py-2.5 italic border border-brand-100">
              {job.explanation}
            </p>
          )}

          {/* CTAs */}
          <div className="mt-5 flex gap-3">
            {job.url && (
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 text-center rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 transition-colors shadow-sm"
              >
                Apply now
              </a>
            )}
            <button
              onClick={toggleSave}
              className={`inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium transition-colors ${
                saved
                  ? "border-amber-300 bg-amber-50 text-amber-700"
                  : "border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              <BookmarkIcon filled={saved} className="w-4 h-4" />
              {saved ? "Saved" : "Save"}
            </button>
          </div>
        </div>

        {/* Skills gap */}
        <div className="rounded-xl bg-white p-6 mb-4 shadow-card animate-fade-in" style={{ animationDelay: "100ms" }}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-bold text-gray-900">Skills analysis</h2>
            {!gap && !gapUnavailable && !gapError && (
              <button
                onClick={loadSkillsGap}
                disabled={gapLoading}
                className="text-sm font-medium text-brand-600 hover:text-brand-700 disabled:opacity-50 transition-colors"
              >
                {gapLoading ? "Analyzing..." : "Analyze my fit"}
              </button>
            )}
          </div>

          {!gap && !gapLoading && !gapUnavailable && !gapError && (
            <p className="text-sm text-gray-500">
              Click &ldquo;Analyze my fit&rdquo; to compare your skills against this job&apos;s requirements.
            </p>
          )}

          {gapError && <p className="text-sm text-red-600">{gapError}</p>}

          {gapUnavailable && (
            <p className="text-sm text-gray-500">
              Skills analysis requires an Anthropic API key and a profile with skills or a resume.
              Add your skills in <Link href="/profile" className="text-brand-600 hover:underline">Profile settings</Link>.
            </p>
          )}

          {gap && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-bold text-emerald-700 uppercase tracking-wider mb-2">
                  You have ({gap.matching.length})
                </p>
                {gap.matching.length === 0 ? (
                  <p className="text-xs text-gray-400">None identified</p>
                ) : (
                  <ul className="space-y-1.5">
                    {gap.matching.map((s) => (
                      <li key={s} className="text-sm flex items-center gap-1.5">
                        <span className="w-4 h-4 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-[10px] font-bold shrink-0">&#10003;</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <p className="text-xs font-bold text-red-600 uppercase tracking-wider mb-2">
                  Gaps ({gap.missing.length})
                </p>
                {gap.missing.length === 0 ? (
                  <p className="text-xs text-gray-400">No gaps identified</p>
                ) : (
                  <ul className="space-y-1.5">
                    {gap.missing.map((s) => (
                      <li key={s} className="text-sm flex items-center gap-1.5">
                        <span className="w-4 h-4 rounded-full bg-red-100 text-red-500 flex items-center justify-center text-[10px] font-bold shrink-0">&#10007;</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Description */}
        {job.description_preview && (
          <div className="rounded-xl bg-white p-6 shadow-card animate-fade-in" style={{ animationDelay: "200ms" }}>
            <h2 className="font-bold text-gray-900 mb-3">Description</h2>
            <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-line">
              {job.description_preview}
            </p>
            {job.url && (
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block mt-4 text-sm font-medium text-brand-600 hover:text-brand-700 transition-colors"
              >
                Read full description on {job.company}&apos;s site &rarr;
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
