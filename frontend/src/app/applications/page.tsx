"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

interface Application {
  id: number;
  job_id: number;
  applied_at: string;
  status: string;
  notes: string | null;
  job_title: string;
  job_company: string;
  job_location: string | null;
  job_is_remote: boolean;
  job_url: string | null;
  job_salary_min: number | null;
  job_salary_max: number | null;
}

const STATUS_FLOW = ["applied", "phone_screen", "interview", "offer", "rejected", "withdrawn"] as const;
type Status = typeof STATUS_FLOW[number];

const STATUS_META: Record<Status, { label: string; color: string }> = {
  applied:      { label: "Applied",       color: "bg-blue-100 text-blue-700" },
  phone_screen: { label: "Phone screen",  color: "bg-purple-100 text-purple-700" },
  interview:    { label: "Interview",     color: "bg-yellow-100 text-yellow-700" },
  offer:        { label: "Offer!",        color: "bg-green-100 text-green-700" },
  rejected:     { label: "Rejected",      color: "bg-red-100 text-red-600" },
  withdrawn:    { label: "Withdrawn",     color: "bg-gray-100 text-gray-500" },
};

const ACTIVE_STATUSES: Status[] = ["applied", "phone_screen", "interview", "offer"];
const CLOSED_STATUSES: Status[] = ["rejected", "withdrawn"];

function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_META[status as Status] ?? { label: status, color: "bg-gray-100 text-gray-600" };
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${meta.color}`}>{meta.label}</span>;
}

function formatSalary(min: number | null, max: number | null) {
  if (!min && !max) return null;
  const fmt = (n: number) => `$${(n / 1000).toFixed(0)}k`;
  if (min && max) return `${fmt(min)}–${fmt(max)}`;
  return min ? `${fmt(min)}+` : `up to ${fmt(max!)}`;
}

export default function ApplicationsPage() {
  const router = useRouter();
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"active" | "closed">("active");
  const [editingNotes, setEditingNotes] = useState<number | null>(null);
  const [notesDraft, setNotesDraft] = useState("");

  useEffect(() => {
    api.get<Application[]>("/applications")
      .then((data) => { setApps(data); setLoading(false); })
      .catch(() => router.push("/login"));
  }, [router]);

  async function updateStatus(id: number, status: string) {
    const updated = await api.patch<Application>(`/applications/${id}`, { status });
    setApps((prev) => prev.map((a) => (a.id === id ? updated : a)));
  }

  async function saveNotes(id: number) {
    const updated = await api.patch<Application>(`/applications/${id}`, { notes: notesDraft });
    setApps((prev) => prev.map((a) => (a.id === id ? updated : a)));
    setEditingNotes(null);
  }

  async function remove(id: number) {
    await api.delete(`/applications/${id}`);
    setApps((prev) => prev.filter((a) => a.id !== id));
  }

  const visible = apps.filter((a) =>
    tab === "active" ? ACTIVE_STATUSES.includes(a.status as Status) : CLOSED_STATUSES.includes(a.status as Status)
  );

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Applications</h1>
        <div className="flex gap-4 text-sm">
          <Link href="/jobs" className="text-brand-600 hover:underline">Matches</Link>
          <Link href="/saved" className="text-gray-500 hover:text-gray-700">Saved</Link>
        </div>
      </div>

      {/* Summary bar */}
      {!loading && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          {(["applied", "phone_screen", "interview", "offer"] as Status[]).map((s) => {
            const count = apps.filter((a) => a.status === s).length;
            const meta = STATUS_META[s];
            return (
              <div key={s} className="rounded-lg border border-gray-200 bg-white p-3 text-center">
                <p className="text-2xl font-bold text-gray-900">{count}</p>
                <p className={`text-xs font-medium mt-0.5 ${meta.color.split(" ")[1]}`}>{meta.label}</p>
              </div>
            );
          })}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {(["active", "closed"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t ? "border-brand-600 text-brand-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "active" ? "In progress" : "Closed"}
            <span className="ml-1.5 text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full">
              {apps.filter((a) => (t === "active" ? ACTIVE_STATUSES : CLOSED_STATUSES).includes(a.status as Status)).length}
            </span>
          </button>
        ))}
      </div>

      {loading && <p className="text-gray-400 text-sm py-8 text-center">Loading…</p>}

      {!loading && visible.length === 0 && (
        <div className="text-center py-12 text-gray-400 text-sm">
          {tab === "active"
            ? <>No active applications yet. <Link href="/jobs" className="text-brand-600 hover:underline">Find jobs →</Link></>
            : "No closed applications."}
        </div>
      )}

      <div className="space-y-3">
        {visible.map((app) => (
          <div key={app.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <Link href={`/jobs/${app.job_id}`} className="font-semibold text-sm text-gray-900 hover:underline">
                    {app.job_title}
                  </Link>
                  <StatusBadge status={app.status} />
                </div>
                <p className="text-sm text-gray-600 mt-0.5">
                  {app.job_company}
                  {app.job_location && ` · ${app.job_location}`}
                  {app.job_is_remote && " · Remote"}
                </p>
                {formatSalary(app.job_salary_min, app.job_salary_max) && (
                  <p className="text-xs text-gray-400 mt-0.5">{formatSalary(app.job_salary_min, app.job_salary_max)}</p>
                )}
                <p className="text-xs text-gray-400 mt-1">
                  Applied {new Date(app.applied_at).toLocaleDateString()}
                </p>
              </div>

              {/* Status selector */}
              <select
                value={app.status}
                onChange={(e) => updateStatus(app.id, e.target.value)}
                className="text-xs rounded border border-gray-300 px-2 py-1 shrink-0"
              >
                {STATUS_FLOW.map((s) => (
                  <option key={s} value={s}>{STATUS_META[s].label}</option>
                ))}
              </select>
            </div>

            {/* Notes */}
            <div className="mt-3">
              {editingNotes === app.id ? (
                <div className="flex gap-2">
                  <textarea
                    value={notesDraft}
                    onChange={(e) => setNotesDraft(e.target.value)}
                    rows={2}
                    placeholder="Add notes…"
                    className="flex-1 rounded border border-gray-300 px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  <div className="flex flex-col gap-1">
                    <button
                      onClick={() => saveNotes(app.id)}
                      className="rounded bg-brand-600 px-2 py-1 text-xs text-white hover:bg-brand-700"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingNotes(null)}
                      className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-500"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start justify-between gap-2">
                  {app.notes
                    ? <p className="text-xs text-gray-500 flex-1">{app.notes}</p>
                    : <p className="text-xs text-gray-300">No notes</p>
                  }
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={() => { setNotesDraft(app.notes ?? ""); setEditingNotes(app.id); }}
                      className="text-xs text-gray-400 hover:text-gray-600"
                    >
                      {app.notes ? "Edit notes" : "+ Notes"}
                    </button>
                    {app.job_url && (
                      <a href={app.job_url} target="_blank" rel="noopener noreferrer"
                        className="text-xs text-brand-600 hover:underline">
                        Posting →
                      </a>
                    )}
                    <button
                      onClick={() => remove(app.id)}
                      className="text-xs text-gray-300 hover:text-red-400"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
