"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { BookmarkIcon } from "@/components/Icons";
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

export default function SavedPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Job[]>("/jobs/saved")
      .then((data) => { setJobs(data); setLoading(false); })
      .catch(() => router.push("/login"));
  }, [router]);

  async function unsave(jobId: number) {
    await api.delete(`/jobs/${jobId}/save`);
    setJobs((prev) => prev.filter((j) => j.id !== jobId));
  }

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-gray-900 mb-6">Saved jobs</h1>

        {loading && <p className="text-gray-400 text-sm py-8">Loading...</p>}
        {!loading && jobs.length === 0 && (
          <div className="text-center py-16">
            <BookmarkIcon filled={false} className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No saved jobs yet.</p>
            <p className="text-gray-400 text-xs mt-1">Save a job on the matches page to see it here.</p>
          </div>
        )}

        <div className="space-y-2">
          {jobs.map((job, idx) => (
            <div
              key={job.id}
              onClick={() => router.push(`/jobs/${job.id}`)}
              className="rounded-xl bg-white p-4 shadow-card hover:shadow-card-hover hover:-translate-y-px transition-all cursor-pointer animate-card-enter"
              style={{ animationDelay: `${Math.min(idx * 40, 400)}ms` }}
            >
              <div className="flex items-center gap-3">
                <div className={`w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0 ${companyColor(job.company)}`}>
                  {job.company.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-sm text-gray-900">{job.title}</p>
                  <p className="text-sm text-gray-500">
                    {job.company}
                    {job.location && <span className="text-gray-300"> / </span>}
                    {job.location}
                    {job.is_remote && <span className="ml-1.5 inline-flex items-center rounded bg-emerald-50 text-emerald-600 text-[10px] font-medium px-1.5 py-0.5">Remote</span>}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={(e) => { e.stopPropagation(); unsave(job.id); }}
                    className="text-xs text-gray-400 hover:text-red-500 transition-colors"
                  >
                    Remove
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
          ))}
        </div>
      </div>
    </div>
  );
}
