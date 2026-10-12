'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    BarChart3,
    Library,
    LogOut,
    PlayCircle,
    Network,
    LayoutDashboard,
    User as UserIcon
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';

export default function Sidebar() {
    const pathname = usePathname();
    const { user, logout } = useAuth();

    if (pathname === '/login' || !user) return null;

    const navigation = [
        { name: 'Dashboard', href: '/', icon: LayoutDashboard, roles: ['architect', 'prompt_engineer'] },
        { name: 'Prompt Library', href: '/prompts', icon: Library, roles: ['prompt_engineer'] },
        { name: 'Modelling Chains', href: '/chains', icon: Network, roles: ['prompt_engineer'] },
        { name: 'Workbench', href: '/workbench', icon: PlayCircle, roles: ['architect'] },
        { name: 'Analytics', href: '/analytics', icon: BarChart3, roles: ['prompt_engineer'] },
    ];

    const filteredNavigation = navigation.filter(item => item.roles.includes(user.role));

    return (
        <div className="flex h-full w-64 flex-col bg-primary text-primary-foreground border-r border-border">
            <div className="flex h-16 shrink-0 items-center px-6">
                <h1 className="text-xl font-bold tracking-tight italic">Enterprise Modelling</h1>
            </div>

            <div className="px-6 py-4 flex items-center space-x-3 bg-accent/10 border-y border-primary-foreground/10 mb-2">
                <div className="h-8 w-8 rounded-full bg-accent flex items-center justify-center text-accent-foreground">
                    <UserIcon className="h-4 w-4" />
                </div>
                <div className="flex flex-col overflow-hidden text-xs">
                    <span className="font-bold truncate">{user.full_name}</span>
                    <span className="opacity-60 capitalize">{user.role.replace('_', ' ')}</span>
                </div>
            </div>

            <nav className="flex flex-1 flex-col px-4 py-4 space-y-1">
                {filteredNavigation.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={cn(
                                'group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                                isActive
                                    ? 'bg-accent text-accent-foreground'
                                    : 'text-primary-foreground/70 hover:bg-accent/50 hover:text-accent-foreground'
                            )}
                        >
                            <item.icon
                                className={cn(
                                    'mr-3 h-5 w-5 shrink-0 transition-colors',
                                    isActive ? 'text-accent-foreground' : 'text-primary-foreground/40 group-hover:text-accent-foreground'
                                )}
                                aria-hidden="true"
                            />
                            {item.name}
                        </Link>
                    );
                })}
            </nav>

            <div className="flex shrink-0 p-4 border-t border-primary-foreground/10">
                <button
                    onClick={logout}
                    className="flex w-full items-center px-3 py-2 text-sm font-medium text-primary-foreground/70 rounded-md hover:bg-destructive/20 hover:text-destructive-foreground transition-colors group"
                >
                    <LogOut className="mr-3 h-5 w-5 shrink-0 text-primary-foreground/40 group-hover:text-destructive-foreground" aria-hidden="true" />
                    Sign Out
                </button>
            </div>
        </div>
    );
}
