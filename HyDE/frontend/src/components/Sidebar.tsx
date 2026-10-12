'use client';

import { useEffect, useState } from 'react';

interface LogEntry {
  timestamp: string;
  stage_name: string;
  latency_ms: number;
  token_count: number;
}

export interface TraceData {
  stage1_prompt: string | null;
  stage1_semantic_narrative: string | null;
  stage1_blueprint: string | null;
  stage2_query: string | null;
  stage2_chunk_count: number | null;
  stage3_prompt: string | null;
}

function CollapsibleStage({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="bg-[#1f2937] rounded-lg border border-gray-700 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-4 py-3 text-sm font-semibold text-gray-200 hover:bg-[#253347] transition-colors text-left"
      >
        <span className="text-xs text-gray-500">{open ? 'v' : '>'}</span>
        {title}
      </button>
      {open && <div className="px-4 pb-3 text-xs text-gray-400 space-y-2">{children}</div>}
    </div>
  );
}

export default function Sidebar({
  isPending,
  traceData,
  framework,
  sourcePages,
}: {
  isPending: boolean;
  traceData?: TraceData;
  framework?: string;
  sourcePages?: string[];
}) {
  const [metrics, setMetrics] = useState<LogEntry[]>([]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPending) {
      interval = setInterval(async () => {
        try {
          const res = await fetch('http://localhost:8011/metrics');
          setMetrics(await res.json());
        } catch {
          // Telemetry service may not be up
        }
      }, 3000);
    } else {
      fetch('http://localhost:8011/metrics')
        .then((r) => r.json())
        .then(setMetrics)
        .catch(() => {});
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPending]);

  return (
    <div className="w-full h-full bg-[#111827] text-white p-6 overflow-y-auto border border-gray-800 rounded-lg shadow-lg flex flex-col gap-6">
      <div>
        <h2 className="text-sm font-bold tracking-wider text-gray-300 mb-4 uppercase">Telemetry</h2>
        {isPending && (
          <div className="flex items-center space-x-2 mb-4 text-blue-400 text-sm">
            <div className="animate-spin h-4 w-4 border-2 border-blue-400 border-t-transparent rounded-full" />
            <span>Processing Pipeline...</span>
          </div>
        )}
        <div className="space-y-3">
          {metrics.map((m, i) => (
            <div
              key={i}
              className="bg-[#1f2937] p-3 rounded-lg text-sm border border-gray-700 shadow flex justify-between items-center"
            >
              <div>
                <div className="font-semibold text-gray-200 capitalize">
                  {m.stage_name.replace(/_/g, ' ')}
                </div>
                <div className="text-gray-500 text-xs mt-1">
                  {new Date(m.timestamp).toLocaleTimeString()}
                </div>
              </div>
              <div className="text-right">
                <div className="text-gray-300 font-mono">{m.latency_ms.toFixed(0)} ms</div>
                <div className="text-gray-400 text-xs mt-1">{m.token_count} tkns</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {traceData && framework && (
        <div>
          <h2 className="text-sm font-bold tracking-wider text-gray-300 mb-4 uppercase">Pipeline Trace</h2>
          <div className="space-y-2">
            <CollapsibleStage title="Stage 1 - Blueprint Generator">
              {traceData.stage1_prompt ? (
                <div>
                  <div className="text-gray-500 font-medium mb-1">Prompt (sent to GPT-4o):</div>
                  <pre className="text-gray-300 leading-relaxed font-mono text-[11px] whitespace-pre-wrap">
                    {traceData.stage1_prompt}
                  </pre>
                </div>
              ) : (
                <div className="text-gray-500 italic">Not available</div>
              )}
              <div className="border-t border-gray-700 pt-2 mt-2">
                <div className="text-gray-500 font-medium mb-1">Output - Semantic Narrative:</div>
                <div className="text-gray-300 leading-relaxed">
                  {traceData.stage1_semantic_narrative ?? 'Not available'}
                </div>
              </div>
              {traceData.stage1_blueprint ? (
                <div className="mt-2">
                  <div className="text-gray-500 font-medium mb-1">Output - Blueprint:</div>
                  <pre className="text-gray-300 leading-relaxed font-mono text-[11px] whitespace-pre-wrap">
                    {traceData.stage1_blueprint}
                  </pre>
                </div>
              ) : null}
            </CollapsibleStage>

            <CollapsibleStage title="Stage 2 - Vector Retrieval">
              {traceData.stage2_query ? (
                <div>
                  <div className="text-gray-500 font-medium mb-1">Query (sent to ChromaDB):</div>
                  <div className="text-gray-300 leading-relaxed">
                    {traceData.stage2_query}
                  </div>
                </div>
              ) : (
                <div className="text-gray-500 italic">Not available</div>
              )}
              <div className="border-t border-gray-700 pt-2 mt-2">
                <div className="text-gray-500 font-medium mb-1">Retrieved Results:</div>
                <div className="text-gray-500 mt-1">
                  Chunks found:{' '}
                  <span className="text-gray-300 font-mono">
                    {traceData.stage2_chunk_count ?? 0}
                  </span>
                </div>
                {sourcePages && sourcePages.length > 0 ? (
                  <ul className="list-disc list-inside text-gray-300 space-y-0.5 mt-1">
                    {sourcePages.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-gray-500 italic">No sources found</div>
                )}
              </div>
            </CollapsibleStage>

            <CollapsibleStage title="Stage 3 - Context Synthesizer">
              {traceData.stage3_prompt ? (
                <div>
                  <div className="text-gray-500 font-medium mb-1">Assembled Prompt (sent to GPT-4o):</div>
                  <pre className="text-gray-300 leading-relaxed font-mono text-[11px] whitespace-pre-wrap">
                    {traceData.stage3_prompt}
                  </pre>
                </div>
              ) : (
                <div className="text-gray-500 italic">Not available</div>
              )}
              <div className="border-t border-gray-700 pt-2 mt-2">
                <div className="text-gray-500 font-medium mb-1">Final Output:</div>
                <div className="text-gray-300 leading-relaxed">
                  {traceData.stage1_semantic_narrative
                    ? 'See the Narrative & Diagram tabs above.'
                    : 'Not available'}
                </div>
              </div>
            </CollapsibleStage>
          </div>
        </div>
      )}
    </div>
  );
}
