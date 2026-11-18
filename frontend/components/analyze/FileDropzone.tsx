"use client";

import { useId, useRef, useState } from "react";
import { UploadIcon } from "@/components/ui/icons";
import { formatFileSize } from "@/lib/utils";
import { ALLOWED_EXTENSIONS, MAX_UPLOAD_MB } from "@/lib/validation";

interface FileDropzoneProps {
  file: File | null;
  error?: string;
  onChange: (file: File | null) => void;
}

export function FileDropzone({ file, error, onChange }: FileDropzoneProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function pick(files: FileList | null) {
    onChange(files && files.length > 0 ? files[0] : null);
  }

  function remove() {
    if (inputRef.current) inputRef.current.value = ""; // lets the same file be chosen again
    onChange(null);
  }

  return (
    <div>
      <label
        htmlFor={inputId}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          pick(event.dataTransfer.files);
        }}
        className={`flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition focus-within:ring-2 focus-within:ring-indigo-600 focus-within:ring-offset-2 ${
          dragging
            ? "border-indigo-500 bg-indigo-50"
            : error
              ? "border-red-300 bg-red-50"
              : "border-slate-300 bg-white hover:bg-slate-50"
        }`}
      >
        <UploadIcon className="h-8 w-8 text-slate-500" />
        <span className="mt-3 text-sm font-medium text-slate-800">
          Drag and drop a resume here, or <span className="text-indigo-700 underline">browse</span>
        </span>
        <span className="mt-1 text-xs text-slate-600">
          PDF or TXT, up to {MAX_UPLOAD_MB} MB
        </span>
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept={ALLOWED_EXTENSIONS.join(",")}
          className="sr-only"
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${inputId}-error` : undefined}
          onChange={(event) => pick(event.target.files)}
        />
      </label>

      {file && (
        <div className="mt-3 flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2 text-sm">
          <span className="truncate text-slate-800">
            {file.name} <span className="text-slate-600">({formatFileSize(file.size)})</span>
          </span>
          <button
            type="button"
            onClick={remove}
            className="shrink-0 rounded px-2 py-1 text-slate-700 underline hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
          >
            Remove
          </button>
        </div>
      )}

      {error && (
        <p id={`${inputId}-error`} className="mt-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}