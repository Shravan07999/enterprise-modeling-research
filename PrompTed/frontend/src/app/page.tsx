'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { PromptService, ChainService, AnalyticsService } from '@/services/api';
import { useAuth } from '@/context/AuthContext';
import {
  Library,
  Network,
  Activity,
  Zap,
  ChevronRight,
  ShieldCheck,
  Server,
  PenTool,
  BarChart3,
  History,
  User as UserIcon,
  Timer,
  ExternalLink
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function Home() {
  const { user } = useAuth();
  const [stats, setStats] = useState({ prompts: 0, chains: 0 });
  const [usage, setUsage] = useState<any[]>([]);
  const [activities, setActivities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [p, c, u, a] = await Promise.all([
        PromptService.getAll(),
        ChainService.getAll(),
        AnalyticsService.getUsage(),
        AnalyticsService.getAuditLogs()
      ]);
      setStats({ prompts: p.length, chains: c.length });
      setUsage(u);
      setActivities(a);
    } catch (err) {
      console.error("Dashboard data load failure", err);
    } finally {
      setLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div className="space-y-8 max-w-6xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-black tracking-tighter text-foreground bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/60">
            {user.role === 'architect' ? 'Architectural Workbench' : 'Dashboard'}
          </h1>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 animate-in fade-in duration-700">
        <div className="group rounded-2xl border bg-card p-6 shadow-sm hover:border-primary/40 transition-all">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-primary/10 rounded-lg group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
              <Library className="h-5 w-5" />
            </div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-tighter italic">Library</span>
          </div>
          <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest leading-none">Patterns</p>
          <div className="text-3xl font-black mt-1">{loading ? '...' : stats.prompts}</div>
        </div>

        <div className="group rounded-2xl border bg-card p-6 shadow-sm hover:border-blue-500/40 transition-all">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-blue-500/10 rounded-lg group-hover:bg-blue-500 group-hover:text-white transition-colors">
              <Network className="h-5 w-5" />
            </div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-tighter italic">Logic</span>
          </div>
          <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest leading-none">Chains</p>
          <div className="text-3xl font-black mt-1">{loading ? '...' : stats.chains}</div>
        </div>

        <div className="group rounded-2xl border bg-card p-6 shadow-sm hover:border-green-500/40 transition-all">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-green-500/10 rounded-lg group-hover:bg-green-500 group-hover:text-white transition-colors">
              <Activity className="h-5 w-5" />
            </div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-tighter italic">Status</span>
          </div>
          <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest leading-none">API Latency</p>
          <div className="text-3xl font-black mt-1">24ms</div>
        </div>

      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* MAIN ACTIONS COLUMN */}
        <div className="lg:col-span-2 space-y-8">
          <section className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-[0.2em] text-muted-foreground flex items-center px-1">
              <Zap className="mr-2 h-4 w-4 text-primary" /> Workspaces
            </h3>
            <div className="grid gap-4">
              {user.role === 'architect' ? (
                <Link href="/workbench" className="group relative overflow-hidden flex items-center justify-between p-8 rounded-3xl border bg-card hover:border-primary/50 transition-all shadow-sm hover:shadow-xl active:scale-[0.99]">
                  <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                    <Zap className="h-24 w-24 -rotate-12" />
                  </div>
                  <div className="relative z-10 flex items-center space-x-6">
                    <div className="hidden sm:flex p-5 rounded-2xl bg-primary text-primary-foreground shadow-lg group-hover:rotate-3 transition-transform">
                      <Zap className="h-8 w-8" />
                    </div>
                    <div>
                      <h4 className="text-2xl font-black tracking-tight">Enterprise Modeling Workbench</h4>
                      <p className="text-sm text-muted-foreground mt-1 max-w-sm">Execute validated enterprise patterns and generate blueprints.</p>
                    </div>
                  </div>
                  <ChevronRight className="h-6 w-6 text-muted-foreground group-hover:translate-x-2 transition-transform" />
                </Link>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  <Link href="/prompts" className="group flex flex-col justify-between p-6 rounded-3xl border bg-card hover:border-primary/50 transition-all hover:shadow-lg h-48">
                    <div className="p-3 w-fit rounded-2xl bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-all">
                      <Library className="h-6 w-6" />
                    </div>
                    <div>
                      <h4 className="text-xl font-bold tracking-tight">Pattern Library</h4>
                      <p className="text-[11px] text-muted-foreground mt-1">Refine generative models.</p>
                    </div>
                  </Link>
                  <Link href="/chains" className="group flex flex-col justify-between p-6 rounded-3xl border bg-card hover:border-blue-500/50 transition-all hover:shadow-lg h-48">
                    <div className="p-3 w-fit rounded-2xl bg-blue-500/10 text-blue-500 group-hover:bg-blue-500 group-hover:text-white transition-all">
                      <Network className="h-6 w-6" />
                    </div>
                    <div>
                      <h4 className="text-xl font-bold tracking-tight">Chain Architect</h4>
                      <p className="text-[11px] text-muted-foreground mt-1">Design sequential execution flows.</p>
                    </div>
                  </Link>
                </div>
              )}
            </div>
          </section>

          <section className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-[0.2em] text-muted-foreground flex items-center px-1">
              <History className="mr-2 h-4 w-4" /> Activity Log
            </h3>
            <div className="rounded-3xl border bg-muted/20 p-2 overflow-hidden">
              <div className="max-h-[320px] overflow-y-auto space-y-1 p-2 custom-scrollbar">
                {activities.length === 0 ? (
                  <div className="p-12 text-center text-xs text-muted-foreground italic">No recent activity detected.</div>
                ) : (
                  activities.map((log) => (
                    <div key={log.id} className="group flex items-center space-x-4 p-4 rounded-2xl hover:bg-background transition-all border border-transparent hover:border-border">
                      <div className={cn(
                        "p-2.5 rounded-xl shadow-sm",
                        log.action.includes('Execute') ? "bg-green-500/10 text-green-600" : "bg-primary/10 text-primary"
                      )}>
                        <UserIcon className="h-4 w-4" />
                      </div>
                      <div className="flex-1 overflow-hidden">
                        <div className="flex items-center text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1">
                          <span>{log.user?.full_name || 'System'}</span>
                          <span className="mx-2 opacity-20">•</span>
                          <span>{new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                        <p className="text-xs font-semibold text-foreground truncate">{log.details}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </section>
        </div>

        {/* INSIGHTS COLUMN */}
        <div className="space-y-8">
          <section className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-[0.2em] text-muted-foreground flex items-center px-1">
              <BarChart3 className="mr-2 h-4 w-4" /> {user.role === 'architect' ? 'Model Availability' : 'Usage Stats'}
            </h3>
            <div className="rounded-3xl border bg-card shadow-sm p-6 space-y-6">
              {user.role === 'architect' ? (
                <div className="space-y-6">
                  <div className="space-y-4">
                    <p className="text-xs font-bold text-primary uppercase flex items-center">
                      <ShieldCheck className="mr-2 h-3 w-3" /> QA-Verified Workspace
                    </p>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      Your environment is currently synced with the 4EM Global Library. Engineers have verified the following schemas:
                    </p>
                  </div>
                  <div className="grid gap-2">
                    {['Strategy v1.4', 'Technical Nodes', 'Process Flow'].map(v => (
                      <div key={v} className="flex items-center justify-between p-3 rounded-xl bg-muted/30 border text-[11px] font-bold">
                        <span>{v}</span>
                        <span className="text-green-600">LIVE</span>
                      </div>
                    ))}
                  </div>
                  <div className="pt-6 border-t">
                    <div className="p-4 rounded-xl bg-primary/5 border border-primary/10 text-[10px] leading-relaxed italic text-muted-foreground">
                      Manage and execute enterprise modeling patterns with precision and consistency.
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Real-time execution counts from the Architect Workbench:
                  </p>
                  <div className="space-y-3">
                    {usage.length === 0 ? (
                      <div className="text-xs italic text-muted-foreground text-center py-4">No model runs detected.</div>
                    ) : (
                      usage.map((u) => (
                        <div key={u.name} className="space-y-1.5">
                          <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-widest overflow-hidden">
                            <span className="truncate pr-2">{u.name}</span>
                            <span className="text-primary">{u.executions} RUNS</span>
                          </div>
                          <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all duration-1000"
                              style={{ width: `${Math.min((u.executions / 10) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                  <button className="w-full mt-4 flex items-center justify-center space-x-2 py-3 border rounded-xl text-xs font-bold hover:bg-muted transition-all opacity-50 cursor-not-allowed">
                    <ExternalLink className="h-3 w-3" />
                    <span>Advanced Analytics</span>
                  </button>
                </div>
              )}
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
