import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileText, Star, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { deleteResume, fetchResumes, setPrimaryResume, uploadResume } from "@/services/resumes";

export default function ResumePage() {
  const queryClient = useQueryClient();
  const { data: resumes, isLoading } = useQuery({ queryKey: ["resumes"], queryFn: fetchResumes });
  const [label, setLabel] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["resumes"] });

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setIsUploading(true);
    try {
      await uploadResume(file, label || file.name);
      setLabel("");
      await refresh();
    } catch {
      setError("Could not upload that file. Only PDF and DOCX resumes are supported.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="space-y-6 p-8">
      <div>
        <h1 className="text-xl font-semibold">Resume</h1>
        <p className="text-sm text-slate-500">
          Upload one resume per target role (e.g. Software Engineer, Data Analyst, Internship).
          JobPilot AI parses each one and never invents information it can't find in the file.
        </p>
      </div>

      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center dark:border-slate-700 dark:bg-slate-900">
        <Upload className="mx-auto mb-2 text-slate-400" size={28} />
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Resume label (e.g. Software Engineer Resume)"
          className="mx-auto mb-3 block w-full max-w-sm rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
        />
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx"
          onChange={handleFileChange}
          disabled={isUploading}
          className="mx-auto block text-sm"
        />
        {isUploading && <p className="mt-2 text-xs text-slate-500">Uploading and parsing...</p>}
        {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading resumes...</p>}

      <div className="space-y-4">
        {resumes?.map((resume) => (
          <div
            key={resume.id}
            className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                <FileText className="mt-0.5 text-slate-400" size={20} />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{resume.label}</span>
                    {resume.is_primary && (
                      <span className="flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-200">
                        <CheckCircle2 size={12} /> Primary
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-500">
                    {resume.original_filename} · {resume.file_type.toUpperCase()}
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                {!resume.is_primary && (
                  <button
                    onClick={async () => {
                      await setPrimaryResume(resume.id);
                      await refresh();
                    }}
                    title="Set as primary"
                    className="text-slate-400 hover:text-brand-600"
                  >
                    <Star size={16} />
                  </button>
                )}
                <button
                  onClick={async () => {
                    await deleteResume(resume.id);
                    await refresh();
                  }}
                  title="Delete"
                  className="text-slate-400 hover:text-red-600"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>

            {resume.parsed_data && (
              <div className="mt-4 grid grid-cols-1 gap-3 border-t border-slate-100 pt-4 text-sm dark:border-slate-800 sm:grid-cols-2">
                <div>
                  <div className="text-xs font-medium text-slate-400">Extracted contact info</div>
                  <div>{resume.parsed_data.name ?? "—"}</div>
                  <div className="text-slate-500">{resume.parsed_data.email ?? "No email found"}</div>
                  <div className="text-slate-500">{resume.parsed_data.phone ?? "No phone found"}</div>
                </div>
                <div>
                  <div className="text-xs font-medium text-slate-400">Detected skills</div>
                  {resume.parsed_data.skills.length > 0 ? (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {resume.parsed_data.skills.map((skill) => (
                        <span
                          key={skill}
                          className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="text-slate-500">None detected — add skills in your Profile instead.</div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {resumes?.length === 0 && (
          <p className="text-sm text-slate-400">No resumes uploaded yet.</p>
        )}
      </div>
    </div>
  );
}
