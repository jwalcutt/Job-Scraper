"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Search jobs</h1>
        <Link href="/jobs" className="text-sm text-brand-600 hover:underline">My matches</Link>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <input
          type="text"
          placeholder="Python engineer, data scientist, product manager…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <select
          value={remote}
          onChange={(e) => setRemote(e.target.value as "" | "true" | "false")}
          className="rounded-lg border border-gray-300 px-2 py-2 text-sm"
        >
          <option value="">Any location</option>
          <option value="true">Remote only</option>
          <option value="false">Onsite only</option>
        </select>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "…" : "Search"}
        </button>
      </form>

      {searchError && (
        <p className="text-sm text-red-600 mb-4">{searchError}</p>
      )}

      {searched && (
        <p className="text-sm text-gray-500 mb-4">
          {jobs.length} result{jobs.length !== 1 ? "s" : ""} for &ldquo;{q}&rdquo;
        </p>
      )}

      <div className="space-y-2">
        {jobs.map((job) => (
          <Link
            key={job.id}
            href={`/jobs/${job.id}`}
            className="block rounded-lg border border-gray-200 bg-white p-4 hover:border-gray-300 hover:shadow-sm transition-all"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-sm text-gray-900">{job.title}</span>
                  {job.score !== null && (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">
                      {Math.round(job.score * 100)}% match
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600 mt-0.5">
                  {job.company}
                  {job.location && ` · ${job.location}`}
                  {job.is_remote && " · Remote"}
                </p>
                {job.description_preview && (
                  <p className="text-xs text-gray-400 mt-1 line-clamp-2">{job.description_preview}</p>
                )}
              </div>
              {job.url && (
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="shrink-0 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700 transition-colors"
                >
                  Apply
                </a>
              )}
            </div>
          </Link>
        ))}
      </div>

      {searched && jobs.length === 0 && (
        <p className="text-center text-gray-400 text-sm py-12">
          No results found. Try different keywords.
        </p>
      )}
    </div>
  );
}
