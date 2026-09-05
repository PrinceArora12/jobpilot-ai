export interface Education {
  id: string;
  degree: string | null;
  university: string | null;
  major: string | null;
  minor: string | null;
  graduation_year: number | null;
  cgpa: number | null;
  relevant_coursework: string[];
}

export interface Experience {
  id: string;
  company: string | null;
  position: string | null;
  start_date: string | null;
  end_date: string | null;
  responsibilities: string | null;
  achievements: string | null;
  technologies: string[];
}

export interface Project {
  id: string;
  name: string | null;
  description: string | null;
  technologies: string[];
  github_url: string | null;
  demo_url: string | null;
  achievements: string | null;
}

export interface Certification {
  id: string;
  name: string | null;
  issuer: string | null;
  issued_date: string | null;
  credential_url: string | null;
}

export interface Skill {
  id: string;
  name: string;
  category: string;
}

export interface Profile {
  id: string;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  city: string | null;
  country: string | null;
  linkedin_url: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  job_types: string[];
  work_modes: string[];
  preferred_locations: string[];
  min_salary: number | null;
  experience_level: string | null;
  preferred_roles: string[];
  preferred_skills: string[];
  education: Education[];
  experience: Experience[];
  projects: Project[];
  certifications: Certification[];
  skills: Skill[];
}

export const SKILL_CATEGORIES = [
  "programming_languages",
  "frameworks",
  "databases",
  "cloud",
  "ai_ml",
  "data_tools",
  "devops",
  "other",
  "soft_skills",
] as const;

export const JOB_TYPES = ["internship", "full_time", "part_time", "contract"] as const;
export const WORK_MODES = ["remote", "hybrid", "on_site"] as const;
export const EXPERIENCE_LEVELS = ["fresher", "entry_level", "0-1", "1-2", "2-4", "4+"] as const;
