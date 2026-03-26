"use client";

import { useEffect, useState } from "react";
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
  const color = pct >= 80 ? "bg-green-100 text-green-800" : pct >= 60 ? "bg-yellow-100 text-yellow-800" : "bg-gray-100 text-gray-600";
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${color}`}>{pct}% match</span>;
}

export default function JobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState<Set<number>>(new Set());

  useEffect(() => {
    api.get<Job[]>("/jobs/matches").then((data) => {
      setJobs(data);
      setLoading(false);
    }).catch(() => router.push("/login"));

    api.get<Job[]>("/jobs/saved").then((data) => {
      setSaved(new Set(data.map((j) => j.id)));
    }).catch(() => {});
  }, [router]);

  async function toggleSave(jobId: number) {
    if (saved.has(jobId)) {
      await api.delete(`/jobs/${jobId}/save`);
      setSaved((s) => { const n = new Set(s); n.delete(jobId); return n; });
    } else {
      await api.post(`/jobs/${jobId}/save`, {});
      setSaved((s) => new Set(s).add(jobId));
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Your matches</h1>
        <div className="flex gap-4">
          <Link href="/saved" className="text-sm text-brand-600 hover:underline">Saved jobs</Link>
          <Link href="/profile" className="text-sm text-gray-600 hover:underline">Edit profile</Link>
        </div>
      </div>

      {loading && <p className="text-gray-500 text-sm">Loading matches...</p>}

      {!loading && jobs.length === 0 && (
        <div className="rounded-lg border border-gray-200 p-8 text-center">
          <p className="text-gray-600 mb-2">No matches yet.</p>
          <p className="text-sm text-gray-500">
            Complete your <Link href="/profile" className="text-brand-600 hover:underline">profile</Link> and
            upload your resume. Matches are computed in the background.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {jobs.map((job) => (
          <div key={job.id} className="rounded-lg border border-gray-200 bg-white p-4 hover:shadow-sm transition-shadow">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-gray-900">{job.title}</span>
                  {job.score !== null && <ScoreBadge score={job.score} />}
                </div>
                <p className="text-sm text-gray-600 mt-0.5">
                  {job.company}
                  {job.location && ` · ${job.location}`}
                  {job.is_remote && " · Remote"}
                </p>
                {(job.salary_min || job.salary_max) && (
                  <p className="text-sm text-gray-500 mt-0.5">{formatSalary(job.salary_min, job.salary_max)}</p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => toggleSave(job.id)}
                  className={`text-xl transition-colors ${saved.has(job.id) ? "text-yellow-400" : "text-gray-300 hover:text-yellow-300"}`}
                  title={saved.has(job.id) ? "Unsave" : "Save"}
                >
                  ★
                </button>
                {job.url && (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
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
    </div>
  );
}
