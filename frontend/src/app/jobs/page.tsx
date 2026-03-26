"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
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

interface MatchStatus {
  has_embedding: boolean;
  match_count: number;
  profile_complete: boolean;
}

function formatSalary(min: number | null, max: number | null): string {
  if (!min && !max) return "";
  const fmt = (n: number) => `$${(n / 1000).toFixed(0)}k`;
  if (min && max) return `${fmt(min)} – ${fmt(max)}`;
  if (min) return `${fmt(min)}+`;
  return `up to ${fmt(max!)}`;
}

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80
      ? "bg-green-100 text-green-700"
      : pct >= 60
      ? "bg-yellow-100 text-yellow-700"
      : "bg-gray-100 text-gray-500";
  return (
    <span className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full ${color}`}>
      {pct}%
    </span>
  );
}

function SourceBadge({ source }: { source: string }) {
  const label = source.replace("jobspy_", "").replace("_", " ");
  return (
    <span className="text-xs text-gray-400 capitalize">{label}</span>
  );
}

export default function JobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [status, setStatus] = useState<MatchStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState<Set<number>>(new Set());
  const [minScore, setMinScore] = useState(0);
  const [expanded, setExpanded] = useState<number | null>(null);

  const fetchMatches = useCallback(async (score: number) => {
    const data = await api.get<Job[]>(`/jobs/matches?min_score=${score}&limit=100`);
    setJobs(data);
  }, []);

  useEffect(() => {
    Promise.all([
      api.get<MatchStatus>("/jobs/matches/status"),
      api.get<Job[]>("/jobs/matches?limit=100"),
      api.get<Job[]>("/jobs/saved"),
    ])
      .then(([st, matches, savedJobs]) => {
        setStatus(st);
        setJobs(matches);
        setSaved(new Set(savedJobs.map((j) => j.id)));
        setLoading(false);
      })
      .catch(() => router.push("/login"));
  }, [router]);

  async function toggleSave(jobId: number, e: React.MouseEvent) {
    e.stopPropagation();
    if (saved.has(jobId)) {
      await api.delete(`/jobs/${jobId}/save`);
      setSaved((s) => { const n = new Set(s); n.delete(jobId); return n; });
    } else {
      await api.post(`/jobs/${jobId}/save`, {});
      setSaved((s) => new Set(s).add(jobId));
    }
  }

  async function handleScoreChange(val: number) {
    setMinScore(val);
    await fetchMatches(val);
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Your matches</h1>
        <div className="flex gap-4 items-center">
          <Link href="/saved" className="text-sm text-brand-600 hover:underline">Saved</Link>
          <Link href="/profile" className="text-sm text-gray-500 hover:underline">Edit profile</Link>
        </div>
      </div>

      {/* Empty / pending states */}
      {loading && (
        <div className="text-center py-16 text-gray-400">Loading matches…</div>
      )}

      {!loading && status && !status.profile_complete && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-5 mb-6">
          <p className="text-sm text-amber-800 font-medium">Profile incomplete</p>
          <p className="text-sm text-amber-700 mt-1">
            Add desired titles, skills, or upload a resume so we can find matches.{" "}
            <Link href="/profile" className="underline">Complete your profile</Link>
          </p>
        </div>
      )}

      {!loading && status?.profile_complete && !status.has_embedding && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-5 mb-6">
          <p className="text-sm text-blue-800 font-medium">Computing your matches…</p>
          <p className="text-sm text-blue-700 mt-1">
            Your profile embedding is being generated in the background. Refresh in a moment.
          </p>
        </div>
      )}

      {/* Filters */}
      {!loading && jobs.length > 0 && (
        <div className="flex items-center gap-4 mb-4">
          <label className="text-sm text-gray-600">
            Min score:
            <select
              value={minScore}
              onChange={(e) => handleScoreChange(Number(e.target.value))}
              className="ml-2 rounded border border-gray-300 text-sm px-2 py-1"
            >
              <option value={0}>All</option>
              <option value={0.5}>50%+</option>
              <option value={0.6}>60%+</option>
              <option value={0.7}>70%+</option>
              <option value={0.8}>80%+</option>
            </select>
          </label>
          <span className="text-sm text-gray-400">{jobs.length} results</span>
        </div>
      )}

      {/* Job list */}
      <div className="space-y-2">
        {jobs.map((job) => (
          <div
            key={job.id}
            className="rounded-lg border border-gray-200 bg-white overflow-hidden hover:border-gray-300 transition-colors cursor-pointer"
            onClick={() => setExpanded(expanded === job.id ? null : job.id)}
          >
            {/* Summary row */}
            <div className="flex items-start gap-3 p-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-gray-900 text-sm">{job.title}</span>
                  {job.score !== null && <ScoreBadge score={job.score} />}
                  <SourceBadge source={job.source} />
                </div>
                <p className="text-sm text-gray-600 mt-0.5">
                  {job.company}
                  {job.location && ` · ${job.location}`}
                  {job.is_remote && " · Remote"}
                </p>
                {(job.salary_min || job.salary_max) && (
                  <p className="text-xs text-gray-400 mt-0.5">{formatSalary(job.salary_min, job.salary_max)}</p>
                )}
                {job.explanation && (
                  <p className="text-xs text-blue-600 mt-1 italic">{job.explanation}</p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0 pt-0.5">
                <button
                  onClick={(e) => toggleSave(job.id, e)}
                  className={`text-xl leading-none transition-colors ${
                    saved.has(job.id) ? "text-yellow-400" : "text-gray-200 hover:text-yellow-300"
                  }`}
                  title={saved.has(job.id) ? "Unsave" : "Save"}
                >
                  ★
                </button>
                {job.url && (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700 transition-colors"
                  >
                    Apply
                  </a>
                )}
              </div>
            </div>

            {/* Expandable description preview */}
            {expanded === job.id && job.description_preview && (
              <div className="border-t border-gray-100 px-4 py-3 bg-gray-50">
                <p className="text-sm text-gray-600 leading-relaxed">{job.description_preview}</p>
                {job.url && (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block mt-2 text-xs text-brand-600 hover:underline"
                  >
                    View full posting →
                  </a>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {!loading && status?.has_embedding && jobs.length === 0 && (
        <div className="text-center py-16 text-gray-400 text-sm">
          No matches found{minScore > 0 ? ` above ${Math.round(minScore * 100)}%` : ""}.
          {minScore > 0 && (
            <button
              onClick={() => handleScoreChange(0)}
              className="ml-1 text-brand-600 hover:underline"
            >
              Show all
            </button>
          )}
        </div>
      )}
    </div>
  );
}
