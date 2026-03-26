"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

interface NotificationSettings {
  notifications_enabled: boolean;
  notification_email: string | null;
  notification_min_score: number;
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
  const [notifSettings, setNotifSettings] = useState<NotificationSettings>({
    notifications_enabled: false,
    notification_email: null,
    notification_min_score: 0.6,
  });
  const [notifEmail, setNotifEmail] = useState("");
  const [notifMinScore, setNotifMinScore] = useState("0.6");
  const [notifEnabled, setNotifEnabled] = useState(false);
  const [notifMsg, setNotifMsg] = useState("");
  const [notifSaving, setNotifSaving] = useState(false);

  // Delete account
  const [showDelete, setShowDelete] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    api.get<NotificationSettings>("/users/me/notifications")
      .then((data) => {
        setNotifSettings(data);
        setNotifEnabled(data.notifications_enabled);
        setNotifEmail(data.notification_email ?? "");
        setNotifMinScore(String(data.notification_min_score));
        setLoading(false);
      })
      .catch(() => router.push("/login"));
  }, [router]);

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setPasswordMsg("New passwords do not match.");
      return;
    }
    if (newPassword.length < 8) {
      setPasswordMsg("Password must be at least 8 characters.");
      return;
    }
    setPasswordSaving(true);
    setPasswordMsg("");
    try {
      await api.post("/users/me/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordMsg("Password updated successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400 text-sm">Loading…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <div className="flex gap-4 text-sm">
          <Link href="/jobs" className="text-brand-600 hover:underline">Matches</Link>
          <Link href="/applications" className="text-gray-500 hover:text-gray-700">Applications</Link>
        </div>
      </div>

      <div className="space-y-6">
        {/* Change Password */}
        <section className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Change password</h2>
          <form onSubmit={handlePasswordChange} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current password</label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">New password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Confirm new password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            {passwordMsg && (
              <p className={`text-sm ${passwordMsg.includes("successfully") ? "text-green-600" : "text-red-600"}`}>
                {passwordMsg}
              </p>
            )}
            <button
              type="submit"
              disabled={passwordSaving}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40 transition-colors"
            >
              {passwordSaving ? "Saving…" : "Update password"}
            </button>
          </form>
        </section>

        {/* Notification Settings */}
        <section className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Email notifications</h2>
          <form onSubmit={handleNotifSave} className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={notifEnabled}
                onChange={(e) => setNotifEnabled(e.target.checked)}
                className="w-4 h-4 text-brand-600 rounded border-gray-300"
              />
              <span className="text-sm font-medium text-gray-700">Send me daily match digests</span>
            </label>

            {notifEnabled && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Notification email <span className="text-gray-400 font-normal">(leave blank to use account email)</span>
                  </label>
                  <input
                    type="email"
                    value={notifEmail}
                    onChange={(e) => setNotifEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Minimum match score: <span className="font-semibold text-brand-600">{Math.round(parseFloat(notifMinScore) * 100)}%</span>
                  </label>
                  <input
                    type="range"
                    min="0.4"
                    max="0.95"
                    step="0.05"
                    value={notifMinScore}
                    onChange={(e) => setNotifMinScore(e.target.value)}
                    className="w-full accent-brand-600"
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-0.5">
                    <span>40% (more results)</span>
                    <span>95% (only the best)</span>
                  </div>
                </div>
              </>
            )}

            {notifMsg && (
              <p className={`text-sm ${notifMsg.includes("saved") ? "text-green-600" : "text-red-600"}`}>
                {notifMsg}
              </p>
            )}
            <button
              type="submit"
              disabled={notifSaving}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40 transition-colors"
            >
              {notifSaving ? "Saving…" : "Save notifications"}
            </button>
          </form>
        </section>

        {/* Danger Zone */}
        <section className="bg-white rounded-xl border border-red-200 p-6">
          <h2 className="text-base font-semibold text-red-700 mb-1">Danger zone</h2>
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
                Type <span className="font-mono font-semibold">delete my account</span> to confirm:
              </p>
              <input
                type="text"
                value={deleteConfirm}
                onChange={(e) => setDeleteConfirm(e.target.value)}
                placeholder="delete my account"
                className="w-full rounded-lg border border-red-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleDeleteAccount}
                  disabled={deleteConfirm !== "delete my account" || deleting}
                  className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-40 transition-colors"
                >
                  {deleting ? "Deleting…" : "Permanently delete account"}
                </button>
                <button
                  onClick={() => { setShowDelete(false); setDeleteConfirm(""); }}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
