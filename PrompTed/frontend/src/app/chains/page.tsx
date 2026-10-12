'use client';

import React, { useEffect, useState } from 'react';
import { ChainService, PromptService } from '@/services/api';
import {
    Network,
    ArrowRight,
    Layers,
    Info,
    Loader2,
    Clock,
    X,
    Layout,
    Plus,
    Trash2,
    Save,
    PlusCircle,
    Edit3,
    Terminal,
    Settings
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface Prompt {
    id: number;
    name: string;
    description: string;
}

interface ChainStep {
    id: number;
    prompt_id: number;
    order: number;
    prompt: {
        name: string;
        description: string;
    };
}

interface Chain {
    id: number;
    name: string;
    description: string;
    updated_at: string;
    steps: ChainStep[];
}

export default function ModellingChains() {
    const [chains, setChains] = useState<Chain[]>([]);
    const [prompts, setPrompts] = useState<Prompt[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedChain, setSelectedChain] = useState<Chain | null>(null);
    const [isEditMode, setIsEditMode] = useState(false);
    const [showCreateModal, setShowCreateModal] = useState(false);

    // Form and Edit State
    const [formData, setFormData] = useState({ name: '', description: '' });
    const [formSteps, setFormSteps] = useState<{ prompt_id: number }[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [c, p] = await Promise.all([ChainService.getAll(), PromptService.getAll()]);
            setChains(c);
            setPrompts(p);
        } catch (error) {
            console.error("Failed to fetch data", error);
        } finally {
            setLoading(false);
        }
    };

    const handleOpenCreate = () => {
        setFormData({ name: '', description: '' });
        setFormSteps([]);
        setShowCreateModal(true);
    };

    const handleOpenEdit = (chain: Chain) => {
        setSelectedChain(chain);
        setFormData({ name: chain.name, description: chain.description });
        setFormSteps(chain.steps.sort((a, b) => a.order - b.order).map(s => ({ prompt_id: s.prompt_id })));
        setIsEditMode(true);
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (formSteps.length === 0) {
            alert("Please add at least one step.");
            return;
        }

        setIsSubmitting(true);
        try {
            if (isEditMode && selectedChain) {
                // Update Chain
                await ChainService.update(selectedChain.id, {
                    ...formData,
                    steps: formSteps.map((s, idx) => ({ prompt_id: s.prompt_id, order: idx + 1 }))
                });
            } else {
                // Create Chain
                const createdChain = await ChainService.create(formData);
                for (let i = 0; i < formSteps.length; i++) {
                    await ChainService.addStep(createdChain.id, {
                        prompt_id: formSteps[i].prompt_id,
                        order: i + 1,
                        input_mapping: i > 0 ? JSON.stringify({ input: "output_from_previous" }) : null
                    });
                }
            }

            setShowCreateModal(false);
            setIsEditMode(false);
            setSelectedChain(null);
            fetchData();
        } catch (error) {
            console.error("Failed to save chain", error);
            alert("Error saving chain.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDeleteChain = async (id: number) => {
        if (!confirm("Delete this chain sequence?")) return;
        try {
            await ChainService.delete(id);
            fetchData();
        } catch (error) {
            alert("Failed to delete chain.");
        }
    };

    const addStepToForm = () => {
        setFormSteps([...formSteps, { prompt_id: prompts[0]?.id || 0 }]);
    };

    const removeStepFromForm = (index: number) => {
        const updated = [...formSteps];
        updated.splice(index, 1);
        setFormSteps(updated);
    };

    const updateStepPrompt = (index: number, promptId: number) => {
        const updated = [...formSteps];
        updated[index].prompt_id = promptId;
        setFormSteps(updated);
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight text-foreground">Modelling Chains</h2>
                    <p className="text-muted-foreground">Orchestrate complex modelling tasks by linking prompts together.</p>
                </div>
                <button
                    onClick={handleOpenCreate}
                    className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none"
                >
                    <PlusCircle className="mr-2 h-4 w-4" /> Create New Chain
                </button>
            </div>

            {loading ? (
                <div className="flex h-64 items-center justify-center">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : (
                <div className="space-y-4">
                    {chains.map((chain) => (
                        <div
                            key={chain.id}
                            className="group overflow-hidden rounded-3xl border bg-card shadow-sm transition-all hover:shadow-xl hover:border-primary/40 relative"
                        >
                            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                                <Network className="h-24 w-24 -rotate-12" />
                            </div>

                            <div className="border-b bg-muted/5 px-8 py-6 relative z-10">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center space-x-4">
                                        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-inner">
                                            <Network className="h-6 w-6" />
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-bold text-card-foreground">{chain.name}</h3>
                                            <p className="text-xs text-muted-foreground mt-0.5">{chain.description || "Experimental Logic Chain"}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-3">
                                        <button
                                            onClick={() => handleOpenEdit(chain)}
                                            className="inline-flex items-center rounded-xl border border-input bg-background px-4 py-2 text-xs font-bold shadow-sm transition-all hover:bg-muted active:scale-95"
                                        >
                                            <Edit3 className="mr-2 h-3.5 w-3.5 text-primary" /> Modify Pipeline
                                        </button>
                                        <button
                                            onClick={() => handleDeleteChain(chain.id)}
                                            className="p-2 text-muted-foreground hover:text-destructive transition-colors rounded-xl hover:bg-destructive/5"
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <div className="px-8 py-10 overflow-x-auto custom-scrollbar bg-[radial-gradient(#e5e7eb_0.5px,transparent_0.5px)] [background-size:12px:12px]">
                                <div className="relative flex items-center justify-start space-x-6 min-w-max">
                                    {chain.steps?.sort((a, b) => a.order - b.order).map((step, idx) => (
                                        <React.Fragment key={step.id}>
                                            <div className="relative flex flex-col items-center group/step">
                                                <div className="flex flex-col items-center space-y-3 rounded-2xl border-2 bg-background p-6 text-center w-52 shadow-sm transition-all group-hover/step:border-primary/50 group-hover/step:shadow-lg">
                                                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-primary text-primary-foreground text-[8px] font-black rounded-full uppercase tracking-widest shadow-lg">
                                                        Step {step.order}
                                                    </div>
                                                    <div className="p-2 bg-muted/50 rounded-lg group-hover/step:bg-primary/10 transition-colors">
                                                        <Terminal className="h-4 w-4 text-primary" />
                                                    </div>
                                                    <span className="text-xs font-black text-foreground truncate w-full">{step.prompt.name}</span>
                                                    <div className="text-[9px] text-muted-foreground line-clamp-1 opacity-60">
                                                        {idx === 0 ? "Entry Context" : "Inherits Output"}
                                                    </div>
                                                </div>
                                            </div>
                                            {idx < chain.steps.length - 1 && (
                                                <div className="flex flex-col items-center">
                                                    <ArrowRight className="h-5 w-5 text-primary/30 group-hover:text-primary transition-colors" />
                                                </div>
                                            )}
                                        </React.Fragment>
                                    ))}
                                    {(!chain.steps || chain.steps.length === 0) && (
                                        <div className="flex w-full items-center justify-center py-8 text-xs text-muted-foreground italic border-2 border-dashed rounded-3xl">
                                            <Info className="mr-2 h-4 w-4" /> No computational steps configured for this sequence.
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="bg-muted/5 px-8 py-4 flex items-center justify-between text-[10px] text-muted-foreground border-t font-bold uppercase tracking-widest">
                                <div className="flex items-center space-x-6">
                                    <div className="flex items-center group-hover:text-primary transition-colors">
                                        <Layers className="mr-1.5 h-3.5 w-3.5" /> {chain.steps?.length || 0} Layers
                                    </div>
                                    <div className="flex items-center">
                                        <Clock className="mr-1.5 h-3.5 w-3.5" /> Updated {new Date(chain.updated_at).toLocaleDateString()}
                                    </div>
                                </div>
                                <div className="flex items-center text-primary/40 group-hover:underline cursor-pointer">
                                    View Audit Trail
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Create/Edit Modal */}
            {(showCreateModal || isEditMode) && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-card w-full max-w-2xl rounded-3xl shadow-2xl border border-primary/10 overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-200">
                        <div className="flex items-center justify-between p-6 border-b bg-muted/5">
                            <div className="flex items-center space-x-3">
                                <div className="p-2 bg-primary/10 rounded-xl">
                                    {isEditMode ? <Edit3 className="h-5 w-5 text-primary" /> : <PlusCircle className="h-5 w-5 text-primary" />}
                                </div>
                                <div>
                                    <h3 className="text-xl font-bold">{isEditMode ? 'Modify Logic Chain' : 'Build New Logic Chain'}</h3>
                                    <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest mt-0.5">Computational Pipeline Architect</p>
                                </div>
                            </div>
                            <button
                                onClick={() => { setShowCreateModal(false); setIsEditMode(false); setSelectedChain(null); }}
                                className="p-2 rounded-xl hover:bg-muted transition-colors text-muted-foreground"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>

                        <form onSubmit={handleSave} className="flex-1 overflow-y-auto p-8 space-y-8 bg-[radial-gradient(#e5e7eb_0.5px,transparent_0.5px)] [background-size:12px:12px]">
                            <div className="space-y-5">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-bold uppercase tracking-widest text-primary flex items-center px-1">
                                        <div className="w-1 h-1 rounded-full bg-primary mr-2" /> Chain Global Identity
                                    </label>
                                    <input
                                        required
                                        placeholder="e.g., Greenshare Operational Flow"
                                        className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm focus:ring-2 focus:ring-primary focus:outline-none transition-all"
                                        value={formData.name}
                                        onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-bold uppercase tracking-widest text-primary flex items-center px-1">
                                        <div className="w-1 h-1 rounded-full bg-primary mr-2" /> Functional Objective
                                    </label>
                                    <textarea
                                        required
                                        placeholder="Explain the purpose of this sequence..."
                                        className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm h-24 resize-none focus:ring-2 focus:ring-primary focus:outline-none transition-all"
                                        value={formData.description}
                                        onChange={e => setFormData({ ...formData, description: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="space-y-5 pt-8 border-t">
                                <div className="flex items-center justify-between px-1">
                                    <h4 className="text-[10px] font-bold uppercase tracking-widest text-primary flex items-center">
                                        <div className="w-1 h-1 rounded-full bg-primary mr-2" /> Logic Sequence [Step Flow]
                                    </h4>
                                    <button
                                        type="button"
                                        onClick={addStepToForm}
                                        className="text-[10px] font-black text-primary bg-primary/10 px-3 py-1.5 rounded-lg hover:bg-primary/20 transition-all border border-primary/10 uppercase tracking-widest"
                                    >
                                        <Plus className="mr-1.5 h-3 w-3" /> Insert Logic Step
                                    </button>
                                </div>

                                <div className="space-y-4">
                                    {formSteps.map((step, idx) => (
                                        <div key={idx} className="flex items-center space-x-4 p-4 bg-background rounded-2xl border-2 group transition-all hover:border-primary/30 relative overflow-hidden">
                                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary text-xs font-black shadow-inner">
                                                {idx + 1}
                                            </div>
                                            <div className="flex-1 space-y-2">
                                                <select
                                                    className="w-full bg-muted/30 border-none rounded-lg px-3 py-2 text-xs font-bold focus:ring-1 focus:ring-primary appearance-none cursor-pointer hover:bg-muted/50 transition-colors"
                                                    value={step.prompt_id}
                                                    onChange={(e) => updateStepPrompt(idx, parseInt(e.target.value))}
                                                >
                                                    {prompts.map(p => (
                                                        <option key={p.id} value={p.id}>{p.name}</option>
                                                    ))}
                                                </select>
                                                <div className="flex items-center space-x-4 px-1">
                                                    <div className="flex items-center text-[8px] font-bold text-muted-foreground uppercase opacity-60">
                                                        <Settings className="mr-1 h-2.5 w-2.5" /> ID: {step.prompt_id}
                                                    </div>
                                                    <div className="flex items-center text-[8px] font-bold text-green-600 uppercase">
                                                        <Layout className="mr-1 h-2.5 w-2.5" /> {idx === 0 ? "Entry Variable: scenario" : "Input: Previous Output"}
                                                    </div>
                                                </div>
                                            </div>
                                            <button
                                                type="button"
                                                onClick={() => removeStepFromForm(idx)}
                                                className="p-2 text-muted-foreground hover:text-destructive transition-colors shrink-0"
                                            >
                                                <X className="h-5 w-5" />
                                            </button>
                                        </div>
                                    ))}
                                    {formSteps.length === 0 && (
                                        <div className="text-center py-12 bg-muted/5 border-2 border-dashed rounded-3xl flex flex-col items-center space-y-2">
                                            <Network className="h-8 w-8 text-muted-foreground/30 mb-2" />
                                            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Pipeline is currently empty</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </form>

                        <div className="p-8 border-t bg-muted/10 flex items-center justify-between">
                            <div className="flex items-center space-x-2 text-[10px] text-muted-foreground font-black uppercase tracking-widest px-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                                <span>Logic Integrity Check: PASS</span>
                            </div>
                            <div className="flex space-x-4">
                                <button
                                    onClick={() => { setShowCreateModal(false); setIsEditMode(false); setSelectedChain(null); }}
                                    className="px-6 py-2.5 text-xs font-bold text-muted-foreground hover:text-foreground transition-all"
                                >
                                    Abort
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={isSubmitting || formSteps.length === 0}
                                    className="px-8 py-2.5 bg-primary text-primary-foreground rounded-xl text-xs font-black shadow-lg hover:bg-primary/90 disabled:opacity-50 transition-all active:scale-[0.97] flex items-center uppercase tracking-widest"
                                >
                                    {isSubmitting ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving Pipeline...</> : <><Save className="mr-2 h-4 w-4" /> Finalize Logic</>}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {!loading && chains.length === 0 && (
                <div className="flex h-64 flex-col items-center justify-center rounded-lg border border-dashed text-center">
                    <p className="text-muted-foreground">No modelling chains found.</p>
                </div>
            )}
        </div>
    );
}
