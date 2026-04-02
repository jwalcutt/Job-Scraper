"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { api } from "@/lib/api";

interface NotificationSettings {
  notifications_enabled: boolean;
  notification_email: string | null;
  notification_min_score: number;
}

interface JobAlert {
  id: number;
  title: string | null;
  location: string | null;
  remote: boolean | null;
  min_score: number;
  is_active: boolean;
  last_alerted_at: string | null;
  created_at: string;
}

export default function SettingsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);

  // Password change
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordMsg, setPasswordMsg] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);

  // Notifications
  const [notifEmail, setNotifEmail] = useState("");
  const [notifMinScore, setNotifMinScore] = useState("0.6");
  const [notifEnabled, setNotifEnabled] = useState(false);
  const [notifMsg, setNotifMsg] = useState("");
  const [notifSaving, setNotifSaving] = useState(false);

  // Job Alerts
  const [alerts, setAlerts] = useState<JobAlert[]>([]);
  const [alertTitle, setAlertTitle] = useState("");
  const [alertLocation, setAlertLocation] = useState("");
  const [alertRemote, setAlertRemote] = useState<string>("any");
  const [alertMinScore, setAlertMinScore] = useState("0.6");
  const [alertMsg, setAlertMsg] = useState("");
  const [alertCreating, setAlertCreating] = useState(false);

  // Delete account
  const [showDelete, setShowDelete] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    api.get<NotificationSettings>("/users/me/notifications")
      .then((notif) => {
        setNotifEnabled(notif.notifications_enabled);
        setNotifEmail(notif.notification_email ?? "");
        setNotifMinScore(String(notif.notification_min_score));
        setLoading(false);
      })
      .catch(() => router.push("/login"));

    api.get<JobAlert[]>("/alerts")
      .then(setAlerts)
      .catch(() => {});
  }, [router]);

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword !== confirmPassword) { setPasswordMsg("New passwords do not match."); return; }
    if (newPassword.length < 8) { setPasswordMsg("Password must be at least 8 characters."); return; }
    setPasswordSaving(true);
    setPasswordMsg("");
    try {
      await api.post("/users/me/change-password", { current_password: currentPassword, new_password: newPassword });
      setPasswordMsg("Password updated successfully.");
      setCurrentPassword(""); setNewPassword(""); setConfirmPassword("");
    } catch {
      setPasswordMsg("Failed to update password. Check your current password.");
    } finally {
      setPasswordSaving(false);
    }
  }

  async function handleNotifSave(e: React.FormEvent) {
    e.preventDefault();
    setNotifSaving(true);
    setNotifMsg("");
    try {
      await api.patch("/users/me/notifications", {
        notifications_enabled: notifEnabled,
        notification_email: notifEmail || null,
        notification_min_score: parseFloat(notifMinScore) || 0.6,
      });
      setNotifMsg("Notification settings saved.");
    } catch {
      setNotifMsg("Failed to save notification settings.");
    } finally {
      setNotifSaving(false);
    }
  }

  async function handleCreateAlert(e: React.FormEvent) {
    e.preventDefault();
    setAlertCreating(true);
    setAlertMsg("");
    try {
      const newAlert = await api.post<JobAlert>("/alerts", {
        title: alertTitle || null,
        location: alertLocation || null,
        remote: alertRemote === "any" ? null : alertRemote === "true",
        min_score: parseFloat(alertMinScore) || 0.6,
      });
      setAlerts((prev) => [newAlert, ...prev]);
      setAlertTitle(""); setAlertLocation(""); setAlertRemote("any"); setAlertMinScore("0.6");
      setAlertMsg("Alert created. You'll receive emails when matching jobs are found.");
    } catch {
      setAlertMsg("Failed to create alert.");
    } finally {
      setAlertCreating(false);
    }
  }

  async function handleDeleteAlert(alertId: number) {
    try {
      await api.delete(`/alerts/${alertId}`);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch { /* silent */ }
  }

  async function handleToggleAlert(alertId: number) {
    try {
      const updated = await api.patch<JobAlert>(`/alerts/${alertId}`, {});
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? updated : a)));
    } catch { /* silent */ }
  }

  async function handleDeleteAccount() {
    if (deleteConfirm !== "delete my account") return;
    setDeleting(true);
    try {
      await api.delete("/users/me");
      localStorage.removeItem("access_token");
      router.push("/");
    } catch {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="flex items-center justify-center py-32 text-gray-400 text-sm">Loading...</div>
      </div>
    );
  }

  const inputClass = "w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition-shadow";

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-gray-900 mb-6">Settings</h1>

        <div className="space-y-4">
          {/* Change Password */}
          <section className="bg-white rounded-xl p-6 shadow-card">
            <h2 className="text-base font-bold text-gray-900 mb-4">Change password</h2>
            <form onSubmit={handlePasswordChange} className="space-y-3">
              <div>
                <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Current password</label>
                <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} required className={inputClass} />
              </div>
              <div>
                <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">New password</label>
                <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8} className={inputClass} />
              </div>
              <div>
                <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Confirm new password</label>
                <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required className={inputClass} />
              </div>
              {passwordMsg && (
                <p className={`text-sm ${passwordMsg.includes("successfully") ? "text-green-600" : "text-red-600"}`}>{passwordMsg}</p>
              )}
              <button type="submit" disabled={passwordSaving} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40 transition-colors shadow-sm">
                {passwordSaving ? "Saving..." : "Update password"}
              </button>
            </form>
          </section>

          {/* Notification Settings */}
          <section className="bg-white rounded-xl p-6 shadow-card">
            <h2 className="text-base font-bold text-gray-900 mb-4">Email notifications</h2>
            <form onSubmit={handleNotifSave} className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" checked={notifEnabled} onChange={(e) => setNotifEnabled(e.target.checked)} className="w-4 h-4 text-brand-600 rounded border-gray-300" />
                <span className="text-sm font-medium text-gray-700">Send me daily match digests</span>
              </label>

              {notifEnabled && (
                <>
                  <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">
                      Notification email <span className="normal-case font-normal">(leave blank to use account email)</span>
                    </label>
                    <input type="email" value={notifEmail} onChange={(e) => setNotifEmail(e.target.value)} placeholder="you@example.com" className={inputClass} />
                  </div>
                  <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">
                      Minimum match score: <span className="text-brand-600">{Math.round(parseFloat(notifMinScore) * 100)}%</span>
                    </label>
                    <input type="range" min="0.4" max="0.95" step="0.05" value={notifMinScore} onChange={(e) => setNotifMinScore(e.target.value)} className="w-full accent-brand-600" />
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>40% (more results)</span>
                      <span>95% (only the best)</span>
                    </div>
                  </div>
                </>
              )}

              {notifMsg && (
                <p className={`text-sm ${notifMsg.includes("saved") ? "text-green-600" : "text-red-600"}`}>{notifMsg}</p>
              )}
              <button type="submit" disabled={notifSaving} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40 transition-colors shadow-sm">
                {notifSaving ? "Saving..." : "Save notifications"}
              </button>
            </form>
          </section>

          {/* Job Alerts */}
          <section className="bg-white rounded-xl p-6 shadow-card">
            <h2 className="text-base font-bold text-gray-900 mb-1">Job alerts</h2>
            <p className="text-sm text-gray-500 mb-4">
              Create saved searches. We&apos;ll email you when new matching jobs are found (checked every 6 hours).
            </p>

            {alerts.length > 0 && (
              <div className="space-y-2 mb-5">
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`flex items-center justify-between rounded-xl border px-4 py-3 text-sm transition-colors ${
                      alert.is_active ? "border-gray-100 bg-gray-50" : "border-gray-100 bg-gray-50/50 opacity-60"
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-900 truncate">
                        {[
                          alert.title && `"${alert.title}"`,
                          alert.location,
                          alert.remote === true ? "Remote" : alert.remote === false ? "Onsite" : null,
                        ].filter(Boolean).join(" \u00B7 ") || "All matches"}
                      </div>
                      <div className="text-xs text-gray-400 mt-0.5">
                        Min score: {Math.round(alert.min_score * 100)}%
                        {alert.last_alerted_at && ` \u00B7 Last sent: ${new Date(alert.last_alerted_at).toLocaleDateString()}`}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-3 flex-shrink-0">
                      <button
                        onClick={() => handleToggleAlert(alert.id)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                          alert.is_active
                            ? "text-yellow-700 bg-yellow-50 hover:bg-yellow-100"
                            : "text-green-700 bg-green-50 hover:bg-green-100"
                        }`}
                      >
                        {alert.is_active ? "Pause" : "Resume"}
                      </button>
                      <button
                        onClick={() => handleDeleteAlert(alert.id)}
                        className="px-2.5 py-1 rounded-lg text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <form onSubmit={handleCreateAlert} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Job title keyword</label>
                  <input type="text" value={alertTitle} onChange={(e) => setAlertTitle(e.target.value)} placeholder="e.g. Backend Engineer" className={inputClass} />
                </div>
                <div>
                  <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Location</label>
                  <input type="text" value={alertLocation} onChange={(e) => setAlertLocation(e.target.value)} placeholder="e.g. San Francisco" className={inputClass} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Remote preference</label>
                  <select value={alertRemote} onChange={(e) => setAlertRemote(e.target.value)} className={inputClass}>
                    <option value="any">Any</option>
                    <option value="true">Remote only</option>
                    <option value="false">Onsite only</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">
                    Min score: {Math.round(parseFloat(alertMinScore) * 100)}%
                  </label>
                  <input type="range" min="0.4" max="0.95" step="0.05" value={alertMinScore} onChange={(e) => setAlertMinScore(e.target.value)} className="w-full accent-brand-600 mt-1.5" />
                </div>
              </div>

              {alertMsg && (
                <p className={`text-sm ${alertMsg.includes("created") ? "text-green-600" : "text-red-600"}`}>{alertMsg}</p>
              )}
              <button type="submit" disabled={alertCreating} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40 transition-colors shadow-sm">
                {alertCreating ? "Creating..." : "Create alert"}
              </button>
            </form>
          </section>

          {/* Danger Zone */}
          <section className="bg-white rounded-xl border border-red-200 p-6 shadow-card">
            <h2 className="text-base font-bold text-red-700 mb-1">Danger zone</h2>
            <p className="text-sm text-gray-500 mb-4">
              Deleting your account removes all your data permanently. This cannot be undone.
            </p>
            {!showDelete ? (
              <button
                onClick={() => setShowDelete(true)}
                className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
              >
                Delete my account
              </button>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-gray-700">
                  Type <span className="font-mono font-bold">delete my account</span> to confirm:
                </p>
                <input
                  type="text"
                  value={deleteConfirm}
                  onChange={(e) => setDeleteConfirm(e.target.value)}
                  placeholder="delete my account"
                  className="w-full rounded-lg border border-red-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400/30"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleDeleteAccount}
                    disabled={deleteConfirm !== "delete my account" || deleting}
                    className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-40 transition-colors"
                  >
                    {deleting ? "Deleting..." : "Permanently delete account"}
                  </button>
                  <button
                    onClick={() => { setShowDelete(false); setDeleteConfirm(""); }}
                    className="rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
