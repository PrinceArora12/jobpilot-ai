export interface ResumeParsedData {
  name: string | null;
  email: string | null;
  phone: string | null;
  links: { linkedin: string | null; github: string | null };
  skills: string[];
  education: string[];
  experience: string[];
  projects: string[];
  certifications: string[];
  achievements: string[];
}

export interface Resume {
  id: string;
  label: string;
  original_filename: string;
  file_type: string;
  is_primary: boolean;
  parsed_data: ResumeParsedData | null;
  created_at: string;
}
