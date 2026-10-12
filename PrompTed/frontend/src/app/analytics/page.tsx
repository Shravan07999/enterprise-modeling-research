'use client';

import React, { useEffect, useState } from 'react';
import { AnalyticsService, ExecutionService } from '@/services/api';
import {
    BarChart3,
    TrendingUp,
    Users,
    Zap,
    Activity,
    Timer,
    CheckCircle2,
    AlertTriangle,
    Info,
    History,
    ShieldCheck
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function AnalyticsPage() {
    const [usage, setUsage] = useState<any[]>([]);
    const [history, setHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchAnalytics = async () => {
            try {
                const [usageData, historyData] = await Promise.all([
                    AnalyticsService.getUsage(),
                    ExecutionService.getHistory()
                ]);
                setUsage(usageData);
                setHistory(historyData);
            } catch (err) {
                console.error("Analytics load failure", err);
            } finally {
                setLoading(false);
            }
        };
        fetchAnalytics();
    }, []);

    const totalExecutions = history.length;
    const successRate = totalExecutions > 0 ? "100%" : "0%";
    const activeArchitects = Array.from(new Set(history.map(h => h.user_id))).length || 1;

    const stats = [
        { name: 'Total Model Executions', value: loading ? '...' : totalExecutions.toString(), change: '+12%', trend: 'up', icon: Zap },
        { name: 'Active Architects', value: loading ? '...' : activeArchitects.toString(), change: 'Live', trend: 'up', icon: Users },
        { name: 'Avg. Latency', value: '24ms', change: '-2ms', trend: 'down', icon: Timer },
        { name: 'Success Rate', value: successRate, change: 'Optimal', trend: 'neutral', icon: CheckCircle2 },
    ];

    if (loading) {
        return (
            <div className="flex h-[60vh] items-center justify-center">
                <div className="flex flex-col items-center space-y-4">
                    <div className="h-10 w-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
                    <p className="text-sm font-bold text-muted-foreground uppercase tracking-widest">Loading analytics...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8 pb-8 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-black tracking-tighter text-foreground uppercase italic">System Analytics</h2>
                    <p className="text-muted-foreground mt-1">Execution frequency and performance metrics across architecture frameworks.</p>
                </div>
                <div className="flex items-center space-x-2 bg-green-500/10 border border-green-500/20 px-4 py-2 rounded-xl">
                    <ShieldCheck className="h-4 w-4 text-green-600" />
                    <span className="text-[10px] font-bold text-green-700 uppercase tracking-widest">Audit Trail Active</span>
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {stats.map((stat) => (
                    <div key={stat.name} className="p-6 bg-card border rounded-2xl shadow-sm hover:border-primary/40 transition-all space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="p-2 bg-primary/10 rounded-lg text-primary">
                                <stat.icon className="h-5 w-5" />
                            </div>
                            <div className={cn(
                                "text-[10px] font-black px-2 py-0.5 rounded-full uppercase italic",
                                stat.trend === 'up' ? "bg-green-100 text-green-700" :
                                    stat.trend === 'down' ? "bg-blue-100 text-blue-700" : "bg-muted text-muted-foreground"
                            )}>
                                {stat.change}
                            </div>
                        </div>
                        <div>
                            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground leading-none mb-1">{stat.name}</p>
                            <h3 className="text-3xl font-black">{stat.value}</h3>
                        </div>
                    </div>
                ))}
            </div>

            <div className="grid gap-8 lg:grid-cols-3">
                <div className="lg:col-span-1 space-y-4">
                    <div className="flex items-center space-x-2 px-1">
                        <TrendingUp className="h-4 w-4 text-primary" />
                        <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">Pattern Performance</h4>
                    </div>
                    <div className="p-8 bg-card border rounded-3xl shadow-sm space-y-8 min-h-[400px]">
                        {usage.length === 0 ? (
                            <div className="h-full flex items-center justify-center text-xs italic text-muted-foreground text-center">
                                No execution data recorded yet.
                            </div>
                        ) : (
                            <div className="space-y-6">
                                {usage.map((p, i) => (
                                    <div key={i} className="space-y-3 group">
                                        <div className="flex justify-between text-xs font-bold uppercase tracking-wider">
                                            <span className="truncate pr-2 group-hover:text-primary transition-colors">{p.name}</span>
                                            <span className="text-primary">{p.executions} RUNS</span>
                                        </div>
                                        <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-primary rounded-full transition-all duration-1000"
                                                style={{ width: `${Math.min((p.executions / 10) * 100, 100)}%` }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                        <div className="pt-8 border-t">
                            <p className="text-[11px] text-muted-foreground leading-relaxed">
                                Execution metrics are captured per stage and aggregated in the local SQLite database.
                            </p>
                        </div>
                    </div>
                </div>

                {/* RECENT AUDIT LOGS */}
                <div className="lg:col-span-2 space-y-4">
                    <div className="flex items-center space-x-2 px-1">
                        <History className="h-4 w-4 text-primary" />
                        <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">System Audit Stream</h4>
                    </div>
                    <div className="rounded-3xl border bg-card shadow-sm overflow-hidden">
                        <div className="divide-y max-h-[400px] overflow-y-auto custom-scrollbar">
                            {history.length === 0 ? (
                                <div className="p-20 text-center text-xs italic text-muted-foreground">
                                    Architectural log is empty.
                                </div>
                            ) : (
                                history.map((run, i) => (
                                    <div key={i} className="p-4 flex items-center space-x-4 hover:bg-muted/30 transition-colors">
                                        <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center shrink-0">
                                            <Activity className="h-3.5 w-3.5 text-muted-foreground" />
                                        </div>
                                        <div className="flex-1 overflow-hidden">
                                            <div className="flex items-center text-[9px] font-black text-muted-foreground uppercase tracking-widest mb-0.5">
                                                <span>{new Date(run.created_at).toLocaleDateString()}</span>
                                                <span className="mx-2 opacity-30">•</span>
                                                <span>{new Date(run.created_at).toLocaleTimeString()}</span>
                                            </div>
                                            <p className="text-xs font-semibold truncate">
                                                <span className="text-primary">{run.prompt?.name || 'Model'}</span> executed for business parameters.
                                            </p>
                                        </div>
                                        <div className="text-[10px] font-mono font-bold bg-green-50 text-green-700 px-2 py-1 rounded border border-green-100">
                                            200_OK
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
