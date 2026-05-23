import React, { useState, useEffect } from 'react';
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
    Upload,
    UserCircle,
    Send,
    Globe,
    Briefcase,
    Receipt,
    HeartPulse,
    CalendarCheck,
    Sparkles,
    Target,
    Scale,
    Lock,
    FileLock2,
    Award,
    ScrollText,
    GraduationCap,
    Thermometer,
    CalendarClock,
    ClipboardList
} from 'lucide-react';
import { cn } from '../../lib/utils';
import AICopilot from '../shared/AICopilot';
import NotificationsPopover from '../shared/NotificationsPopover';
import DemoTour from '../shared/DemoTour';
import TrialBanner from '../shared/TrialBanner';

const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Employees', href: '/employees', icon: Users },
    { name: 'Leave', href: '/leave', icon: Calendar },
    { name: 'Documents', href: '/documents', icon: FileText },
    { name: 'Time Tracking', href: '/time-tracking', icon: Clock },
    { name: 'Scheduling', href: '/scheduling', icon: Clock },
    { name: 'Payroll', href: '/payroll', icon: CreditCard },
    { name: 'Statutory Pay', href: '/statutory', icon: HeartPulse },
    { name: 'Year-End', href: '/year-end', icon: CalendarCheck },
    { name: 'HMRC RTI', href: '/hmrc', icon: Send },
    { name: 'RTI Sync', href: '/rti-sync', icon: Shield },
    { name: 'UKVI Compliance', href: '/ukvi', icon: Globe },
    { name: 'Import', href: '/import', icon: Upload },
    { name: 'Audit Log', href: '/audit', icon: Building2 },
    { name: 'Self-Service', href: '/self-service', icon: UserCircle },
    { name: 'Enterprise', href: '/enterprise', icon: Briefcase },
    { name: 'Performance', href: '/performance', icon: Target },
    { name: 'Cases', href: '/cases', icon: Scale, hrOnly: true },
    { name: 'Absence', href: '/absence', icon: Thermometer, hrOnly: true },
    { name: 'Policies', href: '/policies', icon: ScrollText },
    { name: 'Training', href: '/training', icon: GraduationCap },
    { name: 'HR Analytics', href: '/hr-analytics', icon: CalendarClock, hrOnly: true },
    { name: 'Data Protection', href: '/dpo', icon: ClipboardList, hrOnly: true },
    { name: 'GDPR Centre', href: '/gdpr', icon: FileLock2 },
    { name: 'Security', href: '/security', icon: Lock },
    { name: 'Trust Badge', href: '/trust-badge', icon: Award, ownerOnly: true },
    { name: 'Admin', href: '/admin', icon: Shield, adminOnly: true },
    { name: 'Super Admin', href: '/super-admin', icon: Shield, platformAdminOnly: true },
    { name: 'Billing', href: '/billing', icon: Receipt, ownerOnly: true },
    { name: 'Settings', href: '/settings', icon: Settings },
];

export default function MainLayout({ children }) {
    const { user, company, logout } = useAuth();
    const { theme, toggleTheme } = useTheme();
    const location = useLocation();
    const navigate = useNavigate();
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [copilotOpen, setCopilotOpen] = useState(false);
    const [tourOpen, setTourOpen] = useState(false);
    const [tourSteps, setTourSteps] = useState([]);

    useEffect(() => {
        const loadTour = () => {
            const active = localStorage.getItem('demo_tour_active') === 'true';
            const stepsRaw = localStorage.getItem('demo_tour_steps');
            if (active && stepsRaw) {
                try {
                    const steps = JSON.parse(stepsRaw);
                    if (steps?.length) {
                        setTourSteps(steps);
                        setTourOpen(true);
                    }
                } catch (e) { /* ignore */ }
            }
        };
        loadTour();
        window.addEventListener('demo-tour-start', loadTour);
        return () => window.removeEventListener('demo-tour-start', loadTour);
    }, []);

    const closeTour = () => {
        setTourOpen(false);
        localStorage.removeItem('demo_tour_active');
        localStorage.removeItem('demo_tour_steps');
    };

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
                        {navigation
                            .filter((item) => {
                                if (item.ownerOnly && user?.role !== 'owner') return false;
                                if (item.adminOnly && user?.role !== 'owner' && user?.role !== 'admin') return false;
                                if (item.hrOnly && !['owner', 'admin', 'hr_manager'].includes(user?.role)) return false;
                                if (item.platformAdminOnly && !user?.is_platform_admin) return false;
                                return true;
                            })
                            .map((item) => {
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

                {/* Sandbox demo banner */}
                {user?.is_sandbox && (
                    <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-4 py-2 text-xs flex items-center justify-between" data-testid="sandbox-banner">
                        <div className="flex items-center gap-2">
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>
                                You're in a <strong>sandbox demo</strong>. Data will be wiped after 24h — <Link to="/register" className="underline font-semibold">create a real account</Link> to keep it.
                            </span>
                        </div>
                        <Link to="/billing" className="underline font-semibold hover:opacity-80">Upgrade →</Link>
                    </div>
                )}

                {/* Trial banner for non-sandbox trial companies */}
                {!user?.is_sandbox && <TrialBanner />}

                {/* Page content */}
                <main className="p-4 lg:p-8">
                    {children}
                </main>
            </div>

            {/* AI Copilot Sidebar */}
            <AICopilot open={copilotOpen} onClose={() => setCopilotOpen(false)} />

            {/* Demo Tour overlay */}
            <DemoTour
                open={tourOpen}
                steps={tourSteps}
                onClose={closeTour}
                onComplete={closeTour}
            />
        </div>
    );
}
