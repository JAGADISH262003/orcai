"use client";

import { useEffect, useState } from "react";

import { ErrorBanner, Loading } from "@/components/UI";
import { api } from "@/lib/client";
import type { AgencySettings } from "@/lib/types";

type Tab = "general" | "email" | "messaging" | "branding";

const TABS: { key: Tab; label: string }[] = [
  { key: "general", label: "General" },
  { key: "email", label: "Email" },
  { key: "messaging", label: "Messaging" },
  { key: "branding", label: "Branding" },
];

const CURRENCIES = ["USD", "EUR", "GBP", "INR", "CAD", "AUD"];
const TIMEZONES = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Berlin",
  "Asia/Kolkata",
  "Asia/Tokyo",
  "Australia/Sydney",
];

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>("general");
  const [settings, setSettings] = useState<AgencySettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSettings();
      setSettings(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function update<K extends keyof AgencySettings>(key: K, value: AgencySettings[K]) {
    if (!settings) return;
    setSettings({ ...settings, [key]: value });
  }

  function updateNotification(key: string, value: boolean) {
    if (!settings) return;
    setSettings({
      ...settings,
      notification_preferences: { ...settings.notification_preferences, [key]: value },
    });
  }

  async function handleSave() {
    if (!settings) return;
    setSaving(true);
    setError(null);
    setSaveMsg(null);
    try {
      const payload: Record<string, unknown> = {
        default_currency: settings.default_currency,
        timezone: settings.timezone,
        notification_preferences: settings.notification_preferences,
        email_from_name: settings.email_from_name,
        email_from_address: settings.email_from_address,
        email_signature: settings.email_signature,
        whatsapp_number: settings.whatsapp_number,
        telegram_bot_token: settings.telegram_bot_token,
        branding_logo_url: settings.branding_logo_url,
        branding_primary_color: settings.branding_primary_color,
      };
      const updated = await api.updateSettings(payload);
      setSettings(updated);
      setSaveMsg("Settings saved");
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Loading label="Loading settings…" />;
  if (!settings) return <ErrorBanner message="No settings data" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">Agency Settings</h1>
        <p className="text-xs text-[#8a8f98] mt-1">Configure your agency defaults, integrations, and branding.</p>
      </div>

      <div className="flex gap-2 border-b border-white/[0.06] pb-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`px-3 py-1 text-xs font-medium rounded transition ${tab === t.key ? "bg-[#5e6ad2] text-white" : "text-[#8a8f98] hover:text-[#d0d6e0] hover:bg-white/[0.04]"}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <ErrorBanner message={error} />}

      {saveMsg && (
        <div className="p-2.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300">{saveMsg}</div>
      )}

      <div className="linear-card p-5 space-y-4">
        {tab === "general" && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Default Currency</label>
                <select
                  className="linear-input w-full px-3 py-1.5 text-xs"
                  value={settings.default_currency}
                  onChange={(e) => update("default_currency", e.target.value)}
                >
                  {CURRENCIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Timezone</label>
                <select
                  className="linear-input w-full px-3 py-1.5 text-xs"
                  value={settings.timezone}
                  onChange={(e) => update("timezone", e.target.value)}
                >
                  {TIMEZONES.map((tz) => (
                    <option key={tz} value={tz}>{tz}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-2">Notification Preferences</label>
              <div className="space-y-2">
                {Object.entries(settings.notification_preferences).map(([key, val]) => (
                  <label key={key} className="flex items-center space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={val}
                      onChange={(e) => updateNotification(key, e.target.checked)}
                      className="w-4 h-4 rounded border-white/20 bg-white/[0.06] text-[#5e6ad2] focus:ring-[#5e6ad2] focus:ring-offset-0"
                    />
                    <span className="text-xs text-[#d0d6e0]">{key.replace(/_/g, " ")}</span>
                  </label>
                ))}
              </div>
            </div>
          </>
        )}

        {tab === "email" && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">From Name</label>
                <input
                  className="linear-input w-full px-3 py-1.5 text-xs"
                  placeholder="Your Agency Name"
                  value={settings.email_from_name ?? ""}
                  onChange={(e) => update("email_from_name", e.target.value)}
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">From Address</label>
                <input
                  className="linear-input w-full px-3 py-1.5 text-xs"
                  placeholder="noreply@agency.com"
                  value={settings.email_from_address ?? ""}
                  onChange={(e) => update("email_from_address", e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Email Signature</label>
              <textarea
                rows={4}
                className="linear-input w-full px-3 py-2 text-xs"
                placeholder="Best regards,&#10;Your Agency Team"
                value={settings.email_signature ?? ""}
                onChange={(e) => update("email_signature", e.target.value)}
              />
            </div>
          </div>
        )}

        {tab === "messaging" && (
          <div className="space-y-4">
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">WhatsApp Number</label>
              <input
                className="linear-input w-full px-3 py-1.5 text-xs"
                placeholder="+1 555 123 4567"
                value={settings.whatsapp_number ?? ""}
                onChange={(e) => update("whatsapp_number", e.target.value)}
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Telegram Bot Token</label>
              <input
                type="password"
                className="linear-input w-full px-3 py-1.5 text-xs"
                placeholder="123456:ABC-DEF..."
                value={settings.telegram_bot_token ?? ""}
                onChange={(e) => update("telegram_bot_token", e.target.value)}
              />
              <p className="text-[10px] text-[#62666d] mt-1">Token is stored securely and masked in the UI.</p>
            </div>
          </div>
        )}

        {tab === "branding" && (
          <div className="space-y-4">
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Logo URL</label>
              <input
                className="linear-input w-full px-3 py-1.5 text-xs"
                placeholder="https://your-cdn.com/logo.png"
                value={settings.branding_logo_url ?? ""}
                onChange={(e) => update("branding_logo_url", e.target.value)}
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Primary Color</label>
              <div className="flex items-center space-x-3">
                <input
                  type="color"
                  className="w-8 h-8 rounded border border-white/10 cursor-pointer bg-transparent"
                  value={settings.branding_primary_color}
                  onChange={(e) => update("branding_primary_color", e.target.value)}
                />
                <input
                  className="linear-input px-3 py-1.5 text-xs font-mono w-32"
                  placeholder="#5e6ad2"
                  value={settings.branding_primary_color}
                  onChange={(e) => update("branding_primary_color", e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-end pt-3 border-t border-white/[0.06]">
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-4 py-1.5 rounded-md transition shadow disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save Settings"}
          </button>
        </div>
      </div>
    </div>
  );
}
