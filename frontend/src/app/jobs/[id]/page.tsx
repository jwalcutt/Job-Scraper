"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
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
}

function formatSalary(min: number | null, max: number | null): string {
  if (!min && !max) return "";
  const fmt = (n: number) => `$${(n / 1000).toFixed(0)}k`;
  if (min && max) return `${fmt(min)} – ${fmt(max)} / yr`;
  if (min) return `${fmt(min)}+ / yr`;
  return `up to ${fmt(max!)} / yr`;
}

export default function JobDetailPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [gap, setGap] = useState<SkillsGap | null>(null);
  const [gapLoading, setGapLoading] = useState(false);
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
      setGap(result);
    } catch {
      setGap({ matching: [], missing: [] });
    } finally {
      setGapLoading(false);
    }
  }

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-gray-400">Loading…</div>;
  }

  if (!job) {
    return <div className="flex min-h-screen items-center justify-center text-gray-400">Job not found.</div>;
  }

  const salary = formatSalary(job.salary_min, job.salary_max);
  const pct = job.score !== null ? Math.round(job.score * 100) : null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      {/* Back nav */}
      <Link href="/jobs" className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 mb-6">
        ← Back to matches
      </Link>

      {/* Header card */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{job.title}</h1>
            <p className="text-gray-600 mt-1">
              {job.company}
              {job.location && ` · ${job.location}`}
              {job.is_remote && " · Remote"}
            </p>
            {salary && <p className="text-sm text-gray-500 mt-0.5">{salary}</p>}
            <p className="text-xs text-gray-400 mt-1 capitalize">
              via {job.source.replace("jobspy_", "").replace("_", " ")}
              {job.posted_at && ` · ${new Date(job.posted_at).toLocaleDateString()}`}
            </p>
          </div>

          {/* Score badge */}
          {pct !== null && (
            <div className={`shrink-0 text-center rounded-xl px-4 py-3 ${
              pct >= 80 ? "bg-green-50 text-green-700" :
              pct >= 60 ? "bg-yellow-50 text-yellow-700" :
              "bg-gray-50 text-gray-500"
            }`}>
              <p className="text-2xl font-bold">{pct}%</p>
              <p className="text-xs">match</p>
            </div>
          )}
        </div>

        {/* LLM explanation */}
        {job.explanation && (
          <p className="mt-4 text-sm text-blue-700 bg-blue-50 rounded-lg px-4 py-2 italic">
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
              className="flex-1 text-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 transition-colors"
            >
              Apply now →
            </a>
          )}
          <button
            onClick={toggleSave}
            className={`rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
              saved
                ? "border-yellow-300 bg-yellow-50 text-yellow-700"
                : "border-gray-300 text-gray-600 hover:bg-gray-50"
            }`}
          >
            {saved ? "★ Saved" : "☆ Save"}
          </button>
        </div>
      </div>

      {/* Skills gap */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-900">Skills analysis</h2>
          {!gap && (
            <button
              onClick={loadSkillsGap}
              disabled={gapLoading}
              className="text-sm text-brand-600 hover:underline disabled:opacity-50"
            >
              {gapLoading ? "Analyzing…" : "Analyze my fit"}
            </button>
          )}
        </div>

        {!gap && !gapLoading && (
          <p className="text-sm text-gray-500">
            Click &ldquo;Analyze my fit&rdquo; to compare your skills against this job&apos;s requirements.
          </p>
        )}

        {gap && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-semibold text-green-700 uppercase tracking-wide mb-2">
                You have ({gap.matching.length})
              </p>
              {gap.matching.length === 0 ? (
                <p className="text-xs text-gray-400">None identified</p>
              ) : (
                <ul className="space-y-1">
                  {gap.matching.map((s) => (
                    <li key={s} className="text-sm flex items-center gap-1.5">
                      <span className="text-green-500 font-bold">✓</span> {s}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <p className="text-xs font-semibold text-red-600 uppercase tracking-wide mb-2">
                Gaps ({gap.missing.length})
              </p>
              {gap.missing.length === 0 ? (
                <p className="text-xs text-gray-400">No gaps identified</p>
              ) : (
                <ul className="space-y-1">
                  {gap.missing.map((s) => (
                    <li key={s} className="text-sm flex items-center gap-1.5">
                      <span className="text-red-400">✗</span> {s}
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
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="font-semibold text-gray-900 mb-3">Description preview</h2>
          <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-line">
            {job.description_preview}
          </p>
          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-3 text-sm text-brand-600 hover:underline"
            >
              Read full description on {job.company}&apos;s site →
            </a>
          )}
        </div>
      )}
    </div>
  );
}
