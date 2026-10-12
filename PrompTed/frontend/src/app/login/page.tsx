'use client';

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import axios from 'axios';
import { Lock, User, Loader2, Sparkles } from 'lucide-react';

export default function LoginPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
            const response = await axios.post(`${API_URL}/auth/login`, {
                username,
                password,
            });
            login(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to login. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-950 px-4">
            <div className="w-full max-w-md space-y-8">
                <div className="text-center">
                    <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg mb-4">
                        <Sparkles className="h-6 w-6" />
                    </div>
                    <h1 className="text-3xl font-bold tracking-tight text-foreground">Welcome Back</h1>
                    <p className="mt-2 text-sm text-muted-foreground">
                        Sign in to access your Enterprise Modelling workspace
                    </p>
                </div>

                <div className="rounded-2xl border bg-card p-8 shadow-sm">
                    <form className="space-y-6" onSubmit={handleSubmit}>
                        <div className="space-y-2">
                            <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70" htmlFor="username">
                                Username
                            </label>
                            <div className="relative">
                                <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                <input
                                    id="username"
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-10 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                    placeholder="e.g. architect"
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium leading-none" htmlFor="password">
                                Password
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                <input
                                    id="password"
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-10 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        {error && (
                            <div className="text-sm font-medium text-destructive bg-destructive/10 p-3 rounded-md border border-destructive/20 text-center">
                                {error}
                            </div>
                        )}

                        <button
                            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground shadow transition-all hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 w-full"
                            type="submit"
                            disabled={loading}
                        >
                            {loading ? (
                                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Signing in...</>
                            ) : (
                                'Sign In'
                            )}
                        </button>
                    </form>

                    <div className="mt-8 pt-6 border-t border-dashed">
                        <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground text-center mb-4">Development Accounts</h4>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="text-[11px] bg-muted/50 p-2 rounded-md border border-border">
                                <span className="font-bold text-foreground">Architect:</span>
                                <div className="mt-1 opacity-70">u: architect</div>
                                <div className="opacity-70">p: password123</div>
                            </div>
                            <div className="text-[11px] bg-muted/50 p-2 rounded-md border border-border">
                                <span className="font-bold text-foreground">Engineer:</span>
                                <div className="mt-1 opacity-70">u: engineer</div>
                                <div className="opacity-70">p: password123</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
