"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";

interface Props {
  framework: string;
  runId: string;
  formats: string[];
}

const FORMAT_LABELS: Record<string, string> = {
  adl: "Download .adl (4EM Toolkit)",
  archimate: "Download .archimate (Archi)",
};

const FORMAT_EXTENSIONS: Record<string, string> = {
  adl: "adl",
  archimate: "archimate",
};

export default function ExportToolbar({ framework, runId, formats }: Props) {
  const [exporting, setExporting] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async (format: string) => {
    setExporting(format);
    setError(null);
    try {
      const response = await axios.post(
        "/api/qrew/export",
        { run_id: runId, format },
        { responseType: "blob", timeout: 180000 }
      );

      // Check for validation warnings header
      const warnHeader = response.headers["x-validation-warnings"];
      if (warnHeader) {
        try {
          setWarnings(JSON.parse(warnHeader));
        } catch {
          setWarnings([]);
        }
      } else {
        setWarnings([]);
      }

      // Trigger download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `model.${FORMAT_EXTENSIONS[format]}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        const message = typeof detail === "string" ? detail : detail?.error || err.message;
        setError(message);
      } else {
        setError("An unexpected error occurred");
      }
    } finally {
      setExporting(null);
    }
  };

  if (formats.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-3 p-3 rounded-lg border border-gray-700 bg-gray-900"
    >
      <p className="text-xs text-gray-400 uppercase mb-2">Export Model</p>
      <div className="flex gap-2 flex-wrap">
        {formats.map((fmt) => (
          <button
            key={fmt}
            onClick={() => handleExport(fmt)}
            disabled={!!exporting}
            className={`px-3 py-1.5 text-sm rounded transition-colors ${
              exporting === fmt
                ? "bg-blue-600 text-white cursor-wait"
                : "bg-gray-800 text-gray-300 hover:bg-gray-700"
            }`}
          >
            {exporting === fmt ? (
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin" />
                Exporting...
              </span>
            ) : (
              FORMAT_LABELS[fmt] || `Download .${fmt}`
            )}
          </button>
        ))}
      </div>

      <AnimatePresence>
        {error && (
          <motion.p
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="mt-2 text-xs text-red-400"
          >
            Error: {error}
          </motion.p>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {warnings.length > 0 && (
          <motion.ul
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mt-2 text-xs text-yellow-400 space-y-1"
          >
            {warnings.map((w, i) => (
              <li key={i}>⚠ {w}</li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </motion.div>
  );
}