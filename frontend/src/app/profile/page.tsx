"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { api } from "@/lib/api";

type RemotePreference = "REMOTE" | "HYBRID" | "ONSITE" | "ANY";

interface Profile {
  full_name: string | null;
  location: string | null;
  remote_preference: RemotePreference;
  desired_titles: string[];
  desired_salary_min: number | null;
  desired_salary_max: number | null;
  years_experience: number | null;
  skills: string[];
  has_resume: boolean;
}

interface ResumeVersion {
  id: number;
  label: string;
  is_active: boolean;
  has_embedding: boolean;
  character_count: number;
  uploaded_at: string;
}

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  // Resume versioning
  const [resumes, setResumes] = useState<ResumeVersion[]>([]);
  const [resumeLabel, setResumeLabel] = useState("Default");
  const versionFileRef = useRef<HTMLInputElement>(null);
  const [versionUploadStatus, setVersionUploadStatus] = useState("");

  // Form state
  const [fullName, setFullName] = useState("");
  const [location, setLocation] = useState("");
  const [remotePreference, setRemotePreference] = useState<RemotePreference>("ANY");
  const [desiredTitles, setDesiredTitles] = useState("");
  const [salaryMin, setSalaryMin] = useState("");
  const [salaryMax, setSalaryMax] = useState("");
  const [yearsExp, setYearsExp] = useState("");
  const [skills, setSkills] = useState("");

  useEffect(() => {
    api.get<Profile>("/profile")
      .then((p) => {
        setProfile(p);
        setFullName(p.full_name || "");
        setLocation(p.location || "");
        setRemotePreference(p.remote_preference);
        setDesiredTitles(p.desired_titles.join(", "));
        setSalaryMin(p.desired_salary_min?.toString() || "");
        setSalaryMax(p.desired_salary_max?.toString() || "");
        setYearsExp(p.years_experience?.toString() || "");
        setSkills(p.skills.join(", "));
      })
      .catch(() => router.push("/login"));

    api.get<ResumeVersion[]>("/profile/resumes")
      .then(setResumes)
      .catch(() => {});
  }, [router]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await api.patch("/profile", {
        full_name: fullName || null,
        location: location || null,
        remote_preference: remotePreference,
        desired_titles: desiredTitles.split(",").map((s) => s.trim()).filter(Boolean),
        desired_salary_min: salaryMin ? parseInt(salaryMin) : null,
        desired_salary_max: salaryMax ? parseInt(salaryMax) : null,
        years_experience: yearsExp ? parseInt(yearsExp) : null,
        skills: skills.split(",").map((s) => s.trim()).filter(Boolean),
      });
      router.push("/jobs");
    } finally {
      setSaving(false);
    }
  }

  async function handleResumeUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadStatus("Uploading...");
    const formData = new FormData();
    formData.append("file", file);
    const token = localStorage.getItem("access_token");
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/profile/resume`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (res.ok) {
      const data = await res.json();
      setUploadStatus(`Resume uploaded (${data.characters.toLocaleString()} chars). Embedding queued.`);
    } else {
      setUploadStatus("Upload failed. Only PDF and DOCX are supported.");
    }
  }

  async function handleVersionUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setVersionUploadStatus("Uploading...");
    const formData = new FormData();
    formData.append("file", file);
    const token = localStorage.getItem("access_token");
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/profile/resumes?label=${encodeURIComponent(resumeLabel || "Default")}`,
      {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      }
    );
    if (res.ok) {
      const data: ResumeVersion = await res.json();
      setResumes((prev) => [data, ...prev]);
      setVersionUploadStatus(`"${data.label}" uploaded (${data.character_count.toLocaleString()} chars). Embedding queued.`);
      setResumeLabel("Default");
    } else {
      setVersionUploadStatus("Upload failed. Only PDF and DOCX are supported.");
    }
    if (versionFileRef.current) versionFileRef.current.value = "";
  }

  async function handleActivateResume(id: number) {
    try {
      await api.patch<ResumeVersion>(`/profile/resumes/${id}/activate`, {});
      setResumes((prev) =>
        prev.map((r) => ({ ...r, is_active: r.id === id }))
      );
    } catch { /* silent */ }
  }

  async function handleDeleteResume(id: number) {
    try {
      await api.delete(`/profile/resumes/${id}`);
      setResumes((prev) => prev.filter((r) => r.id !== id));
    } catch { /* silent */ }
  }

  if (!profile) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="flex items-center justify-center py-32 text-gray-400 text-sm">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-gray-900 mb-6">Your Profile</h1>

        {/* Quick resume upload */}
        <div className="mb-6 rounded-xl border-2 border-dashed border-gray-200 bg-white/60 p-6 text-center hover:border-brand-300 hover:bg-brand-50/30 transition-colors cursor-pointer"
          onClick={() => fileRef.current?.click()}
        >
          <p className="text-sm text-gray-600 mb-2">
            {profile.has_resume ? "Resume uploaded. Upload a new one to replace it." : "Upload your resume to improve match quality."}
          </p>
          <span className="inline-block rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700">
            Choose PDF or DOCX
          </span>
          <input ref={fileRef} type="file" accept=".pdf,.docx" className="hidden" onChange={handleResumeUpload} />
          {uploadStatus && <p className="mt-2 text-xs text-gray-500">{uploadStatus}</p>}
        </div>

        {/* Resume Versions */}
        <section className="mb-8 bg-white rounded-xl p-6 shadow-card">
          <h2 className="text-base font-bold text-gray-900 mb-1">Resume versions</h2>
          <p className="text-sm text-gray-500 mb-4">
            Store multiple resume versions. Activate the one to use for matching.
          </p>

          {resumes.length > 0 && (
            <div className="space-y-2 mb-4">
              {resumes.map((r) => (
                <div
                  key={r.id}
                  className={`flex items-center justify-between rounded-xl border px-4 py-3 text-sm transition-colors ${
                    r.is_active
                      ? "border-brand-200 bg-brand-50"
                      : "border-gray-100 bg-gray-50"
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900 truncate">
                      {r.label}
                      {r.is_active && (
                        <span className="ml-2 inline-flex items-center rounded-full bg-brand-100 px-2 py-0.5 text-xs font-bold text-brand-700">
                          Active
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {r.character_count.toLocaleString()} chars
                      {r.has_embedding ? " \u00B7 Embedded" : " \u00B7 Embedding..."}
                      {" \u00B7 "}
                      {new Date(r.uploaded_at).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-3 flex-shrink-0">
                    {!r.is_active && (
                      <button
                        onClick={() => handleActivateResume(r.id)}
                        className="px-2.5 py-1 rounded-lg text-xs font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 transition-colors"
                      >
                        Activate
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteResume(r.id)}
                      className="px-2.5 py-1 rounded-lg text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Label for new version</label>
              <input
                type="text"
                value={resumeLabel}
                onChange={(e) => setResumeLabel(e.target.value)}
                placeholder="e.g. ML Engineer focus"
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition-shadow"
              />
            </div>
            <button
              onClick={() => versionFileRef.current?.click()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 transition-colors shadow-sm whitespace-nowrap"
            >
              Upload resume
            </button>
            <input ref={versionFileRef} type="file" accept=".pdf,.docx" className="hidden" onChange={handleVersionUpload} />
          </div>
          {versionUploadStatus && <p className="mt-2 text-xs text-gray-500">{versionUploadStatus}</p>}
        </section>

        <form onSubmit={handleSave} className="space-y-5 bg-white rounded-xl p-6 shadow-card">
          <h2 className="text-base font-bold text-gray-900 mb-2">Profile details</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Full name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition-shadow"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Location</label>
              <input
                type="text"
                placeholder="San Francisco, CA"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition-shadow"
              />
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Work preference</label>
            <select
              value={remotePreference}
              onChange={(e) => setRemotePreference(e.target.value as RemotePreference)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition-shadow"
            >
              <option value="ANY">Any (remote, hybrid, or onsite)</option>
              <option value="REMOTE">Remote only</option>
              <option value="HYBRID">Hybrid</option>
              <option value="ONSITE">Onsite only</option>
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Desired job titles</label>
            <input
              type="text"
              placeholder="Software Engineer, Backend Developer, Tech Lead"
              value={desiredTitles}
              onChange={(e) => setDesiredTitles(e.target.value)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition-shadow"
            />
            <p className="mt-1 text-xs text-gray-400">Comma-separated</p>
          </div>

          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Skills</label>
            <input
              type="text"
              placeholder="Python, React, AWS, PostgreSQL"
              value={skills}
              onChange={(e) => setSkills(e.target.value)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition-shadow"
            />
            <p className="mt-1 text-xs text-gray-400">Comma-separated</p>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Years exp</label>
              <input
                type="number"
                min={0}
                max={50}
                value={yearsExp}
                onChange={(e) => setYearsExp(e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition-shadow"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Min salary (USD)</label>
              <input
                type="number"
                step={1000}
                value={salaryMin}
                onChange={(e) => setSalaryMin(e.target.value)}
                placeholder="80000"
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition-shadow"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Max salary (USD)</label>
              <input
                type="number"
                step={1000}
                value={salaryMax}
                onChange={(e) => setSalaryMax(e.target.value)}
                placeholder="200000"
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition-shadow"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50 transition-colors shadow-sm"
          >
            {saving ? "Saving..." : "Save profile"}
          </button>
        </form>
      </div>
    </div>
  );
}
