'use client';

import React, { useEffect, useState } from 'react';
import { PromptService, ChainService, ExecutionService, ExportService, downloadBlob, ExecutionMetrics } from '@/services/api';
import {
    Play,
    Settings2,
    Loader2,
    History,
    ChevronRight,
    FileText,
    Copy,
    Check,
    Download,
    PlayCircle,
    BrainCircuit,
    CheckCircle2,
    Terminal
} from 'lucide-react';
import { cn } from '@/lib/utils';

import BlueprintDiagram from '@/components/BlueprintDiagram';
import TelemetryPanel from '@/components/TelemetryPanel';

interface Chain {
    id: number;
    name: string;
    description: string;
    framework: string;
    steps?: any[];
}

interface RunEntry {
    id: number;
    prompt_id?: number;
    inputs: string;
    result: string;
    created_at: string;
    metrics?: ExecutionMetrics | null;
}

export default function ModelingWorkbench() {
    const [chains, setChains] = useState<Chain[]>([]);
    const [history, setHistory] = useState<RunEntry[]>([]);

    // Selection State
    const [selectedFramework, setSelectedFramework] = useState<string>('');
    const [selectedChainId, setSelectedChainId] = useState<number | ''>('');

    const [inputs, setInputs] = useState<Record<string, string>>({});
    const [executing, setExecuting] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [telemetry, setTelemetry] = useState<ExecutionMetrics | null>(null);
    const [logs, setLogs] = useState<string[]>([]);
    const [copied, setCopied] = useState(false);
    const [loadingHistory, setLoadingHistory] = useState(true);
    const [viewMode, setViewMode] = useState<'text' | 'visual'>('text');
    const [exporting, setExporting] = useState(false);
    const [exportError, setExportError] = useState<string | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [c, h] = await Promise.all([
                ChainService.getAll(),
                ExecutionService.getHistory()
            ]);
            setChains(c);
            setHistory(h);
        } catch (error) {
            console.error("Failed to fetch data", error);
        } finally {
            setLoadingHistory(false);
        }
    };

    const frameworks = ['4EM', 'TOGAF', 'ArchiMate', 'Zachman'];

    // Filter chains by framework
    const filteredChains = chains.filter(c =>
        selectedFramework ? c.framework === selectedFramework : true
    );

    const selectedChain = chains.find(c => c.id === selectedChainId);

    const handleChainChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const id = e.target.value === '' ? '' : Number(e.target.value);
        setSelectedChainId(id);
        setResult(null);
        setTelemetry(null);
        setInputs({});

        if (id !== '') {
            const c = chains.find(chain => chain.id === id);
            if (c?.steps && c.steps.length > 0) {
                setInputs({ scenario: '' });
            }
        }
    };

    const addLog = (msg: string) => {
        setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
    };

    const handleExecute = async () => {
        if (selectedChainId === '') return;

        setExecuting(true);
        setResult(null);
        setTelemetry(null);
        setLogs([]);
        addLog(`Initializing execution of "${selectedChain?.name}"...`);

        try {
            addLog(`Framework: ${selectedChain?.framework} - Starting Chain...`);
            const data = await ExecutionService.executeChain(selectedChainId as number, inputs);
            addLog(`Pipeline execution completed.`);
            setResult(data);
            setTelemetry(data.metrics ?? null);
            fetchData();
        } catch (err) {
            console.error(err);
            addLog(`Pipeline error: execution failed.`);
        } finally {
            setExecuting(false);
        }
    };

    const handleLoadHistory = (run: RunEntry) => {
        setResult({
            result: run.result,
            inputs: JSON.parse(run.inputs),
            created_at: run.created_at
        });
        setTelemetry(run.metrics ?? null);
    };

    const copyToClipboard = () => {
        if (!result) return;
        navigator.clipboard.writeText(result.result);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const canExport = result && selectedChain && (selectedChain.framework?.toLowerCase() === '4em' || selectedChain.framework?.toLowerCase() === 'archimate');

    const handleExport = async (format: 'adl' | 'archimate') => {
        if (!result || !selectedChain) return;
        setExporting(true);
        setExportError(null);
        try {
            const file = format === 'adl'
                ? await ExportService.exportAdl({
                    chain_name: selectedChain.name,
                    steps: result.steps || [],
                    history_id: result.id,
                    inputs: result.inputs,
                })
                : await ExportService.exportArchimate({
                    chain_name: selectedChain.name,
                    steps: result.steps || [],
                    history_id: result.id,
                    inputs: result.inputs,
                });
            downloadBlob(file.blob, file.filename);
            addLog(`Exported ${format.toUpperCase()} model: ${file.filename}`);
        } catch (err: any) {
            console.error(err);
            addLog(`ERROR: Export failed - ${err?.message || err}`);
            setExportError(err?.message || 'Export failed. Check console.');
        } finally {
            setExporting(false);
        }
    };

    return (
        <div className="flex h-[calc(100vh-8rem)] space-x-6 overflow-hidden">
            {/* Sidebar: Config & History */}
            <div className="w-[380px] flex flex-col space-y-4 shrink-0 overflow-y-auto pr-1 custom-scrollbar">

                {/* Configuration Card */}
                <div className="rounded-2xl border bg-card p-6 shadow-sm">
                    <div className="flex items-center space-x-2 mb-6">
                        <div className="p-2 bg-primary/10 rounded-lg">
                            <Settings2 className="h-5 w-5 text-primary" />
                        </div>
                        <h3 className="font-bold text-foreground">Model Config</h3>
                    </div>

                    <div className="space-y-5">
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Framework</label>
                            <select
                                className="w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:ring-2 focus:ring-primary focus:outline-none transition-all shadow-sm"
                                value={selectedFramework}
                                onChange={(e) => {
                                    setSelectedFramework(e.target.value);
                                    setSelectedChainId('');
                                }}
                            >
                                <option value="">Global / All</option>
                                {frameworks.map(f => (
                                    <option key={f} value={f}>{f}</option>
                                ))}
                            </select>
                        </div>

                        <div className="space-y-2">
                            <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Architectural Chain</label>
                            <select
                                className="w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:ring-2 focus:ring-primary focus:outline-none transition-all shadow-sm"
                                value={selectedChainId}
                                onChange={handleChainChange}
                                disabled={chains.length === 0}
                            >
                                <option value="">Select Chain...</option>
                                {filteredChains.map(c => (
                                    <option key={c.id} value={c.id}>{c.name}</option>
                                ))}
                            </select>
                        </div>

                        {selectedChain && (
                            <div className="space-y-4 animate-in fade-in duration-300">
                                <div className="p-3 bg-muted/50 rounded-xl text-[11px] text-muted-foreground italic border">
                                    {selectedChain.description || "No description available."}
                                </div>

                                <div className="space-y-2">
                                    <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Scenario Input</label>
                                    <textarea
                                        className="w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:ring-2 focus:ring-primary focus:outline-none transition-all min-h-[100px]"
                                        value={inputs['scenario'] || ''}
                                        onChange={(e) => setInputs(prev => ({ ...prev, scenario: e.target.value }))}
                                        placeholder="Describe the enterprise scenario (e.g. 'We need to digitize the logistics hub to improve throughput by 20%...')"
                                    />
                                </div>

                                <button
                                    onClick={handleExecute}
                                    disabled={executing || !selectedChainId}
                                    className="w-full mt-2 inline-flex items-center justify-center rounded-xl bg-primary px-4 py-3 text-sm font-bold text-primary-foreground shadow-lg transition-all hover:bg-primary/90 disabled:opacity-50 active:scale-[0.98]"
                                >
                                    {executing ? (
                                        <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> RUNNING...</>
                                    ) : (
                                        <><Play className="mr-2 h-4 w-4 fill-current" /> GENERATE BLUEPRINT</>
                                    )}
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* Log Terminal */}
                <div className="rounded-2xl border bg-zinc-950 p-4 font-mono text-[10px] text-zinc-500 min-h-[140px] shadow-lg">
                    <div className="flex items-center justify-between mb-2 opacity-50 border-b border-zinc-800 pb-2">
                        <div className="flex items-center uppercase tracking-tighter">
                            <Terminal className="mr-1.5 h-3 w-3" /> Console Output
                        </div>
                        <History className="h-3 w-3" />
                    </div>
                    <div className="space-y-1 max-h-[100px] overflow-y-auto pt-1">
                        {logs.length === 0 && <div className="italic">Ready for injection...</div>}
                        {logs.map((log, i) => (
                            <div key={i} className="leading-tight animate-in fade-in slide-in-from-left-2">{log}</div>
                        ))}
                    </div>
                </div>

                {/* Pipeline Telemetry */}
                <TelemetryPanel metrics={telemetry} />

                {/* Past Executions */}
                <div className="flex-1 rounded-2xl border bg-muted/20 p-6 flex flex-col space-y-4">
                    <div className="flex items-center justify-between">
                        <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Recent Executions</h4>
                        <History className="h-4 w-4 text-muted-foreground opacity-50" />
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                        {loadingHistory ? (
                            <div className="flex justify-center p-4"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
                        ) : history.length === 0 ? (
                            <div className="text-center py-8 text-xs text-muted-foreground italic">No past runs recorded.</div>
                        ) : (
                            history.map(run => (
                                <button
                                    key={run.id}
                                    onClick={() => handleLoadHistory(run)}
                                    className="w-full text-left p-3 rounded-xl border bg-background hover:border-primary/50 transition-all group flex items-start justify-between"
                                >
                                    <div className="space-y-1 overflow-hidden">
                                        <div className="text-[11px] font-bold truncate">Run #{run.id}</div>
                                        <div className="text-[9px] text-muted-foreground">
                                            {new Date(run.created_at).toLocaleDateString()} at {new Date(run.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                    </div>
                                    <ChevronRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-all shrink-0 mt-1" />
                                </button>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* Main Stage: Results View */}
            <div className="flex-1 rounded-3xl border bg-card overflow-hidden shadow-sm flex flex-col border-primary/10">
                <div className="flex items-center justify-between border-b bg-muted/10 px-8 py-5">
                    <div className="flex items-center space-x-3">
                        <div className="p-2 bg-primary/10 rounded-lg">
                            <BrainCircuit className="h-6 w-6 text-primary" />
                        </div>
                        <div>
                            <h3 className="font-bold text-lg text-foreground">Architectural Blueprint</h3>
                            <p className="text-xs text-muted-foreground">Generative Modeling Environment</p>
                        </div>
                    </div>
                    {result && (
                        <div className="flex items-center space-x-4">
                            {/* View Switcher */}
                            <div className="flex items-center bg-background border rounded-xl p-1 shadow-sm mr-2">
                                <button
                                    onClick={() => setViewMode('text')}
                                    className={cn(
                                        "px-4 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center space-x-2",
                                        viewMode === 'text' ? "bg-primary text-primary-foreground shadow-sm" : "hover:bg-muted text-muted-foreground"
                                    )}
                                >
                                    <FileText className="h-3.5 w-3.5" />
                                    <span>TEXT</span>
                                </button>
                                <button
                                    onClick={() => setViewMode('visual')}
                                    className={cn(
                                        "px-4 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center space-x-2",
                                        viewMode === 'visual' ? "bg-primary text-primary-foreground shadow-sm" : "hover:bg-muted text-muted-foreground"
                                    )}
                                >
                                    <PlayCircle className="h-3.5 w-3.5" />
                                    <span>VISUAL</span>
                                </button>
                            </div>

                            <button
                                onClick={copyToClipboard}
                                className="inline-flex items-center px-4 py-2 rounded-xl border bg-background text-xs font-bold hover:bg-muted transition-all active:scale-95"
                            >
                                {copied ? <><Check className="mr-2 h-3.5 w-3.5 text-green-600" /> Copied</> : <><Copy className="mr-2 h-3.5 w-3.5" /> Copy Text</>}
                            </button>

                            {canExport && (
                                <button
                                    onClick={() => handleExport(selectedChain.framework.toLowerCase() === '4em' ? 'adl' : 'archimate')}
                                    disabled={exporting}
                                    className="inline-flex items-center px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-bold shadow-lg hover:bg-primary/90 transition-all active:scale-95 disabled:opacity-50"
                                >
                                    {exporting ? <><Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> EXPORTING...</> : <><Download className="mr-2 h-3.5 w-3.5" /> EXPORT {selectedChain.framework.toLowerCase() === '4em' ? '.ADL' : '.ARCHIMATE'}</>}
                                </button>
                            )}
                            <div className="hidden md:flex items-center text-xs font-bold text-green-600 bg-green-50 px-4 py-2 rounded-xl border border-green-100 italic">
                                <CheckCircle2 className="mr-2 h-4 w-4" /> VERIFIED MODEL
                            </div>
                        </div>
                    )}
                </div>

                {exportError && (
                    <div className="bg-destructive/10 border-b border-destructive/30 px-8 py-3 text-xs font-bold text-destructive flex items-center">
                        <Terminal className="mr-2 h-3.5 w-3.5 shrink-0" />
                        {exportError}
                    </div>
                )}

                <div className="flex-1 overflow-y-auto p-12 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:16px_16px]">
                    {!result && !executing ? (
                        <div className="h-full flex flex-col items-center justify-center text-center space-y-6">
                            <div className="h-20 w-20 rounded-full bg-primary/5 border border-primary/10 flex items-center justify-center animate-pulse">
                                <FileText className="h-10 w-10 text-primary/40" />
                            </div>
                            <div className="space-y-2">
                                <h4 className="font-bold text-2xl text-foreground">Canvas Ready</h4>
                                <p className="max-w-md text-muted-foreground text-sm leading-relaxed">
                                    Architect, please select a Framework and Chain to begin.
                                </p>
                            </div>
                        </div>
                    ) : executing ? (
                        <div className="h-full flex flex-col items-center justify-center space-y-6">
                            <div className="relative">
                                <div className="h-16 w-16 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <BrainCircuit className="h-6 w-6 text-primary animate-pulse" />
                                </div>
                            </div>
                            <div className="text-center space-y-1">
                                <p className="text-lg font-bold text-foreground">Generating Structural Context...</p>
                                <p className="text-xs text-muted-foreground italic">Reasoning through strategic nodes...</p>
                                {logs.length > 0 && (
                                    <p className="text-[10px] text-muted-foreground font-mono mt-2 opacity-70">{logs[logs.length - 1]}</p>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="max-w-5xl mx-auto space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-700 pb-20">
                            {/* THE RESULT - Polished Pre wrapper */}
                            {viewMode === 'text' ? (
                                <div className="space-y-6">
                                    {(() => {
                                        // Parse steps from the combined result
                                        const stepRegex = /### Step (\d+): ([^\n]+)\n([\s\S]*?)(?=\n### Step|\n\n### |$)/g;
                                        const steps = [];
                                        let match;
                                        while ((match = stepRegex.exec(result.result)) !== null) {
                                            steps.push({
                                                number: match[1],
                                                title: match[2],
                                                content: match[3].trim()
                                            });
                                        }

                                        return steps.length > 0 ? steps.map((step, idx) => (
                                            <div key={idx} className="relative group">
                                                <div className="absolute -inset-1 bg-gradient-to-r from-primary/10 to-blue-500/10 rounded-2xl blur opacity-25 group-hover:opacity-100 transition duration-1000"></div>
                                                <div className="relative bg-background border border-primary/10 rounded-2xl p-8 shadow-2xl overflow-hidden">
                                                    <div className="absolute top-0 right-0 p-4 font-mono text-[8px] text-muted-foreground opacity-30 select-none uppercase tracking-widest">
                                                        STEP {step.number}
                                                    </div>
                                                    <h3 className="text-lg font-bold text-primary mb-4">{step.title}</h3>
                                                    <div className="font-sans text-base leading-relaxed text-foreground whitespace-pre-wrap">
                                                        {step.content}
                                                    </div>
                                                </div>
                                            </div>
                                        )) : (
                                            <div className="relative group">
                                                <div className="absolute -inset-1 bg-gradient-to-r from-primary/10 to-blue-500/10 rounded-2xl blur opacity-25 group-hover:opacity-100 transition duration-1000"></div>
                                                <div className="relative bg-background border border-primary/10 rounded-2xl p-8 shadow-2xl overflow-hidden min-h-[400px]">
                                                    <div className="absolute top-0 right-0 p-4 font-mono text-[8px] text-muted-foreground opacity-30 select-none uppercase tracking-widest">
                                                        SECURE MODEL RUN #00{result.id || '---'}
                                                    </div>
                                                    <div className="font-sans text-base leading-relaxed text-foreground whitespace-pre-wrap space-y-4">
                                                        {result.result}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })()}
                                </div>
                            ) : (
                                <div className="animate-in zoom-in-95 duration-500">
                                    <BlueprintDiagram
                                        text={result.result}
                                        title={selectedChain?.name || 'Architectural Flow'}
                                    />
                                </div>
                            )}

                            {/* INSPECTION DATA */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-12">
                                <div className="space-y-3">
                                    <h5 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center px-1">
                                        <div className="w-1 h-1 rounded-full bg-primary mr-2" /> Logic Steps
                                    </h5>
                                    <div className="p-4 rounded-xl border bg-muted/30 text-[11px] font-mono leading-relaxed group max-h-40 overflow-y-auto custom-scrollbar">
                                        {result.steps?.map((s: any) => (
                                            <div key={s.step} className="mb-2 pb-2 border-b border-white/5 last:border-0 last:mb-0 last:pb-0">
                                                <span className="font-bold text-primary">#{s.step} [{s.prompt_name}]:</span> <span className="text-muted-foreground">{s.type}</span>
                                            </div>
                                        )) || "No step details available."}
                                    </div>
                                </div>
                                <div className="space-y-3">
                                    <h5 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center px-1">
                                        <div className="w-1 h-1 rounded-full bg-blue-500 mr-2" /> Parameters Used
                                    </h5>
                                    <div className="p-4 rounded-xl border bg-muted/30 flex flex-wrap gap-2 items-start h-full">
                                        {Object.entries(result.inputs || {}).map(([key, val]) => (
                                            <div key={key} className="flex items-center space-x-2 bg-background border rounded-lg px-3 py-1.5 shadow-sm">
                                                <span className="text-[10px] font-bold text-primary uppercase">{key}:</span>
                                                <span className="text-xs font-semibold">{String(val)}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
