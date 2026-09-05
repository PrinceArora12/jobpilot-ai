import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import EntityListEditor from "@/components/EntityListEditor";
import { childCollectionApi, fetchProfile, updateProfile } from "@/services/profile";
import {
  EXPERIENCE_LEVELS,
  JOB_TYPES,
  WORK_MODES,
  type Certification,
  type Education,
  type Experience,
  type Project,
  type Skill,
} from "@/types/profile";

const educationApi = childCollectionApi<Education>("education");
const experienceApi = childCollectionApi<Experience>("experience");
const projectsApi = childCollectionApi<Project>("projects");
const certificationsApi = childCollectionApi<Certification>("certifications");
const skillsApi = childCollectionApi<Skill>("skills");

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
      {children}
    </div>
  );
}

function TextField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-500">{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
      />
    </div>
  );
}

function CheckboxGroup({
  options,
  selected,
  onToggle,
}: {
  options: readonly string[];
  selected: string[];
  onToggle: (option: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => {
        const active = selected.includes(option);
        return (
          <button
            key={option}
            type="button"
            onClick={() => onToggle(option)}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              active
                ? "border-brand-600 bg-brand-600 text-white"
                : "border-slate-300 text-slate-600 hover:border-brand-400 dark:border-slate-700 dark:text-slate-300"
            }`}
          >
            {option.replace(/_/g, " ")}
          </button>
        );
      })}
    </div>
  );
}

export default function Profile() {
  const queryClient = useQueryClient();
  const { data: profile, isLoading } = useQuery({ queryKey: ["profile"], queryFn: fetchProfile });

  const [personal, setPersonal] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    city: "",
    country: "",
    linkedin_url: "",
    github_url: "",
    portfolio_url: "",
  });
  const [prefs, setPrefs] = useState({
    job_types: [] as string[],
    work_modes: [] as string[],
    preferred_locations: [] as string[],
    min_salary: "",
    experience_level: "",
    preferred_roles: [] as string[],
    preferred_skills: [] as string[],
  });
  const [isSavingPersonal, setIsSavingPersonal] = useState(false);
  const [isSavingPrefs, setIsSavingPrefs] = useState(false);

  useEffect(() => {
    if (!profile) return;
    setPersonal({
      first_name: profile.first_name ?? "",
      last_name: profile.last_name ?? "",
      phone: profile.phone ?? "",
      city: profile.city ?? "",
      country: profile.country ?? "",
      linkedin_url: profile.linkedin_url ?? "",
      github_url: profile.github_url ?? "",
      portfolio_url: profile.portfolio_url ?? "",
    });
    setPrefs({
      job_types: profile.job_types,
      work_modes: profile.work_modes,
      preferred_locations: profile.preferred_locations,
      min_salary: profile.min_salary?.toString() ?? "",
      experience_level: profile.experience_level ?? "",
      preferred_roles: profile.preferred_roles,
      preferred_skills: profile.preferred_skills,
    });
  }, [profile]);

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["profile"] });

  const savePersonal = async () => {
    if (!profile) return;
    setIsSavingPersonal(true);
    try {
      await updateProfile({ ...profile, ...personal });
      await refresh();
    } finally {
      setIsSavingPersonal(false);
    }
  };

  const savePrefs = async () => {
    if (!profile) return;
    setIsSavingPrefs(true);
    try {
      await updateProfile({
        ...profile,
        ...prefs,
        min_salary: prefs.min_salary === "" ? null : Number(prefs.min_salary),
      });
      await refresh();
    } finally {
      setIsSavingPrefs(false);
    }
  };

  const toggle = (list: string[], value: string) =>
    list.includes(value) ? list.filter((v) => v !== value) : [...list, value];

  if (isLoading || !profile) {
    return <div className="p-8 text-sm text-slate-500">Loading profile...</div>;
  }

  return (
    <div className="space-y-6 p-8">
      <div>
        <h1 className="text-xl font-semibold">Profile</h1>
        <p className="text-sm text-slate-500">
          This is what JobPilot AI's matching engine and Rapid Apply will use — keep it current.
        </p>
      </div>

      <Section title="Personal information">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TextField label="First name" value={personal.first_name} onChange={(v) => setPersonal((p) => ({ ...p, first_name: v }))} />
          <TextField label="Last name" value={personal.last_name} onChange={(v) => setPersonal((p) => ({ ...p, last_name: v }))} />
          <TextField label="Phone" value={personal.phone} onChange={(v) => setPersonal((p) => ({ ...p, phone: v }))} />
          <TextField label="City" value={personal.city} onChange={(v) => setPersonal((p) => ({ ...p, city: v }))} />
          <TextField label="Country" value={personal.country} onChange={(v) => setPersonal((p) => ({ ...p, country: v }))} />
          <TextField label="LinkedIn" value={personal.linkedin_url} onChange={(v) => setPersonal((p) => ({ ...p, linkedin_url: v }))} />
          <TextField label="GitHub" value={personal.github_url} onChange={(v) => setPersonal((p) => ({ ...p, github_url: v }))} />
          <TextField label="Portfolio" value={personal.portfolio_url} onChange={(v) => setPersonal((p) => ({ ...p, portfolio_url: v }))} />
        </div>
        <button
          onClick={savePersonal}
          disabled={isSavingPersonal}
          className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {isSavingPersonal ? "Saving..." : "Save personal info"}
        </button>
      </Section>

      <Section title="Job preferences">
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Job type</label>
            <CheckboxGroup
              options={JOB_TYPES}
              selected={prefs.job_types}
              onToggle={(v) => setPrefs((p) => ({ ...p, job_types: toggle(p.job_types, v) }))}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Work mode</label>
            <CheckboxGroup
              options={WORK_MODES}
              selected={prefs.work_modes}
              onToggle={(v) => setPrefs((p) => ({ ...p, work_modes: toggle(p.work_modes, v) }))}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Experience level</label>
            <CheckboxGroup
              options={EXPERIENCE_LEVELS}
              selected={prefs.experience_level ? [prefs.experience_level] : []}
              onToggle={(v) => setPrefs((p) => ({ ...p, experience_level: p.experience_level === v ? "" : v }))}
            />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TextField
              label="Preferred locations (comma-separated)"
              value={prefs.preferred_locations.join(", ")}
              onChange={(v) => setPrefs((p) => ({ ...p, preferred_locations: v.split(",").map((s) => s.trim()).filter(Boolean) }))}
            />
            <TextField
              label="Minimum salary/stipend"
              value={prefs.min_salary}
              onChange={(v) => setPrefs((p) => ({ ...p, min_salary: v }))}
            />
            <TextField
              label="Preferred roles (comma-separated)"
              value={prefs.preferred_roles.join(", ")}
              onChange={(v) => setPrefs((p) => ({ ...p, preferred_roles: v.split(",").map((s) => s.trim()).filter(Boolean) }))}
            />
            <TextField
              label="Preferred skills (comma-separated)"
              value={prefs.preferred_skills.join(", ")}
              onChange={(v) => setPrefs((p) => ({ ...p, preferred_skills: v.split(",").map((s) => s.trim()).filter(Boolean) }))}
            />
          </div>
        </div>
        <button
          onClick={savePrefs}
          disabled={isSavingPrefs}
          className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {isSavingPrefs ? "Saving..." : "Save preferences"}
        </button>
      </Section>

      <EntityListEditor<Education>
        title="Education"
        items={profile.education}
        fields={[
          { key: "degree", label: "Degree", type: "text" },
          { key: "university", label: "University", type: "text" },
          { key: "major", label: "Major", type: "text" },
          { key: "minor", label: "Minor", type: "text" },
          { key: "graduation_year", label: "Graduation year", type: "number" },
          { key: "cgpa", label: "CGPA", type: "number" },
          { key: "relevant_coursework", label: "Relevant coursework", type: "tags" },
        ]}
        summarize={(e) => ({ primary: `${e.degree ?? ""} — ${e.university ?? ""}`, secondary: e.graduation_year ? `Class of ${e.graduation_year}` : undefined })}
        onCreate={async (p) => { await educationApi.create(p); await refresh(); }}
        onUpdate={async (id, p) => { await educationApi.update(id, p); await refresh(); }}
        onDelete={async (id) => { await educationApi.remove(id); await refresh(); }}
      />

      <EntityListEditor<Experience>
        title="Experience"
        items={profile.experience}
        fields={[
          { key: "company", label: "Company", type: "text" },
          { key: "position", label: "Position", type: "text" },
          { key: "start_date", label: "Start date (YYYY-MM)", type: "text" },
          { key: "end_date", label: "End date (blank = current)", type: "text" },
          { key: "responsibilities", label: "Responsibilities", type: "textarea" },
          { key: "achievements", label: "Achievements", type: "textarea" },
          { key: "technologies", label: "Technologies", type: "tags" },
        ]}
        summarize={(e) => ({ primary: `${e.position ?? ""} @ ${e.company ?? ""}`, secondary: [e.start_date, e.end_date || "Present"].filter(Boolean).join(" – ") })}
        onCreate={async (p) => { await experienceApi.create(p); await refresh(); }}
        onUpdate={async (id, p) => { await experienceApi.update(id, p); await refresh(); }}
        onDelete={async (id) => { await experienceApi.remove(id); await refresh(); }}
      />

      <EntityListEditor<Project>
        title="Projects"
        items={profile.projects}
        fields={[
          { key: "name", label: "Project name", type: "text" },
          { key: "description", label: "Description", type: "textarea" },
          { key: "technologies", label: "Technologies", type: "tags" },
          { key: "github_url", label: "GitHub URL", type: "text" },
          { key: "demo_url", label: "Live demo URL", type: "text" },
          { key: "achievements", label: "Achievements", type: "textarea" },
        ]}
        summarize={(p) => ({ primary: p.name ?? "", secondary: p.technologies.join(", ") })}
        onCreate={async (p) => { await projectsApi.create(p); await refresh(); }}
        onUpdate={async (id, p) => { await projectsApi.update(id, p); await refresh(); }}
        onDelete={async (id) => { await projectsApi.remove(id); await refresh(); }}
      />

      <EntityListEditor<Certification>
        title="Certifications"
        items={profile.certifications}
        fields={[
          { key: "name", label: "Certification", type: "text" },
          { key: "issuer", label: "Issuer", type: "text" },
          { key: "issued_date", label: "Issued date", type: "text" },
          { key: "credential_url", label: "Credential URL", type: "text" },
        ]}
        summarize={(c) => ({ primary: c.name ?? "", secondary: c.issuer ?? undefined })}
        onCreate={async (p) => { await certificationsApi.create(p); await refresh(); }}
        onUpdate={async (id, p) => { await certificationsApi.update(id, p); await refresh(); }}
        onDelete={async (id) => { await certificationsApi.remove(id); await refresh(); }}
      />

      <EntityListEditor<Skill>
        title="Skills"
        items={profile.skills}
        fields={[
          { key: "name", label: "Skill", type: "text" },
          { key: "category", label: "Category (e.g. programming_languages, frameworks, cloud)", type: "text" },
        ]}
        summarize={(s) => ({ primary: s.name, secondary: s.category.replace(/_/g, " ") })}
        onCreate={async (p) => { await skillsApi.create(p); await refresh(); }}
        onUpdate={async (id, p) => { await skillsApi.update(id, p); await refresh(); }}
        onDelete={async (id) => { await skillsApi.remove(id); await refresh(); }}
      />
    </div>
  );
}
