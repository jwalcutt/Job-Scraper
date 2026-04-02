"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Nav from "@/components/Nav";
import { BookmarkIcon, XMarkIcon } from "@/components/Icons";
import { SkeletonList } from "@/components/Skeleton";
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
  completeness_score?: number;
  completeness_tips?: string[];
}

function formatSalary(min: number | null, max: number | null): string {
  if (!min && !max) return "";
  const fmt = (n: number) => `$${(n / 1000).toFixed(0)}k`;
  if (min && max) return `${fmt(min)} - ${fmt(max)}`;
  if (min) return `${fmt(min)}+`;
  return `up to ${fmt(max!)}`;
}

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "1d ago";
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

function companyColor(name: string): string {
  const colors = [
    "bg-blue-500", "bg-emerald-500", "bg-violet-500", "bg-amber-500",
    "bg-rose-500", "bg-cyan-500", "bg-indigo-500", "bg-orange-500",
    "bg-teal-500", "bg-pink-500", "bg-lime-600", "bg-fuchsia-500",
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

function scoreBorderColor(score: number | null): string {
  if (score === null) return "border-l-transparent";
  const pct = score * 100;
  if (pct >= 80) return "border-l-emerald-400";
  if (pct >= 60) return "border-l-amber-400";
  return "border-l-gray-200";
}

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const cls =
    pct >= 80 ? "bg-emerald-50 text-emerald-700 ring-emerald-200" :
    pct >= 60 ? "bg-amber-50 text-amber-700 ring-amber-200" :
    "bg-gray-50 text-gray-500 ring-gray-200";
  return (
    <span className={`animate-badge-pop shrink-0 text-xs font-bold tabular-nums px-2 py-0.5 rounded-full ring-1 ${cls}`}>
      {pct}%
    </span>
  );
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
  const [savingAnim, setSavingAnim] = useState<number | null>(null);
  const [dismissedBanner, setDismissedBanner] = useState(false);

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
    e.stopPropagation();
    setSavingAnim(jobId);
    setTimeout(() => setSavingAnim(null), 300);
    if (saved.has(jobId)) {
      await api.delete(`/jobs/${jobId}/save`);
      setSaved((s) => { const n = new Set(s); n.delete(jobId); return n; });
    } else {
      await api.post(`/jobs/${jobId}/save`, {});
      setSaved((s) => new Set(s).add(jobId));
    }
  }

  async function dismissJob(jobId: number, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    try {
      await api.post("/events", { event_type: "job_dismissed", job_id: jobId });
    } catch { /* best effort */ }
    setJobs((prev) => prev.filter((j) => j.id !== jobId));
  }

  const hasFilters = minScore > 0 || titleFilter || companyFilter || remoteFilter;

  // Compute stats
  const uniqueCompanies = new Set(jobs.map((j) => j.company)).size;
  const avgScore = jobs.length > 0
    ? Math.round(jobs.filter((j) => j.score !== null).reduce((sum, j) => sum + (j.score ?? 0), 0) / Math.max(jobs.filter((j) => j.score !== null).length, 1) * 100)
    : 0;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-3xl px-4 py-8">
        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-2xl font-extrabold tracking-tight text-gray-900">Your matches</h1>
          {!loading && status?.has_embedding && jobs.length > 0 && (
            <p className="text-sm text-gray-400 mt-1">
              {jobs.length} match{jobs.length !== 1 ? "es" : ""} across {uniqueCompanies} compan{uniqueCompanies !== 1 ? "ies" : "y"}
              {avgScore > 0 && <> &middot; avg score {avgScore}%</>}
            </p>
          )}
        </div>

        {/* Profile completeness banner */}
        {!loading && status && !dismissedBanner && status.completeness_score !== undefined && status.completeness_score < 80 && (
          <div className="relative rounded-xl border border-amber-200/60 bg-gradient-to-r from-amber-50 to-orange-50 p-4 mb-5 animate-fade-in">
            <button
              onClick={() => setDismissedBanner(true)}
              className="absolute top-3 right-3 text-amber-400 hover:text-amber-600"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
            <p className="text-sm font-semibold text-amber-800">
              Your profile is {status.completeness_score}% complete
            </p>
            {status.completeness_tips && status.completeness_tips.length > 0 && (
              <p className="text-xs text-amber-700 mt-1">{status.completeness_tips[0]}</p>
            )}
            <Link href="/profile" className="inline-block mt-2 text-xs font-medium text-amber-700 hover:text-amber-900 underline underline-offset-2">
              Complete your profile
            </Link>
          </div>
        )}

        {/* Status banners */}
        {!loading && status && !status.profile_complete && (
          <div className="rounded-xl border border-amber-200/60 bg-amber-50 p-4 mb-5 animate-fade-in">
            <p className="text-sm text-amber-800">
              <span className="font-semibold">Profile incomplete.</span>{" "}
              Add desired titles, skills, or upload a resume.{" "}
              <Link href="/profile" className="underline underline-offset-2">Complete profile</Link>
            </p>
          </div>
        )}
        {!loading && status?.profile_complete && !status.has_embedding && (
          <div className="rounded-xl border border-blue-200/60 bg-blue-50 p-4 mb-5 flex items-center gap-3 animate-fade-in">
            <div className="w-4 h-4 shrink-0 rounded-full border-2 border-blue-400 border-t-blue-700 animate-spin" />
            <p className="text-sm text-blue-800">
              <span className="font-semibold">Computing your matches...</span>{" "}
              This only takes a moment. The page will update automatically.
            </p>
          </div>
        )}

        {/* Filter bar */}
        {!loading && (
          <div className="rounded-xl bg-white/60 backdrop-blur-sm p-3 mb-5 flex flex-wrap gap-2 items-end animate-fade-in">
            <div className="flex-1 min-w-32">
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Title</label>
              <input
                type="text"
                placeholder="engineer, analyst..."
                value={titleFilter}
                onChange={(e) => setTitleFilter(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applyFilters()}
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition-shadow"
              />
            </div>
            <div className="flex-1 min-w-28">
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Company</label>
              <input
                type="text"
                placeholder="stripe, notion..."
                value={companyFilter}
                onChange={(e) => setCompanyFilter(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applyFilters()}
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition-shadow"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Location</label>
              <select
                value={remoteFilter}
                onChange={(e) => setRemoteFilter(e.target.value as "" | "true" | "false")}
                className="rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs"
              >
                <option value="">Any</option>
                <option value="true">Remote</option>
                <option value="false">Onsite</option>
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Min score</label>
              <select
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                className="rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs"
              >
                <option value={0}>All</option>
                <option value={0.5}>50%+</option>
                <option value={0.6}>60%+</option>
                <option value={0.7}>70%+</option>
                <option value={0.8}>80%+</option>
              </select>
            </div>
            <div className="flex gap-1.5">
              <button
                onClick={applyFilters}
                className="rounded-lg bg-brand-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-brand-700 transition-colors shadow-sm"
              >
                Filter
              </button>
              {hasFilters && (
                <button
                  onClick={clearFilters}
                  className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-50 transition-colors"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        )}

        {/* Loading skeletons */}
        {loading && <SkeletonList count={6} />}

        {/* Job cards */}
        <div className="space-y-2">
          {jobs.map((job, idx) => {
            const isTopMatch = idx === 0 && !hasFilters && jobs.length > 1;
            return (
              <div
                key={job.id}
                onClick={() => router.push(`/jobs/${job.id}`)}
                className={`
                  group relative rounded-xl border-l-[3px] bg-white
                  shadow-card hover:shadow-card-hover hover:-translate-y-px
                  transition-all duration-200 cursor-pointer overflow-hidden
                  animate-card-enter
                  ${scoreBorderColor(job.score)}
                  ${isTopMatch ? "ring-1 ring-brand-200 border-l-brand-500" : "border border-gray-100"}
                `}
                style={{ animationDelay: `${Math.min(idx * 40, 400)}ms` }}
              >
                {isTopMatch && (
                  <div className="absolute top-0 right-0 bg-brand-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-bl-lg">
                    Best match
                  </div>
                )}
                <div className="flex items-start gap-3 p-4">
                  {/* Company avatar */}
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0 ${companyColor(job.company)}`}>
                    {job.company.charAt(0).toUpperCase()}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-sm text-gray-900">{job.title}</span>
                      {job.score !== null && <ScoreBadge score={job.score} />}
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5">
                      {job.company}
                      {job.location && <span className="text-gray-300"> / </span>}
                      {job.location}
                      {job.is_remote && <span className="ml-1.5 inline-flex items-center rounded bg-emerald-50 text-emerald-600 text-[10px] font-medium px-1.5 py-0.5">Remote</span>}
                    </p>
                    <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                      {(job.salary_min || job.salary_max) && (
                        <span className="text-xs font-semibold text-gray-700">
                          {formatSalary(job.salary_min, job.salary_max)}
                        </span>
                      )}
                      {job.posted_at && (
                        <span className="text-[11px] text-gray-400">{timeAgo(job.posted_at)}</span>
                      )}
                      <span className="text-[10px] text-gray-300 uppercase tracking-wide">
                        {job.source.replace("jobspy_", "").replace("_", " ")}
                      </span>
                    </div>
                    {job.explanation && (
                      <p className="text-xs text-brand-600/80 mt-1.5 italic line-clamp-1">{job.explanation}</p>
                    )}
                    {!job.explanation && job.description_preview && (
                      <p className="text-xs text-gray-400 mt-1.5 line-clamp-1">{job.description_preview}</p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1.5 shrink-0 pt-0.5">
                    <button
                      onClick={(e) => dismissJob(job.id, e)}
                      className="p-1 rounded-md text-gray-300 opacity-0 group-hover:opacity-100 hover:text-gray-500 hover:bg-gray-100 transition-all"
                      title="Not interested"
                    >
                      <XMarkIcon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => toggleSave(job.id, e)}
                      className={`p-1 rounded-md transition-colors ${
                        saved.has(job.id)
                          ? "text-amber-400 hover:text-amber-500"
                          : "text-gray-300 hover:text-amber-400"
                      } ${savingAnim === job.id ? "animate-save-pulse" : ""}`}
                      title={saved.has(job.id) ? "Unsave" : "Save"}
                    >
                      <BookmarkIcon filled={saved.has(job.id)} className="w-5 h-5" />
                    </button>
                    {job.url && (
                      <a
                        href={job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="rounded-lg border border-brand-200 bg-brand-50 px-3 py-1.5 text-xs font-semibold text-brand-700 hover:bg-brand-100 transition-colors"
                      >
                        Apply
                      </a>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {!loading && status?.has_embedding && jobs.length === 0 && (
          <p className="text-center text-gray-400 text-sm py-16">
            No matches{hasFilters ? " for these filters" : ""}.
            {hasFilters && (
              <button onClick={clearFilters} className="ml-1 text-brand-600 hover:underline">
                Clear filters
              </button>
            )}
          </p>
        )}

        {hasMore && (
          <div className="flex justify-center mt-8">
            <button
              onClick={loadMore}
              disabled={loadingMore}
              className="rounded-xl border border-gray-200 bg-white px-8 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:shadow-card disabled:opacity-40 transition-all"
            >
              {loadingMore ? "Loading..." : "Load more"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
