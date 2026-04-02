"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Nav from "@/components/Nav";
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

const STATUS_META: Record<Status, { label: string; color: string; ring: string }> = {
  applied:      { label: "Applied",       color: "bg-blue-50 text-blue-700",     ring: "ring-blue-200" },
  phone_screen: { label: "Phone screen",  color: "bg-purple-50 text-purple-700", ring: "ring-purple-200" },
  interview:    { label: "Interview",     color: "bg-yellow-50 text-yellow-700", ring: "ring-yellow-200" },
  offer:        { label: "Offer!",        color: "bg-green-50 text-green-700",   ring: "ring-green-200" },
  rejected:     { label: "Rejected",      color: "bg-red-50 text-red-600",       ring: "ring-red-200" },
  withdrawn:    { label: "Withdrawn",     color: "bg-gray-50 text-gray-500",     ring: "ring-gray-200" },
};

const ACTIVE_STATUSES: Status[] = ["applied", "phone_screen", "interview", "offer"];
const CLOSED_STATUSES: Status[] = ["rejected", "withdrawn"];

function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_META[status as Status] ?? { label: status, color: "bg-gray-50 text-gray-600", ring: "ring-gray-200" };
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ring-1 ${meta.color} ${meta.ring}`}>{meta.label}</span>;
}

function formatSalary(min: number | null, max: number | null) {
  if (!min && !max) return null;
  const fmt = (n: number) => `$${(n / 1000).toFixed(0)}k`;
  if (min && max) return `${fmt(min)} - ${fmt(max)}`;
  return min ? `${fmt(min)}+` : `up to ${fmt(max!)}`;
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
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-gray-900 mb-6">Applications</h1>

        {/* Summary bar */}
        {!loading && (
          <div className="grid grid-cols-4 gap-3 mb-6">
            {(["applied", "phone_screen", "interview", "offer"] as Status[]).map((s) => {
              const count = apps.filter((a) => a.status === s).length;
              const meta = STATUS_META[s];
              return (
                <div key={s} className="rounded-xl bg-white p-4 text-center shadow-card">
                  <p className="text-2xl font-extrabold text-gray-900 tabular-nums">{count}</p>
                  <p className={`text-xs font-medium mt-0.5 ${meta.color.split(" ")[1]}`}>{meta.label}</p>
                </div>
              );
            })}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-5">
          {(["active", "closed"] as const).map((t) => {
            const count = apps.filter((a) => (t === "active" ? ACTIVE_STATUSES : CLOSED_STATUSES).includes(a.status as Status)).length;
            return (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm font-medium rounded-full transition-colors ${
                  tab === t
                    ? "bg-brand-600 text-white"
                    : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                }`}
              >
                {t === "active" ? "In progress" : "Closed"}
                <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full ${
                  tab === t ? "bg-brand-500/30 text-white" : "bg-gray-100 text-gray-500"
                }`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {loading && <p className="text-gray-400 text-sm py-8 text-center">Loading...</p>}

        {!loading && visible.length === 0 && (
          <div className="text-center py-16 text-gray-400 text-sm">
            {tab === "active"
              ? <>No active applications yet. <Link href="/jobs" className="text-brand-600 hover:underline">Find jobs</Link></>
              : "No closed applications."}
          </div>
        )}

        <div className="space-y-2">
          {visible.map((app, idx) => (
            <div
              key={app.id}
              className="rounded-xl bg-white p-4 shadow-card animate-card-enter"
              style={{ animationDelay: `${Math.min(idx * 40, 400)}ms` }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 min-w-0 flex-1">
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0 ${companyColor(app.job_company)}`}>
                    {app.job_company.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link href={`/jobs/${app.job_id}`} className="font-bold text-sm text-gray-900 hover:underline">
                        {app.job_title}
                      </Link>
                      <StatusBadge status={app.status} />
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5">
                      {app.job_company}
                      {app.job_location && <span className="text-gray-300"> / </span>}
                      {app.job_location}
                      {app.job_is_remote && <span className="ml-1.5 inline-flex items-center rounded bg-emerald-50 text-emerald-600 text-[10px] font-medium px-1.5 py-0.5">Remote</span>}
                    </p>
                    {formatSalary(app.job_salary_min, app.job_salary_max) && (
                      <p className="text-xs font-semibold text-gray-600 mt-0.5">{formatSalary(app.job_salary_min, app.job_salary_max)}</p>
                    )}
                    <p className="text-[11px] text-gray-400 mt-1">
                      Applied {new Date(app.applied_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>

                <select
                  value={app.status}
                  onChange={(e) => updateStatus(app.id, e.target.value)}
                  className="text-xs rounded-lg border border-gray-200 bg-white px-2 py-1.5 shrink-0"
                >
                  {STATUS_FLOW.map((s) => (
                    <option key={s} value={s}>{STATUS_META[s].label}</option>
                  ))}
                </select>
              </div>

              {/* Notes */}
              <div className="mt-3 ml-12">
                {editingNotes === app.id ? (
                  <div className="flex gap-2">
                    <textarea
                      value={notesDraft}
                      onChange={(e) => setNotesDraft(e.target.value)}
                      rows={2}
                      placeholder="Add notes..."
                      className="flex-1 rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400"
                    />
                    <div className="flex flex-col gap-1">
                      <button
                        onClick={() => saveNotes(app.id)}
                        className="rounded-lg bg-brand-600 px-2.5 py-1 text-xs text-white hover:bg-brand-700 transition-colors"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setEditingNotes(null)}
                        className="rounded-lg border border-gray-200 px-2.5 py-1 text-xs text-gray-500 hover:bg-gray-50 transition-colors"
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
                        className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
                      >
                        {app.notes ? "Edit" : "+ Notes"}
                      </button>
                      {app.job_url && (
                        <a href={app.job_url} target="_blank" rel="noopener noreferrer"
                          className="text-xs text-brand-600 hover:text-brand-700 transition-colors">
                          Posting
                        </a>
                      )}
                      <button
                        onClick={() => remove(app.id)}
                        className="text-xs text-gray-300 hover:text-red-400 transition-colors"
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
    </div>
  );
}
