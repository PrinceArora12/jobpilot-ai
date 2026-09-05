interface ComingSoonProps {
  title: string;
  phase: string;
}

export default function ComingSoon({ title, phase }: ComingSoonProps) {
  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="text-center">
        <h1 className="text-xl font-semibold">{title}</h1>
        <p className="mt-2 text-sm text-slate-500">Ships in {phase} of the JobPilot AI build.</p>
      </div>
    </div>
  );
}
