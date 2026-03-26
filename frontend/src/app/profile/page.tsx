"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
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

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

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
    api.get<Profile>("/profile").then((p) => {
      setProfile(p);
      setFullName(p.full_name || "");
      setLocation(p.location || "");
      setRemotePreference(p.remote_preference);
      setDesiredTitles(p.desired_titles.join(", "));
      setSalaryMin(p.desired_salary_min?.toString() || "");
      setSalaryMax(p.desired_salary_max?.toString() || "");
      setYearsExp(p.years_experience?.toString() || "");
      setSkills(p.skills.join(", "));
    }).catch(() => router.push("/login"));
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

  if (!profile) return <div className="flex min-h-screen items-center justify-center">Loading...</div>;

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Your Profile</h1>
        <a href="/jobs" className="text-sm text-brand-600 hover:underline">View matches</a>
      </div>

      {/* Resume upload */}
      <div className="mb-8 rounded-lg border border-dashed border-gray-300 p-6 text-center">
        <p className="text-sm text-gray-600 mb-3">
          {profile.has_resume ? "Resume uploaded. Upload a new one to replace it." : "Upload your resume to improve match quality."}
        </p>
        <button
          onClick={() => fileRef.current?.click()}
          className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 transition-colors"
        >
          Choose PDF or DOCX
        </button>
        <input ref={fileRef} type="file" accept=".pdf,.docx" className="hidden" onChange={handleResumeUpload} />
        {uploadStatus && <p className="mt-2 text-xs text-gray-500">{uploadStatus}</p>}
      </div>

      <form onSubmit={handleSave} className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
            <input
              type="text"
              placeholder="San Francisco, CA"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Work preference</label>
          <select
            value={remotePreference}
            onChange={(e) => setRemotePreference(e.target.value as RemotePreference)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="ANY">Any (remote, hybrid, or onsite)</option>
            <option value="REMOTE">Remote only</option>
            <option value="HYBRID">Hybrid</option>
            <option value="ONSITE">Onsite only</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Desired job titles</label>
          <input
            type="text"
            placeholder="Software Engineer, Backend Developer, Tech Lead"
            value={desiredTitles}
            onChange={(e) => setDesiredTitles(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <p className="mt-1 text-xs text-gray-500">Comma-separated</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Skills</label>
          <input
            type="text"
            placeholder="Python, React, AWS, PostgreSQL"
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <p className="mt-1 text-xs text-gray-500">Comma-separated</p>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Years experience</label>
            <input
              type="number"
              min={0}
              max={50}
              value={yearsExp}
              onChange={(e) => setYearsExp(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Min salary (USD)</label>
            <input
              type="number"
              step={1000}
              value={salaryMin}
              onChange={(e) => setSalaryMin(e.target.value)}
              placeholder="80000"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max salary (USD)</label>
            <input
              type="number"
              step={1000}
              value={salaryMax}
              onChange={(e) => setSalaryMax(e.target.value)}
              placeholder="200000"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          {saving ? "Saving..." : "Save profile"}
        </button>
      </form>
    </div>
  );
}
