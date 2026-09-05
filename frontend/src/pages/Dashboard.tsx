import { useAuth } from "@/hooks/useAuth";

export default function Dashboard() {
  const { user } = useAuth();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  const stats = [
    { label: "Jobs discovered", value: "—" },
    { label: "Jobs matched", value: "—" },
    { label: "Applications submitted", value: "—" },
    { label: "Interviews", value: "—" },
  ];

  return (
    <div className="p-8">
      <div className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h1 className="text-2xl font-semibold">
          {greeting}
          {user?.first_name ? `, ${user.first_name}` : ""} 👋
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Your JobPilot AI account is set up. Rapid Apply, job sources, and matching come online in
          later phases.
        </p>
        <div className="mt-4 inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          <span className="h-2 w-2 rounded-full bg-slate-400" />
          Rapid Apply not yet configured
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="text-sm text-slate-500">{stat.label}</div>
            <div className="mt-2 text-2xl font-semibold">{stat.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
