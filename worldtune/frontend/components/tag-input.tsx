"use client";

import { useState } from "react";
import { Input, Label } from "@/components/ui/input";

export function TagInput({
  label,
  hint,
  values,
  onChange,
  placeholder = "Type and press Enter",
}: {
  label: string;
  hint?: string;
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");

  function commit(raw: string) {
    const parts = raw
      .split(",")
      .map((p) => p.trim())
      .filter(Boolean)
      .filter((p) => !values.some((v) => v.toLowerCase() === p.toLowerCase()));
    if (parts.length > 0) onChange([...values, ...parts]);
    setDraft("");
  }

  return (
    <div>
      <Label>
        {label}
        {hint ? <span className="ml-2 text-dim">{hint}</span> : null}
      </Label>
      <div className="rounded border border-hairline bg-elevated p-2">
        {values.length > 0 ? (
          <ul className="mb-2 flex flex-wrap gap-1.5">
            {values.map((v) => (
              <li key={v}>
                <button
                  type="button"
                  onClick={() => onChange(values.filter((x) => x !== v))}
                  className="group inline-flex items-center gap-1.5 rounded border border-hairline-strong bg-panel px-2 py-1 text-xs text-foreground hover:border-red-500/50"
                  aria-label={`Remove ${v}`}
                >
                  {v}
                  <span className="text-dim group-hover:text-red-400">×</span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
        <Input
          value={draft}
          placeholder={placeholder}
          className="border-0 bg-transparent px-1 py-1 focus:border-0"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              commit(draft);
            } else if (e.key === "Backspace" && draft === "" && values.length > 0) {
              onChange(values.slice(0, -1));
            }
          }}
          onBlur={() => commit(draft)}
        />
      </div>
    </div>
  );
}
