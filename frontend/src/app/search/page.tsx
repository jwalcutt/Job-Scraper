"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { api, ApiError } from "@/lib/api";

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
  score: number | null;
  description_preview: string | null;
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

export default function SearchPage() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [remote, setRemote] = useState<"" | "true" | "false">("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [searchError, setSearchError] = useState("");

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (q.trim().length < 2) return;
    setLoading(true);
    setSearchError("");
    try {
      const params = new URLSearchParams({ q: q.trim(), limit: "50" });
      if (remote) params.set("remote", remote);
      const data = await api.get<Job[]>(`/jobs/search?${params}`);
      setJobs(data);
      setSearched(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/login");
      } else {
        setSearchError("Search failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-gray-900 mb-6">Search jobs</h1>

        <form onSubmit={handleSearch} className="flex gap-2 mb-6">
          <input
            type="text"
            placeholder="Python engineer, data scientist, product manager..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="flex-1 rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 shadow-card transition-shadow"
          />
          <select
            value={remote}
            onChange={(e) => setRemote(e.target.value as "" | "true" | "false")}
            className="rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm shadow-card"
          >
            <option value="">Any location</option>
            <option value="true">Remote only</option>
            <option value="false">Onsite only</option>
          </select>
          <button
            type="submit"
            disabled={loading}
            className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50 transition-colors shadow-sm"
          >
            {loading ? "..." : "Search"}
          </button>
        </form>

        {searchError && (
          <p className="text-sm text-red-600 mb-4">{searchError}</p>
        )}

        {searched && (
          <p className="text-sm text-gray-400 mb-4">
            {jobs.length} result{jobs.length !== 1 ? "s" : ""} for &ldquo;{q}&rdquo;
          </p>
        )}

        <div className="space-y-2">
          {jobs.map((job, idx) => (
            <div
              key={job.id}
              onClick={() => router.push(`/jobs/${job.id}`)}
              className="rounded-xl bg-white p-4 shadow-card hover:shadow-card-hover hover:-translate-y-px transition-all cursor-pointer animate-card-enter"
              style={{ animationDelay: `${Math.min(idx * 30, 300)}ms` }}
            >
              <div className="flex items-start gap-3">
                <div className={`w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0 ${companyColor(job.company)}`}>
                  {job.company.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-sm text-gray-900">{job.title}</span>
                    {job.score !== null && (
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 ring-1 ring-brand-200 tabular-nums">
                        {Math.round(job.score * 100)}% match
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {job.company}
                    {job.location && <span className="text-gray-300"> / </span>}
                    {job.location}
                    {job.is_remote && <span className="ml-1.5 inline-flex items-center rounded bg-emerald-50 text-emerald-600 text-[10px] font-medium px-1.5 py-0.5">Remote</span>}
                  </p>
                  {job.description_preview && (
                    <p className="text-xs text-gray-400 mt-1.5 line-clamp-2">{job.description_preview}</p>
                  )}
                </div>
                {job.url && (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="shrink-0 rounded-lg border border-brand-200 bg-brand-50 px-3 py-1.5 text-xs font-semibold text-brand-700 hover:bg-brand-100 transition-colors"
                  >
                    Apply
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>

        {searched && jobs.length === 0 && (
          <p className="text-center text-gray-400 text-sm py-16">
            No results found. Try different keywords.
          </p>
        )}
      </div>
    </div>
  );
}
