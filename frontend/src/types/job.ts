export interface Company {
  id: string;
  name: string;
  is_blocked: boolean;
  is_favorite: boolean;
}

export interface Job {
  id: string;
  external_id: string;
  source: string;
  title: string;
  company: Company;
  location: string | null;
  remote: boolean;
  employment_type: string | null;
  experience_level: string | null;
  salary: string | null;
  description: string | null;
  requirements: string[];
  skills: string[];
  url: string;
  posted_at: string | null;
  deadline: string | null;
  first_seen_at: string;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface JobFilters {
  q?: string;
  employment_type?: string;
  experience_level?: string;
  remote?: boolean;
  location?: string;
  source?: string;
  skill?: string;
  page?: number;
}
