'use client';

import React, { useEffect, useState } from 'react';
import { PromptService } from '@/services/api';
import {
    Search,
    Plus,
    Tag,
    Calendar,
    ChevronRight,
    Loader2,
    X,
    Copy,
    Check,
    Trash2,
    AlertCircle,
    TestTube2,
    Play,
    Terminal,
    Download
} from 'lucide-react';
import { ExecutionService, ExportService, downloadBlob } from '@/services/api';
import { cn } from '@/lib/utils';

interface Prompt {
    id: number;
    name: string;
    description: string;
    template: string;
    input_variables: string;
    tags?: string;
    updated_at: string;
}

export default function PromptLibrary() {
    const [prompts, setPrompts] = useState<Prompt[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [selectedPrompt, setSelectedPrompt] = useState<Prompt | null>(null);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [copied, setCopied] = useState(false);

    // Form State
    const [newPrompt, setNewPrompt] = useState({
        name: '',
        description: '',
        template: '',
        input_variables: '',
        tags: ''
    });
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [testInputs, setTestInputs] = useState<Record<string, string>>({});
    const [testResult, setTestResult] = useState<string | null>(null);
    const [testing, setTesting] = useState(false);
    const [activeTab, setActiveTab] = useState<'view' | 'experiment'>('view');
    const [exporting, setExporting] = useState(false);
    const [exportError, setExportError] = useState<string | null>(null);

    useEffect(() => {
        fetchPrompts();
    }, []);

    const fetchPrompts = () => {
        setLoading(true);
        PromptService.getAll()
            .then(setPrompts)
            .finally(() => setLoading(false));
    };

    const filteredPrompts = prompts.filter(p =>
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        (p.tags && p.tags.toLowerCase().includes(search.toLowerCase()))
    );

    const handleCopy = (text: string) => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            await PromptService.create(newPrompt);
            setShowCreateModal(false);
            setNewPrompt({ name: '', description: '', template: '', input_variables: '', tags: '' });
            fetchPrompts();
        } catch (error) {
            console.error("Failed to create prompt", error);
            alert("Error creating prompt. Please try again.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Are you sure you want to delete this prompt?")) return;
        try {
            await PromptService.delete(id);
            fetchPrompts();
            if (selectedPrompt?.id === id) setSelectedPrompt(null);
        } catch (error) {
            alert("Failed to delete prompt.");
        }
    };

    // Infer export format from prompt tags
    const exportFormat = (): 'adl' | 'archimate' | null => {
        const tags = (selectedPrompt?.tags || '').toLowerCase();
        if (tags.includes('4em')) return 'adl';
        if (tags.includes('archimate')) return 'archimate';
        return null;
    };

    const handleExport = async () => {
        if (!testResult || !selectedPrompt) return;
        const format = exportFormat();
        if (!format) return;
        setExporting(true);
        setExportError(null);
        try {
            const payload = {
                chain_name: selectedPrompt.name,
                steps: [{
                    step: 1,
                    prompt_name: selectedPrompt.name,
                    type: 'GENERATION',
                    result: testResult,
                }],
                inputs: testInputs,
            };
            const file = format === 'adl'
                ? await ExportService.exportAdl(payload)
                : await ExportService.exportArchimate(payload);
            downloadBlob(file.blob, file.filename);
        } catch (err: any) {
            console.error(err);
            setExportError(err?.message || 'Export failed. Check console.');
        } finally {
            setExporting(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight text-foreground">Prompt Library</h2>
                    <p className="text-muted-foreground">Manage and refine your enterprise modelling templates.</p>
                </div>
                <button
                    onClick={() => setShowCreateModal(true)}
                    className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                >
                    <Plus className="mr-2 h-4 w-4" /> New Prompt
                </button>
            </div>

            <div className="flex items-center space-x-2">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search prompts or tags..."
                        className="w-full rounded-md border border-input bg-background pl-10 pr-4 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
            </div>

            {loading ? (
                <div className="flex h-64 items-center justify-center">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {filteredPrompts.map((prompt) => (
                        <div
                            key={prompt.id}
                            className="group relative flex flex-col justify-between overflow-hidden rounded-3xl border bg-card p-8 shadow-sm transition-all hover:shadow-xl hover:border-primary/40 active:scale-[0.99]"
                        >
                            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                                <TestTube2 className="h-16 w-16" />
                            </div>
                            <div className="space-y-4 relative z-10">
                                <div className="flex items-start justify-between">
                                    <div className="space-y-1">
                                        <h3 className="text-lg font-bold text-card-foreground group-hover:text-primary transition-colors">
                                            {prompt.name}
                                        </h3>
                                        <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                                            {prompt.description}
                                        </p>
                                    </div>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); handleDelete(prompt.id); }}
                                        className="p-1.5 text-muted-foreground hover:text-destructive transition-colors opacity-0 group-hover:opacity-100"
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </button>
                                </div>

                                <div className="flex flex-wrap gap-2">
                                    {(prompt.tags || "Pattern").split(',').map((tag) => (
                                        <span
                                            key={tag}
                                            className="inline-flex items-center rounded-lg bg-primary/5 px-2.5 py-0.5 text-[10px] font-bold text-primary uppercase border border-primary/10"
                                        >
                                            {tag.trim()}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            <div className="mt-8 flex items-center justify-between border-t pt-5">
                                <div className="flex items-center text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                    <Calendar className="mr-1.5 h-3 w-3" />
                                    {new Date(prompt.updated_at).toLocaleDateString()}
                                </div>
                                <button
                                    onClick={() => { setSelectedPrompt(prompt); setActiveTab('view'); setTestResult(null); }}
                                    className="px-4 py-1.5 rounded-full bg-primary/10 text-primary text-xs font-bold hover:bg-primary hover:text-primary-foreground transition-all"
                                >
                                    Experiment
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Details Modal */}
            {selectedPrompt && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-card w-full max-w-3xl rounded-3xl shadow-2xl border border-primary/10 overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-200">
                        <div className="flex items-center justify-between p-6 border-b bg-muted/5">
                            <div className="flex flex-col">
                                <h3 className="text-xl font-bold">{selectedPrompt.name}</h3>
                                <div className="flex items-center space-x-4 mt-2">
                                    <button
                                        onClick={() => setActiveTab('view')}
                                        className={cn("text-[10px] font-bold uppercase tracking-widest pb-1 transition-all border-b-2", activeTab === 'view' ? "border-primary text-primary" : "border-transparent text-muted-foreground")}
                                    >
                                        Configuration
                                    </button>
                                    <button
                                        onClick={() => {
                                            setActiveTab('experiment');
                                            // Pre-fill inputs with empty strings
                                            const vars = selectedPrompt.input_variables.split(',').map(v => v.trim());
                                            const initInputs: any = {};
                                            vars.forEach(v => { if (v) initInputs[v] = ''; });
                                            setTestInputs(initInputs);
                                        }}
                                        className={cn("text-[10px] font-bold uppercase tracking-widest pb-1 transition-all border-b-2", activeTab === 'experiment' ? "border-primary text-primary" : "border-transparent text-muted-foreground")}
                                    >
                                        Live Experiment
                                    </button>
                                </div>
                            </div>
                            <button
                                onClick={() => setSelectedPrompt(null)}
                                className="p-2 rounded-xl hover:bg-muted transition-colors text-muted-foreground"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>

                        <div className="p-8 overflow-y-auto custom-scrollbar flex-1 bg-[radial-gradient(#e5e7eb_0.5px,transparent_0.5px)] [background-size:12px:12px]">
                            {activeTab === 'view' ? (
                                <div className="space-y-6">
                                    <div className="space-y-2">
                                        <h4 className="text-[10px] font-bold uppercase tracking-widest text-primary flex items-center">
                                            <div className="w-1 h-1 rounded-full bg-primary mr-2" /> Goal & Context
                                        </h4>
                                        <p className="text-sm leading-relaxed text-muted-foreground">{selectedPrompt.description}</p>
                                    </div>

                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <h4 className="text-[10px] font-bold uppercase tracking-widest text-primary flex items-center">
                                                <div className="w-1 h-1 rounded-full bg-primary mr-2" /> Pattern Template
                                            </h4>
                                            <button
                                                onClick={() => handleCopy(selectedPrompt.template)}
                                                className="inline-flex items-center text-[10px] font-bold text-primary bg-primary/5 px-3 py-1.5 rounded-lg hover:bg-primary/10 transition-colors border border-primary/10"
                                            >
                                                {copied ? <><Check className="mr-1.5 h-3 w-3" /> Copied</> : <><Copy className="mr-1.5 h-3 w-3" /> Copy Structure</>}
                                            </button>
                                        </div>
                                        <div className="relative group">
                                            <div className="absolute -inset-0.5 bg-gradient-to-r from-primary/20 to-blue-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-1000"></div>
                                            <pre className="relative p-6 rounded-2xl bg-zinc-950 text-zinc-300 font-mono text-[11px] border border-white/5 whitespace-pre-wrap leading-relaxed">
                                                {selectedPrompt.template}
                                            </pre>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-8 pt-4">
                                        <div className="space-y-3">
                                            <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">Logical Variables</h4>
                                            <div className="flex flex-wrap gap-2">
                                                {selectedPrompt.input_variables.split(',').map(v => (
                                                    <code key={v} className="bg-primary/5 text-primary text-[10px] px-2 py-1 rounded-lg border border-primary/10 font-bold tracking-tight">
                                                        {v.trim()}
                                                    </code>
                                                ))}
                                            </div>
                                        </div>
                                        <div className="space-y-3">
                                            <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">Framework Sync</h4>
                                            <div className="inline-flex items-center px-3 py-1 text-[10px] font-bold bg-green-50 text-green-600 rounded-lg border border-green-100">
                                                <div className="w-1.5 h-1.5 rounded-full bg-green-500 mr-2 animate-pulse" />
                                                PRODUCTION READY
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-8 h-full flex flex-col">
                                    <div className="grid gap-4">
                                        <h4 className="text-[10px] font-bold uppercase tracking-widest text-primary flex items-center">
                                            <div className="w-1 h-1 rounded-full bg-primary mr-2" /> Injection Parameters
                                        </h4>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {selectedPrompt.input_variables.split(',').map(v => v.trim()).filter(v => v).map(v => (
                                                <div key={v} className="space-y-1.5">
                                                    <label className="text-[9px] font-bold uppercase text-muted-foreground px-1">{v}</label>
                                                    <input
                                                        className="w-full rounded-xl border border-input bg-background px-4 py-2.5 text-xs focus:ring-2 focus:ring-primary focus:outline-none transition-all"
                                                        placeholder={`Enter value for ${v}...`}
                                                        value={testInputs[v] || ''}
                                                        onChange={(e) => setTestInputs(prev => ({ ...prev, [v]: e.target.value }))}
                                                    />
                                                </div>
                                            ))}
                                        </div>
                                        <button
                                            onClick={async () => {
                                                setTesting(true);
                                                setTestResult(null);
                                                try {
                                                    const res = await ExecutionService.execute(selectedPrompt.id, testInputs);
                                                    setTestResult(res.result);
                                                } catch (e) {
                                                    setTestResult("Error during pattern execution. Check server logs.");
                                                } finally {
                                                    setTesting(false);
                                                }
                                            }}
                                            disabled={testing}
                                            className="w-full mt-2 inline-flex items-center justify-center rounded-xl bg-primary px-4 py-3 text-sm font-bold text-primary-foreground shadow-lg transition-all hover:bg-primary/90 disabled:opacity-50 active:scale-[0.98]"
                                        >
                                            {testing ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> EXECUTING...</> : <><Play className="mr-2 h-4 w-4 fill-current" /> RUN TEST INJECTION</>}
                                        </button>
                                    </div>

                                    {testResult && (
                                        <div className="flex-1 space-y-3 animate-in fade-in slide-in-from-bottom-4">
                                            <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground flex items-center px-1">
                                                <Terminal className="mr-2 h-3.5 w-3.5" /> Generative Response
                                            </h4>
                                            <div className="p-6 rounded-2xl bg-zinc-950 text-zinc-300 font-mono text-[11px] border border-white/5 whitespace-pre-wrap leading-relaxed h-[200px] overflow-y-auto custom-scrollbar shadow-inner">
                                                {testResult}
                                            </div>

                                            {exportFormat() && (
                                                <div className="flex flex-col items-start gap-2">
                                                    <button
                                                        onClick={handleExport}
                                                        disabled={exporting}
                                                        className="inline-flex items-center rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-primary-foreground shadow-lg transition-all hover:bg-primary/90 disabled:opacity-50 active:scale-[0.98]"
                                                    >
                                                        {exporting ? <><Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> EXPORTING...</> : <><Download className="mr-2 h-3.5 w-3.5" /> EXPORT {exportFormat() === 'adl' ? '4EM .ADL' : 'ARCHIMATE .ARCHIMATE'}</>}
                                                    </button>
                                                    {exportError && (
                                                        <span className="text-[10px] font-bold text-destructive">{exportError}</span>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        <div className="p-6 bg-muted/20 border-t flex justify-between items-center">
                            <div className="text-[9px] text-muted-foreground uppercase font-black opacity-40">
                                Engineering Secure Gateway v4.2
                            </div>
                            <button
                                onClick={() => setSelectedPrompt(null)}
                                className="px-6 py-2.5 bg-background border rounded-xl text-xs font-bold shadow-sm hover:bg-muted transition-all active:scale-95"
                            >
                                Dismiss Detail
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Create Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-card w-full max-w-xl rounded-2xl shadow-2xl border overflow-hidden flex flex-col max-h-[95vh] animate-in zoom-in-95 duration-200">
                        <div className="flex items-center justify-between p-6 border-b bg-primary/5">
                            <div className="flex items-center space-x-2">
                                <div className="p-2 bg-primary/10 rounded-lg">
                                    <Plus className="h-5 w-5 text-primary" />
                                </div>
                                <h3 className="text-xl font-bold text-foreground">Draft New Pattern</h3>
                            </div>
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="p-1 rounded-md hover:bg-muted transition-colors text-muted-foreground"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>

                        <form onSubmit={handleCreate} className="flex-1 overflow-y-auto p-6 space-y-5">
                            <div className="space-y-2">
                                <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Prompt Name</label>
                                <input
                                    required
                                    placeholder="e.g., 4EM: Organizational Model"
                                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary focus:outline-none"
                                    value={newPrompt.name}
                                    onChange={e => setNewPrompt({ ...newPrompt, name: e.target.value })}
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Description</label>
                                <textarea
                                    required
                                    placeholder="What is this pattern used for?"
                                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm h-20 resize-none focus:ring-2 focus:ring-primary focus:outline-none"
                                    value={newPrompt.description}
                                    onChange={e => setNewPrompt({ ...newPrompt, description: e.target.value })}
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">AI Template</label>
                                <div className="relative group">
                                    <textarea
                                        required
                                        placeholder="Use {{variable}} for logic placeholders..."
                                        className="w-full rounded-md border border-input bg-zinc-950 font-mono text-zinc-100 px-3 py-3 text-xs h-32 focus:ring-2 focus:ring-primary focus:outline-none"
                                        value={newPrompt.template}
                                        onChange={e => setNewPrompt({ ...newPrompt, template: e.target.value })}
                                    />
                                    <div className="absolute right-2 bottom-2 text-[10px] text-zinc-500 font-mono">
                                        Markdown supported
                                    </div>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Variables</label>
                                    <input
                                        placeholder="e.g., topic, domain"
                                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs focus:ring-2 focus:ring-primary focus:outline-none"
                                        value={newPrompt.input_variables}
                                        onChange={e => setNewPrompt({ ...newPrompt, input_variables: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Tags</label>
                                    <input
                                        placeholder="e.g., 4EM, Strategy"
                                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs focus:ring-2 focus:ring-primary focus:outline-none"
                                        value={newPrompt.tags}
                                        onChange={e => setNewPrompt({ ...newPrompt, tags: e.target.value })}
                                    />
                                </div>
                            </div>
                        </form>

                        <div className="p-6 border-t bg-muted/20 flex items-center justify-between">
                            <div className="flex items-center text-[10px] text-muted-foreground max-w-[250px]">
                                <AlertCircle className="h-3 w-3 mr-1 shrink-0" />
                                Patterns are shared globally across the Enterprise Architect team.
                            </div>
                            <div className="flex space-x-3">
                                <button
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                    className="px-4 py-2 text-sm font-bold text-muted-foreground hover:text-foreground transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleCreate}
                                    disabled={isSubmitting}
                                    className="px-6 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-bold shadow-lg hover:bg-primary/90 disabled:opacity-50 transition-all active:scale-95"
                                >
                                    {isSubmitting ? 'Creating...' : 'Save Pattern'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {!loading && filteredPrompts.length === 0 && (
                <div className="flex h-64 flex-col items-center justify-center rounded-lg border border-dashed text-center">
                    <p className="text-muted-foreground">No prompts found matching your search.</p>
                </div>
            )}
        </div>
    );
}
