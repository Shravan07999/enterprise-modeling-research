"use client";

import { motion, AnimatePresence } from "framer-motion";

interface Metrics {
  stage_1_latency_seconds: number;
  stage_2_latency_seconds: number;
  total_latency_seconds: number;
  stage_1_prompt_tokens: number;
  stage_1_completion_tokens: number;
  stage_2_prompt_tokens: number;
  stage_2_completion_tokens: number;
}

interface Traces {
  original_raw_input: string;
  stage_1_rewritten_query: string;
  final_generated_code: string;
}

interface Props {
  metrics?: Metrics;
  traces?: Traces;
}

function MetricRow({ label, value, unit }: { label: string; value: number; unit: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex justify-between text-sm py-0.5"
    >
      <span className="text-gray-400">{label}</span>
      <span className="text-gray-100 font-mono">
        {value.toFixed(2)}{unit}
      </span>
    </motion.div>
  );
}

function TokenRow({ label, prompt, completion }: { label: string; prompt: number; completion: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex justify-between text-sm py-0.5"
    >
      <span className="text-gray-400">{label}</span>
      <span className="text-gray-100 font-mono text-xs">
        {prompt}↑ / {completion}↓
      </span>
    </motion.div>
  );
}

export default function TelemetryPanel({ metrics, traces }: Props) {
  if (!metrics) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <p className="text-sm text-gray-500">No data yet. Run a pipeline to see metrics.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-3 space-y-2">
      <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">Telemetry</h2>

      <AnimatePresence mode="wait">
        <motion.div
          key={metrics.total_latency_seconds}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="space-y-0"
        >
          <p className="text-xs text-gray-500 uppercase mt-1 mb-0.5">Latency</p>
          <MetricRow label="Stage 1" value={metrics.stage_1_latency_seconds} unit="s" />
          <MetricRow label="Stage 2" value={metrics.stage_2_latency_seconds} unit="s" />
          <div className="border-t border-gray-700 pt-1 mt-1">
            <MetricRow label="Total" value={metrics.total_latency_seconds} unit="s" />
          </div>

          <p className="text-xs text-gray-500 uppercase mt-2 mb-0.5">Tokens</p>
          <TokenRow
            label="Stage 1"
            prompt={metrics.stage_1_prompt_tokens}
            completion={metrics.stage_1_completion_tokens}
          />
          <TokenRow
            label="Stage 2"
            prompt={metrics.stage_2_prompt_tokens}
            completion={metrics.stage_2_completion_tokens}
          />
        </motion.div>
      </AnimatePresence>

      {traces && (
        <div className="space-y-1.5">
          <p className="text-xs text-gray-500 uppercase mt-1 mb-0.5">Traces</p>
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Original</p>
            <p className="text-xs text-gray-300 bg-gray-800 rounded p-2 truncate">
              {traces.original_raw_input}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Rewritten</p>
            <p className="text-xs text-gray-300 bg-gray-800 rounded p-2 max-h-64 overflow-y-auto">
              {traces.stage_1_rewritten_query}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
