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
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Saved jobs</h1>
        <Link href="/jobs" className="text-sm text-brand-600 hover:underline">Back to matches</Link>
      </div>

      {loading && <p className="text-gray-500 text-sm">Loading...</p>}
      {!loading && jobs.length === 0 && (
        <p className="text-gray-500 text-sm">No saved jobs yet. Star a job on the matches page to save it here.</p>
      )}

      <div className="space-y-3">
        {jobs.map((job) => (
          <div key={job.id} className="rounded-lg border border-gray-200 bg-white p-4 flex items-center justify-between gap-3">
            <div>
              <p className="font-semibold text-gray-900">{job.title}</p>
              <p className="text-sm text-gray-600">
                {job.company}{job.location && ` · ${job.location}`}{job.is_remote && " · Remote"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => unsave(job.id)}
                className="text-xs text-gray-500 hover:text-red-500 transition-colors"
              >
                Remove
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
        ))}
      </div>
    </div>
  );
}
