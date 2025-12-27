import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { Button } from '../ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '../ui/avatar';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { 
    LayoutDashboard, 
    Users, 
    Calendar, 
    FileText, 
    Clock, 
    CreditCard, 
    Shield, 
    Settings, 
    LogOut,
    Sun,
    Moon,
    Menu,
    X,
    Bot,
    ChevronRight,
    Building2,
    Upload
} from 'lucide-react';
import { cn } from '../../lib/utils';
import AICopilot from '../shared/AICopilot';
import NotificationsPopover from '../shared/NotificationsPopover';

const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Employees', href: '/employees', icon: Users },
    { name: 'Leave', href: '/leave', icon: Calendar },
    { name: 'Documents', href: '/documents', icon: FileText },
    { name: 'Scheduling', href: '/scheduling', icon: Clock },
    { name: 'Payroll', href: '/payroll', icon: CreditCard },
    { name: 'Import', href: '/import', icon: Upload },
    { name: 'Audit Log', href: '/audit', icon: Shield },
    { name: 'Settings', href: '/settings', icon: Settings },
];

export default function MainLayout({ children }) {
    const { user, company, logout } = useAuth();
    const { theme, toggleTheme } = useTheme();
    const location = useLocation();
    const navigate = useNavigate();
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [copilotOpen, setCopilotOpen] = useState(false);

    const handleLogout = async () => {
        await logout();
        navigate('/');
    };

    const initials = user?.name?.split(' ').map(n => n[0]).join('').toUpperCase() || 'U';

    return (
        <div className="min-h-screen bg-background">
            {/* Mobile sidebar overlay */}
            {sidebarOpen && (
                <div 
                    className="fixed inset-0 z-40 bg-black/50 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={cn(
                "fixed inset-y-0 left-0 z-50 w-64 bg-card border-r border-border transform transition-transform duration-300 lg:translate-x-0",
                sidebarOpen ? "translate-x-0" : "-translate-x-full"
            )}>
                <div className="flex flex-col h-full">
                    {/* Logo */}
                    <div className="flex items-center justify-between h-16 px-6 border-b border-border">
                        <Link to="/dashboard" className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
                                <Building2 className="w-5 h-5 text-white" />
                            </div>
                            <span className="font-bold text-lg font-['Plus_Jakarta_Sans']">RealtouchHR</span>
                        </Link>
                        <button 
                            className="lg:hidden p-1 rounded-md hover:bg-accent"
                            onClick={() => setSidebarOpen(false)}
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Company */}
                    {company && (
                        <div className="px-4 py-3 border-b border-border">
                            <p className="text-xs text-muted-foreground uppercase tracking-wide">Company</p>
                            <p className="font-medium truncate">{company.name}</p>
                        </div>
                    )}

                    {/* Navigation */}
                    <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
                        {navigation.map((item) => {
                            const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/');
                            return (
                                <Link
                                    key={item.name}
                                    to={item.href}
                                    onClick={() => setSidebarOpen(false)}
                                    className={cn(
                                        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                                        isActive 
                                            ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20" 
                                            : "text-muted-foreground hover:text-foreground hover:bg-accent"
                                    )}
                                    data-testid={`nav-${item.name.toLowerCase()}`}
                                >
                                    <item.icon className="w-5 h-5" />
                                    {item.name}
                                    {isActive && <ChevronRight className="w-4 h-4 ml-auto" />}
                                </Link>
                            );
                        })}
                    </nav>

                    {/* AI Copilot Button */}
                    <div className="p-4 border-t border-border">
                        <Button
                            onClick={() => setCopilotOpen(true)}
                            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white"
                            data-testid="open-copilot-btn"
                        >
                            <Bot className="w-4 h-4 mr-2" />
                            AI Copilot
                        </Button>
                    </div>
                </div>
            </aside>

            {/* Main content */}
            <div className="lg:pl-64">
                {/* Top bar */}
                <header className="sticky top-0 z-30 h-16 bg-card/80 backdrop-blur-xl border-b border-border">
                    <div className="flex items-center justify-between h-full px-4 lg:px-8">
                        <button 
                            className="lg:hidden p-2 rounded-md hover:bg-accent"
                            onClick={() => setSidebarOpen(true)}
                            data-testid="mobile-menu-btn"
                        >
                            <Menu className="w-5 h-5" />
                        </button>

                        <div className="flex-1" />

                        <div className="flex items-center gap-2">
                            {/* Notifications */}
                            <NotificationsPopover />

                            {/* Theme toggle */}
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={toggleTheme}
                                className="rounded-full"
                                data-testid="theme-toggle-btn"
                            >
                                {theme === 'light' ? (
                                    <Moon className="w-5 h-5" />
                                ) : (
                                    <Sun className="w-5 h-5" />
                                )}
                            </Button>

                            {/* User menu */}
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" className="relative h-10 w-10 rounded-full" data-testid="user-menu-btn">
                                        <Avatar className="h-10 w-10">
                                            <AvatarImage src={user?.picture} alt={user?.name} />
                                            <AvatarFallback className="bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300">
                                                {initials}
                                            </AvatarFallback>
                                        </Avatar>
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent className="w-56" align="end" forceMount>
                                    <div className="flex items-center justify-start gap-2 p-2">
                                        <div className="flex flex-col space-y-1 leading-none">
                                            <p className="font-medium">{user?.name}</p>
                                            <p className="w-[200px] truncate text-sm text-muted-foreground">
                                                {user?.email}
                                            </p>
                                        </div>
                                    </div>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem onClick={() => navigate('/settings')} data-testid="settings-menu-item">
                                        <Settings className="mr-2 h-4 w-4" />
                                        Settings
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem onClick={handleLogout} data-testid="logout-menu-item">
                                        <LogOut className="mr-2 h-4 w-4" />
                                        Log out
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>
                    </div>
                </header>

                {/* Page content */}
                <main className="p-4 lg:p-8">
                    {children}
                </main>
            </div>

            {/* AI Copilot Sidebar */}
            <AICopilot open={copilotOpen} onClose={() => setCopilotOpen(false)} />
        </div>
    );
}
