'use client';

import React from 'react';
import { Gauge } from 'lucide-react';
import { ExecutionMetrics, StepMetrics } from '@/services/api';

const fmtLatency = (v?: number) => `${(typeof v === 'number' ? v : 0).toFixed(2)}s`;

// -1 is the sentinel for "not available" (simulation fallback / offline run)
const fmtTokens = (n?: number | null) =>
    typeof n === 'number' && n > 0 ? n.toLocaleString() : '—';

function normalizeSteps(metrics: ExecutionMetrics): StepMetrics[] {
    if (metrics.steps && metrics.steps.length > 0) return metrics.steps;
    // Single-prompt executions report a flat shape
    if (metrics.latency_seconds !== undefined) {
        return [
            {
                step: 1,
                prompt_name: 'Single Pattern',
                type: 'GENERATION',
                model: metrics.model ?? null,
                latency_seconds: metrics.latency_seconds,
                prompt_tokens: metrics.prompt_tokens ?? -1,
                completion_tokens: metrics.completion_tokens ?? -1,
            },
        ];
    }
    return [];
}

export default function TelemetryPanel({ metrics }: { metrics: ExecutionMetrics | null }) {
    const steps = metrics ? normalizeSteps(metrics) : [];
    const totals = metrics?.totals;
    const hasData = steps.length > 0;

    return (
        <div className="rounded-2xl border bg-card p-5 shadow-sm space-y-3">
            <div className="flex items-center space-x-2">
                <div className="p-2 bg-primary/10 rounded-lg">
                    <Gauge className="h-4 w-4 text-primary" />
                </div>
                <h3 className="font-bold text-sm text-foreground">Pipeline Telemetry</h3>
            </div>

            {!hasData ? (
                <p className="text-xs text-muted-foreground italic py-2">
                    No telemetry yet. Run an execution to capture stage latency and token usage.
                </p>
            ) : (
                <>
                    <div>
                        {steps.map((s) => (
                            <div key={s.step} className="py-2 border-b border-border/40 last:border-0">
                                <div className="flex items-center justify-between gap-3">
                                    <span className="text-[11px] font-bold truncate">
                                        <span className="text-primary">#{s.step}</span> {s.prompt_name}
                                    </span>
                                    <span className="font-mono text-[11px] shrink-0 text-foreground">
                                        {fmtLatency(s.latency_seconds)}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between gap-3 mt-0.5">
                                    <span className="text-[9px] uppercase tracking-widest text-muted-foreground truncate">
                                        {s.model || s.type}
                                    </span>
                                    <span className="font-mono text-[10px] shrink-0 text-muted-foreground">
                                        {fmtTokens(s.prompt_tokens)}↑ / {fmtTokens(s.completion_tokens)}↓
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>

                    {totals && (
                        <div className="pt-1 flex items-center justify-between gap-3 border-t border-border pt-3">
                            <span className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground">
                                Total
                            </span>
                            <span className="font-mono text-[11px] font-bold text-foreground shrink-0">
                                {fmtLatency(totals.total_latency_seconds)} · {fmtTokens(totals.total_prompt_tokens)}↑ /{' '}
                                {fmtTokens(totals.total_completion_tokens)}↓
                            </span>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
