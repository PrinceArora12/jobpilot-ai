import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAuth } from "@/hooks/useAuth";
import { verifyEmail } from "@/services/auth";

type Status = "verifying" | "success" | "error";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const { refreshUser } = useAuth();
  const [status, setStatus] = useState<Status>("verifying");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("This verification link is missing its token.");
      return;
    }
    verifyEmail(token)
      .then(async (res) => {
        setStatus("success");
        setMessage(res.message);
        await refreshUser();
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err?.response?.data?.detail || "This verification link is invalid or has expired.");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="flex flex-col items-center gap-4 text-center">
      {status === "verifying" && (
        <>
          <Loader2 className="animate-spin text-brand-600" size={32} />
          <p className="text-sm text-slate-500">Verifying your email...</p>
        </>
      )}
      {status === "success" && (
        <>
          <CheckCircle2 className="text-emerald-500" size={32} />
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{message}</p>
          <Link
            to="/dashboard"
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Go to dashboard
          </Link>
        </>
      )}
      {status === "error" && (
        <>
          <XCircle className="text-red-500" size={32} />
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{message}</p>
          <Link
            to="/dashboard"
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
          >
            Back to dashboard
          </Link>
        </>
      )}
    </div>
  );
}
