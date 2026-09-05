import { Pencil, Plus, Trash2, X } from "lucide-react";
import { useState } from "react";

export type FieldType = "text" | "textarea" | "number" | "tags";

export interface FieldConfig {
  key: string;
  label: string;
  type: FieldType;
  placeholder?: string;
}

interface EntityListEditorProps<T extends { id: string }> {
  title: string;
  fields: FieldConfig[];
  items: T[];
  summarize: (item: T) => { primary: string; secondary?: string };
  onCreate: (payload: Record<string, unknown>) => Promise<void>;
  onUpdate: (id: string, payload: Record<string, unknown>) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

function emptyForm(fields: FieldConfig[]): Record<string, unknown> {
  const form: Record<string, unknown> = {};
  for (const f of fields) form[f.key] = f.type === "tags" ? [] : f.type === "number" ? "" : "";
  return form;
}

function toFormValues<T>(item: T, fields: FieldConfig[]): Record<string, unknown> {
  const form: Record<string, unknown> = {};
  for (const f of fields) {
    const raw = (item as Record<string, unknown>)[f.key];
    form[f.key] = f.type === "tags" ? (raw as string[] | null) ?? [] : raw ?? "";
  }
  return form;
}

function toPayload(form: Record<string, unknown>, fields: FieldConfig[]): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const f of fields) {
    const value = form[f.key];
    if (f.type === "number") {
      payload[f.key] = value === "" || value === null ? null : Number(value);
    } else if (f.type === "tags") {
      payload[f.key] = value;
    } else {
      payload[f.key] = value === "" ? null : value;
    }
  }
  return payload;
}

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: FieldConfig;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  if (field.type === "textarea") {
    return (
      <textarea
        placeholder={field.placeholder}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
      />
    );
  }
  if (field.type === "tags") {
    const tags = (value as string[]) ?? [];
    return (
      <input
        placeholder={field.placeholder ?? "Comma-separated"}
        value={tags.join(", ")}
        onChange={(e) =>
          onChange(
            e.target.value
              .split(",")
              .map((t) => t.trim())
              .filter(Boolean)
          )
        }
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
      />
    );
  }
  return (
    <input
      type={field.type === "number" ? "number" : "text"}
      placeholder={field.placeholder}
      value={(value as string | number) ?? ""}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
    />
  );
}

export default function EntityListEditor<T extends { id: string }>({
  title,
  fields,
  items,
  summarize,
  onCreate,
  onUpdate,
  onDelete,
}: EntityListEditorProps<T>) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [form, setForm] = useState<Record<string, unknown>>(emptyForm(fields));
  const [isSaving, setIsSaving] = useState(false);

  const startEdit = (item: T) => {
    setEditingId(item.id);
    setIsAdding(false);
    setForm(toFormValues(item, fields));
  };

  const startAdd = () => {
    setIsAdding(true);
    setEditingId(null);
    setForm(emptyForm(fields));
  };

  const cancel = () => {
    setEditingId(null);
    setIsAdding(false);
  };

  const save = async () => {
    setIsSaving(true);
    try {
      const payload = toPayload(form, fields);
      if (editingId) {
        await onUpdate(editingId, payload);
      } else {
        await onCreate(payload);
      }
      cancel();
    } finally {
      setIsSaving(false);
    }
  };

  const isFormOpen = isAdding || editingId !== null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
        {!isFormOpen && (
          <button
            onClick={startAdd}
            className="flex items-center gap-1 rounded-lg bg-brand-50 px-2.5 py-1.5 text-xs font-medium text-brand-700 hover:bg-brand-100 dark:bg-brand-900/30 dark:text-brand-200"
          >
            <Plus size={14} /> Add
          </button>
        )}
      </div>

      <div className="space-y-3">
        {items.length === 0 && !isFormOpen && (
          <p className="text-sm text-slate-400">Nothing added yet.</p>
        )}
        {items.map((item) => {
          const { primary, secondary } = summarize(item);
          if (editingId === item.id) return null;
          return (
            <div
              key={item.id}
              className="flex items-start justify-between rounded-lg border border-slate-100 px-3 py-2 dark:border-slate-800"
            >
              <div>
                <div className="text-sm font-medium">{primary || "Untitled"}</div>
                {secondary && <div className="text-xs text-slate-500">{secondary}</div>}
              </div>
              <div className="flex gap-2">
                <button onClick={() => startEdit(item)} className="text-slate-400 hover:text-brand-600">
                  <Pencil size={15} />
                </button>
                <button onClick={() => onDelete(item.id)} className="text-slate-400 hover:text-red-600">
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          );
        })}

        {isFormOpen && (
          <div className="space-y-3 rounded-lg border border-brand-200 bg-brand-50/30 p-3 dark:border-brand-900 dark:bg-brand-900/10">
            {fields.map((f) => (
              <div key={f.key}>
                <label className="mb-1 block text-xs font-medium text-slate-500">{f.label}</label>
                <FieldInput
                  field={f}
                  value={form[f.key]}
                  onChange={(v) => setForm((prev) => ({ ...prev, [f.key]: v }))}
                />
              </div>
            ))}
            <div className="flex gap-2">
              <button
                onClick={save}
                disabled={isSaving}
                className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-60"
              >
                {isSaving ? "Saving..." : "Save"}
              </button>
              <button
                onClick={cancel}
                className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <X size={14} /> Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
