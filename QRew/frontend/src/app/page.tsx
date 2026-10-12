"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import QRewCanvas from "@/components/QRewCanvas";
import TelemetryPanel from "@/components/TelemetryPanel";
import ExportToolbar from "@/components/ExportToolbar";

const FRAMEWORKS = ["BPMN", "TOGAF", "4EM", "ZACHMAN"];
const API_URL = "/api/qrew/run";
const API_TIMEOUT_MS = 180000; // 3 minutes for Stage 2b (canonical model generation)

const EXPORT_FORMATS: Record<string, string[]> = {
  "4EM": ["adl"],
  "BPMN": ["archimate"],
  "TOGAF": [],
  "ZACHMAN": [],
};

interface CanonicalElementAttributes {
  [key: string]: string | number | boolean | undefined;
}

interface CanonicalElement {
  id: string;
  frameworkType: string;
  canonicalType: string;
  name: string;
  description: string;
  layer: string | null;
  submodel: string | null;
  attributes: CanonicalElementAttributes;
}

interface CanonicalRelationship {
  id: string;
  sourceId: string;
  targetId: string;
  frameworkType: string;
  canonicalType: string;
  name: string;
  description: string;
  attributes: Record<string, unknown>;
}

interface CanonicalModel {
  framework: "4EM" | "BPMN" | "TOGAF" | "ZACHMAN";
  metadata: {
    modelId: string;
    name: string;
    version: string;
    createdAt: string;
    toolVersion: string;
    frameworkVersion: string;
    sourceRunId: string;
  };
  elements: CanonicalElement[];
  relationships: CanonicalRelationship[];
  diagrams: unknown[];
  folders: unknown[];
  extensions: Record<string, unknown>;
}

interface PipelineResult {
  run_id: string;
  timestamp: string;
  pipeline_strategy: string;
  framework_target: string;
  metrics: {
    stage_1_latency_seconds: number;
    stage_2_latency_seconds: number;
    total_latency_seconds: number;
    stage_1_prompt_tokens: number;
    stage_1_completion_tokens: number;
    stage_2_prompt_tokens: number;
    stage_2_completion_tokens: number;
    stage_2b_latency_seconds?: number;
    stage_2b_prompt_tokens?: number;
    stage_2b_completion_tokens?: number;
  };
  traces: {
    original_raw_input: string;
    stage_1_rewritten_query: string;
    final_generated_code: string;
    canonical_model?: CanonicalModel;
    canonical_model_warnings?: string[];
  };
}

function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="fixed top-4 right-4 z-50 bg-red-600 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 max-w-md"
    >
      <span className="text-sm flex-1">{message}</span>
      <button onClick={onClose} className="text-white/70 hover:text-white text-lg leading-none">&times;</button>
    </motion.div>
  );
}

export default function Home() {
  const [input, setInput] = useState("");
  const [framework, setFramework] = useState("BPMN");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!input.trim()) return;
    setLoading(true);
    setError(null);
try {
        const res = await axios.post<PipelineResult>(API_URL, {
          user_input: input,
          framework_choice: framework,
        }, { timeout: API_TIMEOUT_MS });
      setResult(res.data);
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        const fallback = err.response?.data ? JSON.stringify(err.response.data) : err.message;
        setError(typeof detail === "string" ? detail : detail?.error || fallback);
      } else {
        setError("An unexpected error occurred");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <AnimatePresence>
        {error && <Toast message={error} onClose={() => setError(null)} />}
      </AnimatePresence>

      <header className="border-b border-gray-800 px-6 py-4">
        <h1 className="text-xl font-bold text-white">QRew</h1>
        <p className="text-sm text-gray-400">Enterprise Architecture Diagram Generator</p>
      </header>

      <main className="flex-1 flex flex-col p-6 gap-6">
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-xs text-gray-400 mb-1">Architecture Request</label>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              placeholder="e.g. Design a customer onboarding process"
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Framework</label>
            <select
              value={framework}
              onChange={(e) => setFramework(e.target.value)}
              className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {FRAMEWORKS.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleSubmit}
            disabled={loading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Running
              </span>
            ) : (
              "Generate"
            )}
          </button>
        </div>

        <AnimatePresence>
          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex items-center justify-center py-16"
            >
              <div className="flex flex-col items-center gap-3">
                <div className="w-10 h-10 border-3 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                <p className="text-sm text-gray-400">Running two-stage pipeline...</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {result && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex gap-6 flex-1"
          >
            <div className="flex-[2] flex flex-col">
              <QRewCanvas code={result.traces.final_generated_code} />
              <ExportToolbar
                framework={result.framework_target}
                runId={result.run_id}
                formats={EXPORT_FORMATS[result.framework_target] || []}
              />
            </div>
            <div className="flex-1">
              <TelemetryPanel metrics={result.metrics} traces={result.traces} />
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}
