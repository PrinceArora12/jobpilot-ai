import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BarChart3,
  Bell,
  Bot,
  Briefcase,
  Calendar,
  FileText,
  LayoutDashboard,
  LogOut,
  Rocket,
  Settings,
  User as UserIcon,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "@/hooks/useAuth";
import {
  getUnreadNotificationCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/services/automation";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/jobs", label: "Jobs", icon: Briefcase },
  { to: "/rapid-apply", label: "Rapid Apply", icon: Rocket },
  { to: "/applications", label: "Applications", icon: FileText },
  { to: "/interviews", label: "Interviews", icon: Calendar },
  { to: "/resume", label: "Resume", icon: FileText },
  { to: "/profile", label: "Profile", icon: UserIcon },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/automation", label: "Automation", icon: Bot },
  { to: "/settings", label: "Settings", icon: Settings },
];

function NotificationBell() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: unreadCount } = useQuery({
    queryKey: ["notifications-unread-count"],
    queryFn: getUnreadNotificationCount,
    refetchInterval: 30000,
  });
  const { data: notifications } = useQuery({
    queryKey: ["notifications", "recent"],
    queryFn: () => listNotifications(false),
    enabled: open,
  });

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["notifications-unread-count"] }),
      queryClient.invalidateQueries({ queryKey: ["notifications", "recent"] }),
      queryClient.invalidateQueries({ queryKey: ["notifications"] }),
    ]);

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
        aria-label="Notifications"
      >
        <Bell size={18} />
        {!!unreadCount && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-brand-600 px-1 text-[10px] font-bold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-10 mt-2 w-80 rounded-xl border border-slate-200 bg-white p-3 shadow-lg dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Notifications</span>
            <button
              onClick={async () => {
                await markAllNotificationsRead();
                await refresh();
              }}
              disabled={!unreadCount}
              className="text-xs font-medium text-brand-600 hover:underline disabled:text-slate-300 disabled:no-underline"
            >
              Mark all read
            </button>
          </div>
          <div className="max-h-80 space-y-1.5 overflow-y-auto">
            {notifications?.length === 0 && (
              <p className="py-4 text-center text-xs text-slate-400">You're all caught up.</p>
            )}
            {notifications?.slice(0, 10).map((n) => (
              <div
                key={n.id}
                className={`rounded-lg px-2.5 py-2 text-xs ${
                  n.is_read ? "text-slate-500" : "bg-brand-50/60 font-medium dark:bg-brand-900/10"
                }`}
              >
                <div className="text-slate-700 dark:text-slate-200">{n.title}</div>
                <div className="mt-0.5 text-slate-400">{n.message}</div>
                {!n.is_read && (
                  <button
                    onClick={async () => {
                      await markNotificationRead(n.id);
                      await refresh();
                    }}
                    className="mt-1 text-brand-600 hover:underline"
                  >
                    Mark read
                  </button>
                )}
              </div>
            ))}
          </div>
          <Link
            to="/automation"
            onClick={() => setOpen(false)}
            className="mt-2 block rounded-lg py-1.5 text-center text-xs font-medium text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20"
          >
            View all in Automation
          </Link>
        </div>
      )}
    </div>
  );
}

export default function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-950">
      <aside className="flex w-64 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-2 px-6 py-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
            <Rocket size={18} />
          </div>
          <span className="text-lg font-semibold tracking-tight">JobPilot AI</span>
        </div>

        <nav className="flex-1 space-y-1 px-3">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-200"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-200 px-3 py-4 dark:border-slate-800">
          <div className="mb-2 truncate px-3 text-xs text-slate-500">{user?.email}</div>
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <LogOut size={18} />
            Log out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <div className="flex items-center justify-end border-b border-slate-200 bg-white px-6 py-2.5 dark:border-slate-800 dark:bg-slate-900">
          <NotificationBell />
        </div>
        <Outlet />
      </main>
    </div>
  );
}
