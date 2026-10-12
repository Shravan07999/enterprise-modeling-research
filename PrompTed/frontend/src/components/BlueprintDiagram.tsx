'use client';

import React, { useEffect, useState, useMemo, useRef } from 'react';
import {
    Users,
    Activity,
    Target,
    Database,
    ChevronDown,
    ChevronUp,
    Layers,
    Info,
    Move,
    Maximize2,
    Minimize2,
    Download,
    FileImage,
    FileText,
    Loader2
} from 'lucide-react';

interface BlueprintDiagramProps {
    text: string;
    title: string;
}

// Node types and their corresponding icons/colors
const NODE_TYPES: Record<string, { icon: any, color: string, bg: string, border: string }> = {
    actor: { icon: Users, color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200' },
    process: { icon: Activity, color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' },
    goal: { icon: Target, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' },
    system: { icon: Database, color: 'text-purple-600', bg: 'bg-purple-50', border: 'border-purple-200' },
    default: { icon: Info, color: 'text-slate-600', bg: 'bg-slate-50', border: 'border-slate-200' }
};

const parseAllFlowData = (text: string) => {
    const flows: any[] = [];
    const validStarts = [];
    for (let i = 0; i < text.length; i++) {
        if (text[i] === '{') validStarts.push(i);
    }

    for (const start of validStarts) {
        let balance = 0;
        let end = -1;
        for (let j = start; j < text.length; j++) {
            if (text[j] === '{') balance++;
            if (text[j] === '}') balance--;
            if (balance === 0) {
                end = j;
                break;
            }
        }

        if (end !== -1) {
            try {
                const jsonStr = text.substring(start, end + 1);
                const data = JSON.parse(jsonStr);

                let foundFlow = null;
                if (data.visual_flow) foundFlow = data.visual_flow;
                else if (data.nodes && data.edges) foundFlow = data;

                if (foundFlow && foundFlow.nodes && foundFlow.nodes.length > 0) {
                    const isDuplicate = flows.some(f => f.nodes.length === foundFlow.nodes.length && f.nodes[0]?.data?.label === foundFlow.nodes[0]?.data?.label);
                    if (!isDuplicate) {
                        const contextTitleMatch = text.substring(Math.max(0, start - 100), start).match(/### Step \d+: (.*)/);
                        flows.push({
                            ...foundFlow,
                            contextTitle: contextTitleMatch ? contextTitleMatch[1] : `Layer ${flows.length + 1}`
                        });
                    }
                }
            } catch (e) { }
        }
    }
    return flows;
};

export default function BlueprintDiagram({ text, title }: BlueprintDiagramProps) {
    const [debugOpen, setDebugOpen] = useState(false);
    const [activeFlowIndex, setActiveFlowIndex] = useState(0);
    const [zoom, setZoom] = useState(1);
    const [downloading, setDownloading] = useState(false);
    const [showDownloadMenu, setShowDownloadMenu] = useState(false);
    const canvasRef = useRef<HTMLDivElement>(null);

    const handleExport = async (format: 'png' | 'pdf') => {
        if (!canvasRef.current || downloading) return;
        setDownloading(true);
        setShowDownloadMenu(false);

        try {
            const filename = `blueprint-${title.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}`;

            // Capture all layers
            const layerImages: { dataUrl: string; width: number; height: number; title: string }[] = [];
            const originalIndex = activeFlowIndex;

            for (let i = 0; i < allFlows.length; i++) {
                setActiveFlowIndex(i);
                await new Promise(resolve => setTimeout(resolve, 400)); // Wait for render

                const currentLayout = (() => {
                    const flow = allFlows[i];
                    if (!flow) return { nodes: [], edges: [], width: 0, height: 0 };

                    const nodes = [...flow.nodes];
                    const edges = [...(flow.edges || [])];
                    const typeOrder = ['actor', 'process', 'system', 'goal', 'other'];
                    const lanes: Record<string, any[]> = {};

                    nodes.forEach(node => {
                        const type = (node.type || 'other').toLowerCase();
                        const laneKey = typeOrder.includes(type) ? type : 'other';
                        if (!lanes[laneKey]) lanes[laneKey] = [];
                        lanes[laneKey].push(node);
                    });

                    const laneWidth = 300;
                    const nodeHeight = 120;
                    const verticalGap = 60;

                    const positionedNodes = nodes.map(node => {
                        const type = (node.type || 'other').toLowerCase();
                        const laneKey = typeOrder.includes(type) ? type : 'other';
                        const laneIndex = typeOrder.indexOf(laneKey);
                        const nodesInLane = lanes[laneKey];
                        const indexInLane = nodesInLane.findIndex(n => n.id === node.id);

                        return {
                            ...node,
                            x: laneIndex * laneWidth + 50,
                            y: indexInLane * (nodeHeight + verticalGap) + 100
                        };
                    });

                    const maxWidth = typeOrder.length * laneWidth + 100;
                    const maxHeight = Math.max(...Object.values(lanes).map(l => l.length)) * (nodeHeight + verticalGap) + 200;

                    return { nodes: positionedNodes, edges, width: maxWidth, height: maxHeight };
                })();

                const { default: domtoimage } = await import('dom-to-image-more');
                const dataUrl = await domtoimage.toPng(canvasRef.current, {
                    quality: 1,
                    width: currentLayout.width,
                    height: currentLayout.height,
                    bgcolor: '#ffffff',
                    style: {
                        transform: 'scale(1)',
                        transformOrigin: 'top left'
                    }
                });

                layerImages.push({
                    dataUrl,
                    width: currentLayout.width,
                    height: currentLayout.height,
                    title: allFlows[i].contextTitle || `Layer ${i + 1}`
                });
            }

            // Restore original view
            setActiveFlowIndex(originalIndex);

            if (format === 'png') {
                // Create a vertically stacked PNG
                const totalHeight = layerImages.reduce((sum, img) => sum + img.height + 40, 0);
                const maxWidth = Math.max(...layerImages.map(img => img.width));

                const canvas = document.createElement('canvas');
                canvas.width = maxWidth;
                canvas.height = totalHeight;
                const ctx = canvas.getContext('2d');

                if (ctx) {
                    ctx.fillStyle = '#ffffff';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);

                    let yOffset = 20;
                    for (const layerImg of layerImages) {
                        const img = new Image();
                        img.src = layerImg.dataUrl;
                        await new Promise((resolve) => { img.onload = resolve; });

                        ctx.drawImage(img, 0, yOffset);
                        yOffset += layerImg.height + 40;
                    }

                    const link = document.createElement('a');
                    link.download = `${filename}.png`;
                    link.href = canvas.toDataURL('image/png');
                    link.click();
                }
            } else {
                // Create a multi-page PDF
                const { default: jsPDF } = await import('jspdf');
                const pdf = new jsPDF({
                    orientation: 'l',
                    unit: 'px',
                    format: [layerImages[0].width, layerImages[0].height]
                });

                for (let i = 0; i < layerImages.length; i++) {
                    if (i > 0) pdf.addPage([layerImages[i].width, layerImages[i].height], layerImages[i].width > layerImages[i].height ? 'l' : 'p');
                    pdf.addImage(layerImages[i].dataUrl, 'PNG', 0, 0, layerImages[i].width, layerImages[i].height);
                }

                pdf.save(`${filename}.pdf`);
            }
        } catch (e: any) {
            console.error("Export failed:", e);
            console.error("Error details:", e.message, e.stack);
            alert(`Export failed: ${e.message || 'Unknown error'}. Check console for details.`);
        } finally {
            setDownloading(false);
        }
    };

    const allFlows = useMemo(() => parseAllFlowData(text), [text]);
    const activeFlow = allFlows[activeFlowIndex] || null;
    const hasJSON = !!(activeFlow && activeFlow.nodes && activeFlow.nodes.length > 0);

    // Dynamic Layout Calculation
    const layout = useMemo(() => {
        if (!activeFlow) return { nodes: [], edges: [], width: 0, height: 0 };

        const nodes = [...activeFlow.nodes];
        const edges = [...(activeFlow.edges || [])];

        // Group by type for lanes
        const typeOrder = ['actor', 'process', 'system', 'goal', 'other'];
        const lanes: Record<string, any[]> = {};

        nodes.forEach(node => {
            const type = (node.type || 'other').toLowerCase();
            const laneKey = typeOrder.includes(type) ? type : 'other';
            if (!lanes[laneKey]) lanes[laneKey] = [];
            lanes[laneKey].push(node);
        });

        // Calculate positions
        const laneWidth = 300;
        const nodeHeight = 120;
        const verticalGap = 60;

        const positionedNodes = nodes.map(node => {
            const type = (node.type || 'other').toLowerCase();
            const laneKey = typeOrder.includes(type) ? type : 'other';
            const laneIndex = typeOrder.indexOf(laneKey);

            const nodesInLane = lanes[laneKey];
            const indexInLane = nodesInLane.findIndex(n => n.id === node.id);

            return {
                ...node,
                x: laneIndex * laneWidth + 50,
                y: indexInLane * (nodeHeight + verticalGap) + 100
            };
        });

        const maxWidth = typeOrder.length * laneWidth + 100;
        const maxHeight = Math.max(...Object.values(lanes).map(l => l.length)) * (nodeHeight + verticalGap) + 200;

        return { nodes: positionedNodes, edges, width: maxWidth, height: maxHeight };
    }, [activeFlow]);

    useEffect(() => {
        setActiveFlowIndex(0);
        setZoom(1);
    }, [text]);

    const renderArrow = (edge: any) => {
        const source = layout.nodes.find(n => n.id === edge.source);
        const target = layout.nodes.find(n => n.id === edge.target);

        if (!source || !target) return null;

        const startX = source.x + 240; // Anchor right
        const startY = source.y + 50;  // Center Y
        const endX = target.x;         // Anchor left
        const endY = target.y + 50;    // Center Y

        // Curved path
        const cp1x = startX + (endX - startX) / 2;
        const cp2x = startX + (endX - startX) / 2;

        const path = `M ${startX} ${startY} C ${cp1x} ${startY}, ${cp2x} ${endY}, ${endX} ${endY}`;

        return (
            <g key={edge.id} className="group">
                <path
                    d={path}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    className="text-slate-200 group-hover:text-blue-400 transition-colors"
                    markerEnd="url(#arrowhead)"
                />
                {edge.label && (
                    <text
                        x={(startX + endX) / 2}
                        y={(startY + endY) / 2 - 10}
                        className="text-[9px] font-bold fill-slate-400 uppercase tracking-tighter"
                        textAnchor="middle"
                    >
                        {edge.label}
                    </text>
                )}
            </g>
        );
    };

    return (
        <div className="relative bg-white rounded-3xl border shadow-2xl overflow-hidden min-h-[750px] flex flex-col font-sans border-primary/10">

            {/* Header / Layer Controls */}
            <div className="px-8 py-6 border-b flex items-center justify-between bg-white relative z-20 shadow-sm">
                <div className="flex items-center space-x-3">
                    <div className="p-2 bg-blue-50 rounded-lg">
                        <Layers className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                        <h2 className="text-xl font-black text-slate-800 tracking-tight">{title}</h2>
                        <div className="flex items-center space-x-2">
                            <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none">
                                {activeFlow?.contextTitle || "Blueprint Layer"}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="flex items-center space-x-4">
                    {allFlows.length > 1 && (
                        <div className="flex items-center bg-slate-50 border rounded-xl p-1 shrink-0">
                            {allFlows.map((flow, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => setActiveFlowIndex(idx)}
                                    className={`px-4 py-1.5 rounded-lg text-[9px] font-black uppercase tracking-wider transition-all ${activeFlowIndex === idx
                                        ? "bg-white text-blue-600 shadow-sm border border-slate-200"
                                        : "text-slate-400 hover:text-slate-600"
                                        }`}
                                >
                                    {flow.contextTitle?.split(':').pop() || `Layer ${idx + 1}`}
                                </button>
                            ))}
                        </div>
                    )}

                    <div className="bg-slate-50 border rounded-xl p-1 flex space-x-1">
                        <button onClick={() => setZoom(z => Math.max(0.5, z - 0.1))} className="p-2 hover:bg-white rounded-lg text-slate-400 transition-all"><Minimize2 size={14} /></button>
                        <button onClick={() => setZoom(1)} className="px-2 text-[10px] font-bold text-slate-500 uppercase">{Math.round(zoom * 100)}%</button>
                        <button onClick={() => setZoom(z => Math.min(2, z + 0.1))} className="p-2 hover:bg-white rounded-lg text-slate-400 transition-all"><Maximize2 size={14} /></button>
                    </div>

                    <div className="relative">
                        <button
                            onClick={() => setShowDownloadMenu(!showDownloadMenu)}
                            className="flex items-center space-x-2 bg-slate-900 text-white px-3 py-1.5 rounded-xl text-[10px] font-bold uppercase tracking-widest hover:bg-slate-800 transition-all shadow-md active:scale-95"
                        >
                            {downloading ? (
                                <Loader2 size={12} className="animate-spin" />
                            ) : (
                                <Download size={12} />
                            )}
                            <span>Export</span>
                        </button>

                        {showDownloadMenu && (
                            <div className="absolute right-0 top-full mt-2 w-40 bg-white rounded-xl shadow-xl border border-slate-100 overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-200">
                                <button
                                    onClick={() => handleExport('png')}
                                    className="w-full flex items-center space-x-3 px-4 py-3 text-left hover:bg-slate-50 transition-colors"
                                >
                                    <div className="p-1.5 bg-purple-50 text-purple-600 rounded-lg">
                                        <FileImage size={14} />
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-xs font-bold text-slate-700">PNG Image</span>
                                        <span className="text-[9px] text-slate-400 uppercase tracking-wider">High Res</span>
                                    </div>
                                </button>
                                <div className="h-px bg-slate-100" />
                                <button
                                    onClick={() => handleExport('pdf')}
                                    className="w-full flex items-center space-x-3 px-4 py-3 text-left hover:bg-slate-50 transition-colors"
                                >
                                    <div className="p-1.5 bg-red-50 text-red-600 rounded-lg">
                                        <FileText size={14} />
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-xs font-bold text-slate-700">PDF Document</span>
                                        <span className="text-[9px] text-slate-400 uppercase tracking-wider">Vectorized</span>
                                    </div>
                                </button>
                            </div>
                        )}
                        {showDownloadMenu && (
                            <div className="fixed inset-0 z-40" onClick={() => setShowDownloadMenu(false)} />
                        )}
                    </div>
                </div>
            </div>

            {/* Main Stage */}
            <div className="flex-1 overflow-auto bg-slate-50/50 custom-scrollbar relative p-10 cursor-grab active:cursor-grabbing">
                {hasJSON ? (
                    <div
                        ref={canvasRef}
                        className="transition-transform duration-300 origin-top-left bg-white" // Added bg-white for clean capture
                        style={{
                            transform: `scale(${zoom})`,
                            width: layout.width,
                            height: layout.height
                        }}
                    >
                        {/* SVG Edge Layer */}
                        <svg className="absolute inset-0 pointer-events-none overflow-visible w-full h-full">
                            <defs>
                                <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                                    <polygon points="0 0, 10 3.5, 0 7" fill="#e2e8f0" />
                                </marker>
                            </defs>
                            {layout.edges.map(renderArrow)}
                        </svg>

                        {/* Node Layer */}
                        {layout.nodes.map((node) => {
                            const config = NODE_TYPES[node.type?.toLowerCase()] || NODE_TYPES.default;
                            const Icon = config.icon;

                            return (
                                <div
                                    key={node.id}
                                    className="absolute"
                                    style={{ left: node.x, top: node.y }}
                                >
                                    <div className={`w-[240px] bg-white border-2 rounded-2xl p-5 shadow-lg group transition-all hover:scale-105 hover:shadow-xl ${config.border} relative overflow-hidden`}>
                                        <div className={`absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity ${config.color}`}>
                                            <Icon size={48} strokeWidth={1} />
                                        </div>

                                        <div className="flex items-center space-x-2 mb-3">
                                            <div className={`p-1.5 rounded-lg ${config.bg} ${config.color}`}>
                                                <Icon size={14} />
                                            </div>
                                            <span className={`text-[9px] font-black uppercase tracking-widest ${config.color}`}>
                                                {node.type || 'ENTITY'}
                                            </span>
                                        </div>

                                        <h4 className="text-sm font-black text-slate-800 uppercase tracking-tight mb-2 leading-tight">
                                            {node.data?.label || "Component"}
                                        </h4>
                                        <p className="text-[10px] text-slate-500 leading-relaxed line-clamp-2">
                                            {node.data?.description || "Architectural node identified in model trace."}
                                        </p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center space-y-4 opacity-30 p-20 text-center">
                        <div className="p-8 border-4 border-dashed rounded-full animate-spin-slow">
                            <Move size={48} className="text-slate-400" />
                        </div>
                        <div className="space-y-1">
                            <p className="font-black uppercase tracking-[0.2em] text-sm">Visual Engine Awaiting Context</p>
                            <p className="text-xs">Processing structural nodes and logical edges...</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Legend / Info Footer */}
            <div className="px-8 py-4 bg-white border-t flex items-center justify-between text-[10px] font-bold text-slate-400">
                <div className="flex items-center space-x-6">
                    {Object.entries(NODE_TYPES).filter(([k]) => k !== 'default').map(([type, config]) => (
                        <div key={type} className="flex items-center space-x-2">
                            <div className={`h-2 w-2 rounded-full ${config.bg} border ${config.border}`} />
                            <span className="uppercase tracking-widest">{type}</span>
                        </div>
                    ))}
                </div>

                <button
                    onClick={() => setDebugOpen(!debugOpen)}
                    className="flex items-center space-x-2 px-3 py-1.5 rounded-lg hover:bg-slate-50 transition-all uppercase tracking-widest group"
                >
                    <Info size={12} className="group-hover:text-blue-500" />
                    <span>Inspect Model Trace</span>
                </button>
            </div>

            {debugOpen && (
                <div className="absolute inset-0 z-50 bg-white/95 backdrop-blur-sm p-12 overflow-auto animate-in fade-in zoom-in-95 duration-500">
                    <div className="max-w-4xl mx-auto space-y-12">
                        <div className="flex justify-between items-end border-b pb-6">
                            <div>
                                <h3 className="text-3xl font-black text-slate-900 tracking-tighter">Model Trace Inspector</h3>
                                <p className="text-sm text-slate-500">Inspect intermediate model graph payload and raw generation output</p>
                            </div>
                            <button
                                onClick={() => setDebugOpen(false)}
                                className="bg-slate-900 text-white px-6 py-3 rounded-2xl font-black text-xs tracking-widest hover:bg-blue-600 transition-all shadow-lg"
                            >
                                CLOSE INSPECTOR
                            </button>
                        </div>

                        <div className="grid grid-cols-2 gap-10 font-mono">
                            <div className="space-y-4">
                                <h5 className="text-[10px] font-black text-blue-600 uppercase tracking-widest">Active Data Structure</h5>
                                <div className="p-6 bg-slate-900 rounded-3xl text-blue-400 text-xs overflow-auto max-h-[500px] shadow-2xl">
                                    <pre>{JSON.stringify(activeFlow, null, 2)}</pre>
                                </div>
                            </div>
                            <div className="space-y-4">
                                <h5 className="text-[10px] font-black text-orange-600 uppercase tracking-widest">Raw Terminal Output</h5>
                                <div className="p-6 bg-zinc-950 rounded-3xl text-zinc-500 text-[10px] leading-relaxed overflow-auto max-h-[500px] shadow-2xl">
                                    {text}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <style jsx>{`
                .animate-spin-slow {
                    animation: spin 8s linear infinite;
                }
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                .custom-scrollbar::-webkit-scrollbar {
                    width: 6px;
                    height: 6px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: #f8fafc;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: #e2e8f0;
                    border-radius: 10px;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                    background: #cbd5e1;
                }
            `}</style>
        </div>
    );
}
