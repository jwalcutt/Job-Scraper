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
  explained_count: number;
  profile_complete: boolean;
}

function formatSalary(min: number | null, max: number | null): string {
  if (!min && !max) return "";
  const fmt = (n: number) => `$${(n / 1000).toFixed(0)}k`;
  if (min && max) return `${fmt(min)}–${fmt(max)}`;
  if (min) return `${fmt(min)}+`;
  return `up to ${fmt(max!)}`;
}

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const cls =
    pct >= 80 ? "bg-green-100 text-green-700" :
    pct >= 60 ? "bg-yellow-100 text-yellow-700" :
    "bg-gray-100 text-gray-500";
  return <span className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full ${cls}`}>{pct}%</span>;
}

const PAGE_SIZE = 20;

export default function JobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [status, setStatus] = useState<MatchStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [saved, setSaved] = useState<Set<number>>(new Set());

  // Filters
  const [minScore, setMinScore] = useState(0);
  const [titleFilter, setTitleFilter] = useState("");
  const [companyFilter, setCompanyFilter] = useState("");
  const [remoteFilter, setRemoteFilter] = useState<"" | "true" | "false">("");

  function buildParams(opts: {
    minScore?: number; title?: string; company?: string; remote?: string; offset?: number;
  }) {
    const params = new URLSearchParams({ limit: String(PAGE_SIZE) });
    if (opts.minScore) params.set("min_score", String(opts.minScore));
    if (opts.title) params.set("title", opts.title);
    if (opts.company) params.set("company", opts.company);
    if (opts.remote) params.set("remote", opts.remote);
    if (opts.offset) params.set("offset", String(opts.offset));
    return params;
  }

  const fetchMatches = useCallback(async (opts: {
    minScore?: number; title?: string; company?: string; remote?: string;
  }) => {
    const data = await api.get<Job[]>(`/jobs/matches?${buildParams(opts)}`);
    setJobs(data);
    setOffset(data.length);
    setHasMore(data.length === PAGE_SIZE);
  }, []);

  useEffect(() => {
    Promise.all([
      api.get<MatchStatus>("/jobs/matches/status"),
      api.get<Job[]>(`/jobs/matches?${buildParams({})}`),
      api.get<Job[]>("/jobs/saved"),
    ])
      .then(([st, matches, savedJobs]) => {
        setStatus(st);
        setJobs(matches);
        setOffset(matches.length);
        setHasMore(matches.length === PAGE_SIZE);
        setSaved(new Set(savedJobs.map((j) => j.id)));
        setLoading(false);
      })
      .catch(() => router.push("/login"));
  }, [router]);

  // Auto-poll every 3 s while embedding is still pending
  useEffect(() => {
    if (loading || status?.has_embedding) return;
    const id = setInterval(async () => {
      try {
        const st = await api.get<MatchStatus>("/jobs/matches/status");
        setStatus(st);
        if (st.has_embedding) {
          const matches = await api.get<Job[]>(`/jobs/matches?${buildParams({})}`);
          setJobs(matches);
          setOffset(matches.length);
          setHasMore(matches.length === PAGE_SIZE);
          clearInterval(id);
        }
      } catch { /* ignore */ }
    }, 3000);
    return () => clearInterval(id);
  }, [loading, status?.has_embedding]);

  async function applyFilters() {
    await fetchMatches({
      minScore, title: titleFilter, company: companyFilter, remote: remoteFilter,
    });
  }

  async function clearFilters() {
    setMinScore(0); setTitleFilter(""); setCompanyFilter(""); setRemoteFilter("");
    await fetchMatches({});
  }

  async function loadMore() {
    setLoadingMore(true);
    try {
      const data = await api.get<Job[]>(`/jobs/matches?${buildParams({
        minScore, title: titleFilter, company: companyFilter, remote: remoteFilter, offset,
      })}`);
      setJobs((prev) => [...prev, ...data]);
      setOffset((prev) => prev + data.length);
      setHasMore(data.length === PAGE_SIZE);
    } finally {
      setLoadingMore(false);
    }
  }

  async function toggleSave(jobId: number, e: React.MouseEvent) {
    e.preventDefault();
    if (saved.has(jobId)) {
      await api.delete(`/jobs/${jobId}/save`);
      setSaved((s) => { const n = new Set(s); n.delete(jobId); return n; });
    } else {
      await api.post(`/jobs/${jobId}/save`, {});
      setSaved((s) => new Set(s).add(jobId));
    }
  }

  const hasFilters = minScore > 0 || titleFilter || companyFilter || remoteFilter;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-2xl font-bold text-gray-900">Your matches</h1>
        <div className="flex gap-4 text-sm">
          <Link href="/search" className="text-gray-500 hover:text-gray-700">Search all jobs</Link>
          <Link href="/saved" className="text-brand-600 hover:underline">Saved</Link>
          <Link href="/profile" className="text-gray-500 hover:text-gray-700">Profile</Link>
        </div>
      </div>

      {/* Status banners */}
      {!loading && status && !status.profile_complete && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 mb-5">
          <p className="text-sm text-amber-800">
            <span className="font-medium">Profile incomplete.</span>{" "}
            Add desired titles, skills, or upload a resume.{" "}
            <Link href="/profile" className="underline">Complete profile →</Link>
          </p>
        </div>
      )}
      {!loading && status?.profile_complete && !status.has_embedding && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 mb-5 flex items-center gap-3">
          <div className="w-4 h-4 shrink-0 rounded-full border-2 border-blue-400 border-t-blue-700 animate-spin" />
          <p className="text-sm text-blue-800">
            <span className="font-medium">Computing your matches…</span>{" "}
            Hang tight, this only takes a moment. The page will update automatically.
          </p>
        </div>
      )}

      {/* Filter bar */}
      {!loading && (
        <div className="rounded-lg border border-gray-200 bg-white p-3 mb-5 flex flex-wrap gap-2 items-end">
          <div className="flex-1 min-w-32">
            <label className="block text-xs text-gray-500 mb-1">Title</label>
            <input
              type="text"
              placeholder="engineer, analyst…"
              value={titleFilter}
              onChange={(e) => setTitleFilter(e.target.value)}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div className="flex-1 min-w-28">
            <label className="block text-xs text-gray-500 mb-1">Company</label>
            <input
              type="text"
              placeholder="stripe, notion…"
              value={companyFilter}
              onChange={(e) => setCompanyFilter(e.target.value)}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Location</label>
            <select
              value={remoteFilter}
              onChange={(e) => setRemoteFilter(e.target.value as "" | "true" | "false")}
              className="rounded border border-gray-300 px-2 py-1.5 text-xs"
            >
              <option value="">Any</option>
              <option value="true">Remote</option>
              <option value="false">Onsite</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Min score</label>
            <select
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="rounded border border-gray-300 px-2 py-1.5 text-xs"
            >
              <option value={0}>All</option>
              <option value={0.5}>50%+</option>
              <option value={0.6}>60%+</option>
              <option value={0.7}>70%+</option>
              <option value={0.8}>80%+</option>
            </select>
          </div>
          <div className="flex gap-1">
            <button
              onClick={applyFilters}
              className="rounded bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700 transition-colors"
            >
              Filter
            </button>
            {hasFilters && (
              <button
                onClick={clearFilters}
                className="rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-50 transition-colors"
              >
                Clear
              </button>
            )}
          </div>
          <span className="ml-auto text-xs text-gray-400 self-center">{jobs.length} results</span>
        </div>
      )}

      {loading && <div className="text-center py-16 text-gray-400 text-sm">Loading matches…</div>}

      {/* Job cards */}
      <div className="space-y-2">
        {jobs.map((job) => (
          <div
            key={job.id}
            onClick={() => router.push(`/jobs/${job.id}`)}
            className="block rounded-lg border border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm transition-all overflow-hidden cursor-pointer"
          >
            <div className="flex items-start gap-3 p-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-sm text-gray-900">{job.title}</span>
                  {job.score !== null && <ScoreBadge score={job.score} />}
                  <span className="text-xs text-gray-400 capitalize">
                    {job.source.replace("jobspy_", "").replace("_", " ")}
                  </span>
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
                  <p className="text-xs text-blue-600 mt-1 italic line-clamp-1">{job.explanation}</p>
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
          </div>
        ))}
      </div>

      {!loading && status?.has_embedding && jobs.length === 0 && (
        <p className="text-center text-gray-400 text-sm py-12">
          No matches{hasFilters ? " for these filters" : ""}.
          {hasFilters && (
            <button onClick={clearFilters} className="ml-1 text-brand-600 hover:underline">
              Clear filters
            </button>
          )}
        </p>
      )}

      {hasMore && (
        <div className="flex justify-center mt-6">
          <button
            onClick={loadMore}
            disabled={loadingMore}
            className="rounded-lg border border-gray-300 px-6 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors"
          >
            {loadingMore ? "Loading…" : "Load more"}
          </button>
        </div>
      )}
    </div>
  );
}
