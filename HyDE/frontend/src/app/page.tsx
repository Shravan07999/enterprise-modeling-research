'use client';
import { useState } from 'react';
import axios from 'axios';
import Sidebar from '../components/Sidebar';
import type { TraceData } from '../components/Sidebar';
import DiagramRenderer from '../components/DiagramRenderer';

export default function Home() {
  const [query, setQuery] = useState('');
  const [framework, setFramework] = useState('BPMN');
  const [isPending, setIsPending] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [traceData, setTraceData] = useState<TraceData | null>(null);
  const [sourcePages, setSourcePages] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [stage1Blueprint, setStage1Blueprint] = useState<string>('');

  const getNarrativeText = (text: string) => {
    return text.split('```')[0].trim();
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;
    
    setIsPending(true);
    setResult(null);
    setTraceData(null);
    setSourcePages([]);
    setError(null);
    setStage1Blueprint('');

    try {
      const response = await axios.post('http://localhost:8010/process-hyde', {
        user_query: query,
        framework_selected: framework,
      });
      const data = response.data;
      setResult(data.final_output);
      setStage1Blueprint(data.stage1_blueprint ?? '');
      setTraceData({
        stage1_prompt: data.stage1_prompt ?? null,
        stage1_semantic_narrative: data.stage1_semantic_narrative ?? null,
        stage1_blueprint: data.stage1_blueprint ?? null,
        stage2_query: data.stage2_query ?? null,
        stage2_chunk_count: data.stage2_chunk_count ?? null,
        stage3_prompt: data.stage3_prompt ?? null,
      });
      setSourcePages(data.retrieved_source_pages ?? []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'An error occurred connecting to HyDE Engine.');
    } finally {
      setIsPending(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0e17] text-gray-200 font-sans">
      <header className="border-b border-gray-800 px-6 py-4 flex flex-col">
        <h1 className="text-xl font-bold text-white">HyDE</h1>
        <p className="text-sm text-gray-400">Enterprise Architecture Diagram Generator</p>
      </header>

      <main className="flex-1 flex flex-col p-6 gap-6 overflow-hidden">
        <div className="flex gap-3 items-end max-w-full">
          <div className="flex-1">
            <label className="block text-xs text-gray-400 mb-1">Architecture Request</label>
            <input
              suppressHydrationWarning
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              placeholder="e.g. Design an employee onboarding process for an IT company specializing in software services"
              className="w-full bg-[#111827] border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Framework</label>
            <select
              value={framework}
              onChange={(e) => setFramework(e.target.value)}
              className="bg-[#111827] border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 w-32"
            >
              <option value="TOGAF">TOGAF</option>
              <option value="Zachman">Zachman</option>
              <option value="4EM">4EM</option>
              <option value="BPMN">BPMN</option>
            </select>
          </div>
          <button
            onClick={() => handleSubmit()}
            disabled={isPending || !query.trim()}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors h-[42px]"
          >
            Generate
          </button>
        </div>

        {error && (
          <div className="p-4 bg-red-900/40 border border-red-500 text-red-200 rounded">
            {error}
          </div>
        )}

        {isPending && (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
              <p className="text-sm text-gray-400">Running three-stage pipeline...</p>
            </div>
          </div>
        )}

        {result && !isPending && (
          <div className="flex gap-6 flex-1 min-h-0">
            <div className="flex-[2] flex flex-col bg-[#111827] border border-gray-800 rounded-lg shadow-lg relative min-h-0">
              <DiagramRenderer
                rawText={result}
                framework={framework}
                narrative={getNarrativeText(result)}
                stage1Blueprint={stage1Blueprint}
                modelName={query.slice(0, 60).trim() || 'hyde_model'}
              />
            </div>
            <div className="flex-1 min-h-0">
              <Sidebar
                isPending={isPending}
                traceData={traceData ?? undefined}
                framework={framework}
                sourcePages={sourcePages}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
