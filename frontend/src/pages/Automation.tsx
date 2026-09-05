import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Bell, Bot, Pause, Play, Square } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  getAutomationRules,
  getUnreadNotificationCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  pauseAutomation,
  startAutomation,
  stopAutomation,
  updateAutomationRules,
} from "@/services/automation";
import type { AutomationState } from "@/types/automation";

const STATE_META: Record<AutomationState, { label: string; classes: string }> = {
  running: { label: "Running", classes: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300" },
  paused: { label: "Paused", classes: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300" },
  stopped: { label: "Stopped", classes: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300" },
};

function TagInput({
  label,
  hint,
  values,
  onChange,
}: {
  label: string;
  hint: string;
  values: string[];
  onChange: (values: string[]) => void;
}) {
  const [draft, setDraft] = useState(values.join(", "));

  useEffect(() => {
    setDraft(values.join(", "));
  }, [values]);

  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-500">{label}</label>
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() =>
          onChange(
            draft
              .split(",")
              .map((t) => t.trim())
              .filter(Boolean)
          )
        }
        placeholder="Comma-separated"
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
      />
      <p className="mt-1 text-xs text-slate-400">{hint}</p>
    </div>
  );
}

function LimitInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | null;
  onChange: (value: number | null) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-500">{label}</label>
      <input
        type="number"
        min={1}
        value={value ?? ""}
        placeholder="Unlimited"
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
      />
    </div>
  );
}

export default function Automation() {
  const queryClient = useQueryClient();
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isSavingRules, setIsSavingRules] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const { data: rules } = useQuery({ queryKey: ["automation-rules"], queryFn: getAutomationRules });
  const { data: notifications, isLoading: notificationsLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => listNotifications(false),
  });
  const { data: unreadCount } = useQuery({
    queryKey: ["notifications-unread-count"],
    queryFn: getUnreadNotificationCount,
  });

  const refreshRules = () => queryClient.invalidateQueries({ queryKey: ["automation-rules"] });
  const refreshNotifications = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["notifications"] }),
      queryClient.invalidateQueries({ queryKey: ["notifications-unread-count"] }),
    ]);

  const handleTransition = async (action: "start" | "pause" | "stop") => {
    setIsTransitioning(true);
    try {
      if (action === "start") await startAutomation();
      if (action === "pause") await pauseAutomation();
      if (action === "stop") await stopAutomation();
      await refreshRules();
    } finally {
      setIsTransitioning(false);
    }
  };

  const saveLimit = async (field: string, value: number | null) => {
    setIsSavingRules(true);
    try {
      await updateAutomationRules({ [field]: value });
      await refreshRules();
      setSaveMessage("Saved.");
      setTimeout(() => setSaveMessage(null), 1500);
    } finally {
      setIsSavingRules(false);
    }
  };

  const saveTags = async (field: string, value: string[]) => {
    setIsSavingRules(true);
    try {
      await updateAutomationRules({ [field]: value });
      await refreshRules();
      setSaveMessage("Saved.");
      setTimeout(() => setSaveMessage(null), 1500);
    } finally {
      setIsSavingRules(false);
    }
  };

  const handleMarkRead = async (id: string) => {
    await markNotificationRead(id);
    await refreshNotifications();
  };

  const handleMarkAllRead = async () => {
    await markAllNotificationsRead();
    await refreshNotifications();
  };

  const state = rules?.state ?? "running";
  const meta = STATE_META[state];

  return (
    <div className="space-y-6 p-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold">
            <Bot size={20} className="text-brand-600" /> Automation
          </h1>
          <p className="text-sm text-slate-500">
            Hard limits and blocklists that Rapid Apply obeys no matter how strong a match looks (spec
            sections 60-62), plus a global kill switch and the in-app notification feed.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${meta.classes}`}>{meta.label}</span>
          <div className="flex gap-2">
            <button
              onClick={() => handleTransition("start")}
              disabled={isTransitioning || state === "running"}
              className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              <Play size={14} /> Start
            </button>
            <button
              onClick={() => handleTransition("pause")}
              disabled={isTransitioning || state !== "running"}
              className="flex items-center gap-1.5 rounded-lg bg-amber-500 px-3 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50"
            >
              <Pause size={14} /> Pause
            </button>
            <button
              onClick={() => handleTransition("stop")}
              disabled={isTransitioning || state === "stopped"}
              className="flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              <Square size={14} /> Stop
            </button>
          </div>
        </div>
      </div>

      {state === "stopped" && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          <AlertTriangle size={16} />
          Automation is stopped. No job will be auto-queued or auto-submitted until you press Start.
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Rate limits</h2>
            {saveMessage && <span className="text-xs text-emerald-600">{saveMessage}</span>}
          </div>
          <div className="space-y-4">
            <LimitInput
              label="Max applications per hour"
              value={rules?.max_applications_per_hour ?? null}
              onChange={(v) => saveLimit("max_applications_per_hour", v)}
            />
            <LimitInput
              label="Max applications per day"
              value={rules?.max_applications_per_day ?? null}
              onChange={(v) => saveLimit("max_applications_per_day", v)}
            />
            <LimitInput
              label="Max applications per company"
              value={rules?.max_applications_per_company ?? null}
              onChange={(v) => saveLimit("max_applications_per_company", v)}
            />
            <p className="text-xs text-slate-400">
              Leave blank for unlimited. These caps apply regardless of match score — once hit, Rapid
              Apply pauses itself for the rest of the window and notifies you below.
            </p>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">Blocklists</h2>
          <div className="space-y-4">
            <TagInput
              label="Blocked sources"
              hint='e.g. "mock", "greenhouse" — jobs from these sources are never auto-queued.'
              values={rules?.blocked_sources ?? []}
              onChange={(v) => saveTags("blocked_sources", v)}
            />
            <TagInput
              label="Blocked companies"
              hint="Case-insensitive substring match against the company name."
              values={rules?.blocked_companies ?? []}
              onChange={(v) => saveTags("blocked_companies", v)}
            />
            <TagInput
              label="Blocked keywords"
              hint="Matched against the job title and description."
              values={rules?.blocked_keywords ?? []}
              onChange={(v) => saveTags("blocked_keywords", v)}
            />
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
            <Bell size={15} /> Notifications
            {unreadCount != null && unreadCount > 0 && (
              <span className="rounded-full bg-brand-600 px-1.5 py-0.5 text-[10px] font-bold text-white">
                {unreadCount}
              </span>
            )}
          </h2>
          <button
            onClick={handleMarkAllRead}
            disabled={!unreadCount}
            className="text-xs font-medium text-brand-600 hover:underline disabled:text-slate-300 disabled:no-underline"
          >
            Mark all as read
          </button>
        </div>

        {notificationsLoading && <p className="text-sm text-slate-500">Loading notifications...</p>}
        {!notificationsLoading && notifications?.length === 0 && (
          <p className="text-sm text-slate-400">
            No notifications yet — submissions, manual-review fallbacks, and rate-limit pauses will show up
            here.
          </p>
        )}
        <div className="space-y-2">
          {notifications?.map((n) => (
            <div
              key={n.id}
              className={`flex items-start justify-between gap-3 rounded-lg border px-3 py-2 text-sm ${
                n.is_read
                  ? "border-slate-100 dark:border-slate-800"
                  : "border-brand-200 bg-brand-50/40 dark:border-brand-900 dark:bg-brand-900/10"
              }`}
            >
              <div>
                <div className="font-medium">{n.title}</div>
                <div className="text-xs text-slate-500">{n.message}</div>
                <div className="mt-1 flex items-center gap-2 text-xs text-slate-400">
                  <span>{new Date(n.created_at).toLocaleString()}</span>
                  {n.application_id && (
                    <Link to={`/applications/${n.application_id}`} className="text-brand-600 hover:underline">
                      View application
                    </Link>
                  )}
                </div>
              </div>
              {!n.is_read && (
                <button
                  onClick={() => handleMarkRead(n.id)}
                  className="shrink-0 text-xs font-medium text-slate-400 hover:text-brand-600"
                >
                  Mark read
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {isSavingRules && <p className="text-xs text-slate-400">Saving...</p>}
    </div>
  );
}
