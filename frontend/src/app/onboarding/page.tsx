"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

const STEPS = ["Resume", "Roles & Skills", "Preferences"] as const;

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);

  // Step 1 — Resume
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadStatus, setUploadStatus] = useState("");

  // Step 2 — Roles & Skills
  const [desiredTitles, setDesiredTitles] = useState("");
  const [skills, setSkills] = useState("");
  const [yearsExp, setYearsExp] = useState("");

  // Step 3 — Preferences
  const [location, setLocation] = useState("");
  const [remotePreference, setRemotePreference] = useState("ANY");
  const [salaryMin, setSalaryMin] = useState("");

  async function handleResumeUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadStatus("Uploading…");
    const formData = new FormData();
    formData.append("file", file);
    const token = localStorage.getItem("access_token");
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/profile/resume`,
      { method: "POST", headers: token ? { Authorization: `Bearer ${token}` } : {}, body: formData }
    );
    if (res.ok) {
      const data = await res.json();
      setUploadStatus(`✓ ${file.name} uploaded (${data.characters.toLocaleString()} chars)`);
    } else {
      setUploadStatus("Upload failed — only PDF and DOCX are supported");
    }
  }

  async function handleFinish() {
    setSaving(true);
    try {
      await api.patch("/profile", {
        desired_titles: desiredTitles.split(",").map((s) => s.trim()).filter(Boolean),
        skills: skills.split(",").map((s) => s.trim()).filter(Boolean),
        years_experience: yearsExp ? parseInt(yearsExp) : null,
        location: location || null,
        remote_preference: remotePreference,
        desired_salary_min: salaryMin ? parseInt(salaryMin) : null,
      });
      router.push("/jobs");
    } finally {
      setSaving(false);
    }
  }

  const canAdvance = [
    true,                                       // Step 0: resume is optional
    desiredTitles.trim().length > 0,            // Step 1: need at least one title
    true,                                       // Step 2: preferences optional
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-lg">
        {/* Progress */}
        <div className="flex items-center gap-2 mb-8">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center gap-2 flex-1">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                i < step ? "bg-brand-600 text-white" :
                i === step ? "bg-brand-600 text-white ring-4 ring-brand-100" :
                "bg-gray-200 text-gray-400"
              }`}>
                {i < step ? "✓" : i + 1}
              </div>
              <span className={`text-xs hidden sm:block ${i === step ? "text-brand-600 font-medium" : "text-gray-400"}`}>
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-0.5 ${i < step ? "bg-brand-600" : "bg-gray-200"}`} />
              )}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          {/* Step 0 — Resume */}
          {step === 0 && (
            <>
              <h2 className="text-lg font-bold text-gray-900 mb-1">Upload your resume</h2>
              <p className="text-sm text-gray-500 mb-5">
                We&apos;ll extract your skills and experience automatically. You can skip this and fill in details manually.
              </p>
              <div
                onClick={() => fileRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                  uploadStatus.startsWith("✓") ? "border-green-300 bg-green-50" : "border-gray-300 hover:border-brand-400 hover:bg-blue-50"
                }`}
              >
                {uploadStatus ? (
                  <p className={`text-sm font-medium ${uploadStatus.startsWith("✓") ? "text-green-700" : "text-red-600"}`}>
                    {uploadStatus}
                  </p>
                ) : (
                  <>
                    <p className="text-3xl mb-2">📄</p>
                    <p className="text-sm font-medium text-gray-700">Click to upload PDF or DOCX</p>
                    <p className="text-xs text-gray-400 mt-1">or drag and drop</p>
                  </>
                )}
              </div>
              <input ref={fileRef} type="file" accept=".pdf,.docx" className="hidden" onChange={handleResumeUpload} />
            </>
          )}

          {/* Step 1 — Roles & Skills */}
          {step === 1 && (
            <>
              <h2 className="text-lg font-bold text-gray-900 mb-1">What roles are you looking for?</h2>
              <p className="text-sm text-gray-500 mb-5">
                These drive which jobs we surface for you. Be specific.
              </p>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Desired job titles <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="Software Engineer, Backend Developer, Tech Lead"
                    value={desiredTitles}
                    onChange={(e) => setDesiredTitles(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                  <p className="mt-1 text-xs text-gray-400">Comma-separated</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Key skills</label>
                  <input
                    type="text"
                    placeholder="Python, React, AWS, PostgreSQL, Docker"
                    value={skills}
                    onChange={(e) => setSkills(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                  <p className="mt-1 text-xs text-gray-400">Comma-separated</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Years of experience</label>
                  <input
                    type="number"
                    min={0}
                    max={50}
                    value={yearsExp}
                    onChange={(e) => setYearsExp(e.target.value)}
                    className="w-32 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
              </div>
            </>
          )}

          {/* Step 2 — Preferences */}
          {step === 2 && (
            <>
              <h2 className="text-lg font-bold text-gray-900 mb-1">Location & preferences</h2>
              <p className="text-sm text-gray-500 mb-5">Help us filter out roles that don&apos;t fit.</p>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Your location</label>
                  <input
                    type="text"
                    placeholder="San Francisco, CA"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Work preference</label>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { val: "ANY", label: "Open to all" },
                      { val: "REMOTE", label: "Remote only" },
                      { val: "HYBRID", label: "Hybrid" },
                      { val: "ONSITE", label: "Onsite only" },
                    ].map(({ val, label }) => (
                      <button
                        key={val}
                        type="button"
                        onClick={() => setRemotePreference(val)}
                        className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                          remotePreference === val
                            ? "border-brand-600 bg-brand-50 text-brand-700"
                            : "border-gray-300 text-gray-600 hover:bg-gray-50"
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Minimum salary (USD/yr)</label>
                  <input
                    type="number"
                    step={5000}
                    placeholder="80000"
                    value={salaryMin}
                    onChange={(e) => setSalaryMin(e.target.value)}
                    className="w-48 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
              </div>
            </>
          )}

          {/* Navigation */}
          <div className="flex justify-between mt-6 pt-4 border-t border-gray-100">
            <button
              onClick={() => step > 0 ? setStep(step - 1) : router.push("/jobs")}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              {step === 0 ? "Skip setup" : "← Back"}
            </button>
            {step < STEPS.length - 1 ? (
              <button
                onClick={() => setStep(step + 1)}
                disabled={!canAdvance[step]}
                className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40 transition-colors"
              >
                Continue →
              </button>
            ) : (
              <button
                onClick={handleFinish}
                disabled={saving}
                className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40 transition-colors"
              >
                {saving ? "Saving…" : "Find my matches →"}
              </button>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-4">
          You can always update these in your profile settings.
        </p>
      </div>
    </div>
  );
}
