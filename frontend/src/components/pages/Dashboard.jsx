import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import ComplianceScore from '../shared/ComplianceScore';
import NextActionBanner from '../shared/NextActionBanner';
import { DemoLauncherCard } from '../shared/DemoTour';
import {
    Users,
    Calendar,
    CreditCard,
    Clock,
    ArrowRight,
    TrendingUp,
    AlertTriangle,
    CheckCircle2,
    Plus,
    FileText,
    Bell,
    ShieldCheck,
} from 'lucide-react';
import { cn, formatCurrency, getStatusColor } from '../../lib/utils';
import { requestOrDefault } from '../../lib/loaders';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const STATE_MESSAGES = {
    not_assessed:   'No compliance scan has been run yet. Add employees and run a scan.',
    demo_data_only: 'Only demo data present. Add real employees to see your score.',
    setup_incomplete: 'Company setup is incomplete. Finish setup to enable scanning.',
    needs_attention: 'Some compliance items need attention.',
    high_risk:       'Compliance issues require urgent attention.',
    compliant:       'All employees meet compliance requirements.',
};

export default function Dashboard() {
    const { user, company, token } = useAuth();
    const [stats, setStats] = useState(null);
    const [employees, setEmployees] = useState([]);
    const [recentLeaves, setRecentLeaves] = useState([]);
    const [loading, setLoading] = useState(true);
    const [demoStatus, setDemoStatus] = useState({ demo_mode: false });

    const fetchData = async () => {
        try {
            const headers = { Authorization: `Bearer ${token}` };
            const [statsData, employeesData, leaveData, demoData] = await Promise.all([
                requestOrDefault(
                    axios.get(`${API_URL}/api/dashboard/stats`, { headers, withCredentials: true }),
                    {
                        total_employees: 0,
                        active_employees: 0,
                        on_leave_today: 0,
                        pending_approvals: 0,
                        compliance_score: null,
                        compliance_state: 'not_assessed',
                    },
                    'dashboard stats'
                ),
                requestOrDefault(
                    axios.get(`${API_URL}/api/employees`, { headers, withCredentials: true }),
                    [],
                    'dashboard employees'
                ),
                requestOrDefault(
                    axios.get(`${API_URL}/api/leave`, { headers, withCredentials: true }),
                    [],
                    'dashboard leave'
                ),
                requestOrDefault(
                    axios.get(`${API_URL}/api/demo/status`, { headers, withCredentials: true }),
                    { demo_mode: false },
                    'demo status'
                ),
            ]);
            setStats(statsData);
            setEmployees((Array.isArray(employeesData) ? employeesData : []).slice(0, 5));
            setRecentLeaves((Array.isArray(leaveData) ? leaveData : []).slice(0, 5));
            setDemoStatus(demoData || { demo_mode: false });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleStartTour = (steps) => {
        localStorage.setItem('demo_tour_steps', JSON.stringify(steps));
        localStorage.setItem('demo_tour_active', 'true');
        window.dispatchEvent(new Event('demo-tour-start'));
        fetchData();
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    const complianceScore = stats?.compliance_score ?? null;
    const complianceState = stats?.compliance_state || 'not_assessed';
    const complianceIsAssessed = complianceScore !== null && complianceScore !== undefined;

    const statCards = [
        {
            title: 'Total Employees',
            value: stats?.total_employees || 0,
            icon: Users,
            color: 'text-indigo-600 bg-indigo-100 dark:bg-indigo-900/30',
            link: '/employees',
        },
        {
            title: 'On Leave Today',
            value: stats?.on_leave_today || 0,
            icon: Calendar,
            color: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30',
            link: '/leave',
        },
        {
            title: 'Pending Approvals',
            value: stats?.pending_approvals || 0,
            icon: Clock,
            color: 'text-rose-600 bg-rose-100 dark:bg-rose-900/30',
            link: '/leave',
        },
        {
            title: 'Compliance Status',
            value: complianceIsAssessed ? `${complianceScore}%` : '—',
            icon: ShieldCheck,
            color: complianceIsAssessed
                ? (complianceScore >= 90 ? 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30'
                    : complianceScore >= 70 ? 'text-amber-600 bg-amber-100 dark:bg-amber-900/30'
                    : 'text-rose-600 bg-rose-100 dark:bg-rose-900/30')
                : 'text-slate-500 bg-slate-100 dark:bg-slate-800',
            link: '/settings',
            subtitle: complianceIsAssessed ? null : 'Not assessed yet',
        },
    ];

    return (
        <div className="space-y-8" data-testid="dashboard-page">
            {/* Welcome Header */}
            <div>
                <h1 className="text-3xl lg:text-4xl font-bold font-['Plus_Jakarta_Sans'] text-foreground">
                    Welcome back, {user?.name?.split(' ')[0]}
                </h1>
                <p className="mt-2 text-lg text-muted-foreground">
                    {company?.name ? `${company.name} · ` : ''}Here's what's happening with your HR today.
                </p>
            </div>

            {/* Next Best Action */}
            <NextActionBanner action={stats?.next_action} />

            {/* Demo launcher */}
            <DemoLauncherCard
                isSeeded={demoStatus.demo_mode}
                onStart={handleStartTour}
                onReset={fetchData}
            />

            {/* KPI Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {statCards.map((stat, index) => (
                    <Link key={index} to={stat.link}>
                        <Card
                            className="hover:shadow-md transition-all hover-lift cursor-pointer h-full"
                            data-testid={`stat-card-${stat.title.toLowerCase().replace(/\s+/g, '-')}`}
                        >
                            <CardContent className="p-5">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{stat.title}</p>
                                        <p className="text-2xl font-bold font-['Plus_Jakarta_Sans'] mt-1">{stat.value}</p>
                                        {stat.subtitle && (
                                            <p className="text-xs text-muted-foreground mt-0.5">{stat.subtitle}</p>
                                        )}
                                    </div>
                                    <div className={cn('p-2.5 rounded-xl flex-shrink-0', stat.color)}>
                                        <stat.icon className="w-5 h-5" />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                ))}
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Compliance Score Card */}
                <Card
                    className={cn(
                        'lg:col-span-4 relative overflow-hidden',
                        complianceIsAssessed
                            ? 'bg-gradient-to-br from-emerald-50 to-white dark:from-emerald-950/30 dark:to-background border-emerald-100 dark:border-emerald-900/50'
                            : 'bg-gradient-to-br from-slate-50 to-white dark:from-slate-900/30 dark:to-background'
                    )}
                    data-testid="compliance-score-card"
                >
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <CheckCircle2 className={cn('w-5 h-5', complianceIsAssessed ? 'text-emerald-600' : 'text-slate-400')} />
                            Compliance Status
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="flex flex-col items-center py-6">
                        <ComplianceScore score={complianceScore} state={complianceState} size="lg" />
                        <p className="mt-4 text-center text-sm text-muted-foreground px-2">
                            {STATE_MESSAGES[complianceState] || (
                                complianceIsAssessed && complianceScore >= 90
                                    ? 'Excellent! Your compliance is in great shape.'
                                    : complianceIsAssessed && complianceScore >= 70
                                        ? 'Good, but there are some items to address.'
                                        : 'Attention needed. Please review compliance tasks.'
                            )}
                        </p>
                        <Link to="/settings" className="mt-4">
                            <Button variant="outline" size="sm">
                                {complianceIsAssessed ? 'View Details' : 'Run Compliance Scan'}
                                <ArrowRight className="w-4 h-4 ml-2" />
                            </Button>
                        </Link>
                    </CardContent>
                </Card>

                {/* Employee Directory Preview */}
                <Card className="lg:col-span-8" data-testid="employees-preview-card">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle>Employee Directory</CardTitle>
                        <Link to="/employees">
                            <Button variant="ghost" size="sm">
                                View All
                                <ArrowRight className="w-4 h-4 ml-1" />
                            </Button>
                        </Link>
                    </CardHeader>
                    <CardContent>
                        {employees.length === 0 ? (
                            <div className="text-center py-8">
                                <Users className="w-12 h-12 mx-auto text-muted-foreground/50" />
                                <p className="mt-4 text-muted-foreground">No employees yet</p>
                                <Link to="/employees/new">
                                    <Button className="mt-4" data-testid="add-first-employee-btn">
                                        <Plus className="w-4 h-4 mr-2" />
                                        Add Your First Employee
                                    </Button>
                                </Link>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {employees.map((emp) => {
                                    const hasAlerts = emp.compliance_score !== null && emp.compliance_score < 80;
                                    return (
                                        <Link
                                            key={emp.employee_id}
                                            to={`/employees/${emp.employee_id}`}
                                            className="flex items-center justify-between p-3 rounded-lg hover:bg-accent transition-colors"
                                        >
                                            <div className="flex items-center gap-3">
                                                <div className="w-9 h-9 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center flex-shrink-0">
                                                    <span className="text-xs font-semibold text-indigo-700 dark:text-indigo-300">
                                                        {emp.first_name?.[0]}{emp.last_name?.[0]}
                                                    </span>
                                                </div>
                                                <div>
                                                    <p className="font-medium text-sm">{emp.first_name} {emp.last_name}</p>
                                                    <p className="text-xs text-muted-foreground">{emp.job_title || emp.department || 'No title'}</p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Badge className={getStatusColor(emp.status)} variant="secondary">
                                                    {emp.status || 'active'}
                                                </Badge>
                                                {hasAlerts && (
                                                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                                                )}
                                                {emp.compliance_score === null && (
                                                    <span className="text-xs text-muted-foreground">Unscanned</span>
                                                )}
                                            </div>
                                        </Link>
                                    );
                                })}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Recent Leave Requests */}
            {recentLeaves.length > 0 && (
                <Card data-testid="recent-leave-card">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="flex items-center gap-2">
                            <Calendar className="w-5 h-5 text-amber-600" />
                            Recent Leave Requests
                        </CardTitle>
                        <Link to="/leave">
                            <Button variant="ghost" size="sm">
                                View All <ArrowRight className="w-4 h-4 ml-1" />
                            </Button>
                        </Link>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {recentLeaves.map(leave => (
                                <div key={leave.leave_id} className="flex items-center justify-between p-2 rounded-lg border text-sm">
                                    <div>
                                        <p className="font-medium capitalize">{leave.leave_type?.replace(/_/g, ' ')}</p>
                                        <p className="text-xs text-muted-foreground">{leave.start_date} → {leave.end_date}</p>
                                    </div>
                                    <Badge className={
                                        leave.status === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                                        leave.status === 'rejected' ? 'bg-red-100 text-red-700' :
                                        'bg-amber-100 text-amber-700'
                                    }>
                                        {leave.status}
                                    </Badge>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* What's New */}
            <Card data-testid="whats-new-card">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-indigo-600" />
                        What's New in RealtouchHR
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        {[
                            { date: 'Jun 2026', title: 'UKVI Compliance Scanner', desc: '2 scans/month on all plans. PDF & DOCX reports available.', tag: 'New' },
                            { date: 'Jun 2026', title: 'Employee Lifecycle Statuses', desc: 'Track employees from Draft → Onboarding → Active → Archived with immutable history.', tag: 'New' },
                            { date: 'Jun 2026', title: 'RTI Sandbox Go-Live Checklist', desc: '15-item production readiness gate before enabling live HMRC submissions.', tag: 'Improved' },
                            { date: 'Jun 2026', title: 'Updated Plan Pricing', desc: 'Starter £29 · Professional £39 · Enterprise £129. Payslip previews now free.', tag: 'Updated' },
                        ].map((item, i) => (
                            <div key={i} className="flex items-start gap-3 p-3 rounded-lg border">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <p className="font-medium text-sm">{item.title}</p>
                                        <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                                            item.tag === 'New' ? 'bg-emerald-100 text-emerald-700' :
                                            item.tag === 'Improved' ? 'bg-blue-100 text-blue-700' :
                                            'bg-amber-100 text-amber-700'
                                        }`}>{item.tag}</span>
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
                                </div>
                                <span className="text-xs text-muted-foreground whitespace-nowrap">{item.date}</span>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Quick Actions */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Link to="/employees/new">
                    <Card className="hover:shadow-md transition-all hover-lift cursor-pointer h-full" data-testid="quick-add-employee">
                        <CardContent className="p-6 flex flex-col items-center text-center">
                            <div className="p-3 rounded-xl bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 mb-3">
                                <Users className="w-6 h-6" />
                            </div>
                            <p className="font-medium">Add Employee</p>
                        </CardContent>
                    </Card>
                </Link>
                <Link to="/payroll/new">
                    <Card className="hover:shadow-md transition-all hover-lift cursor-pointer h-full" data-testid="quick-run-payroll">
                        <CardContent className="p-6 flex flex-col items-center text-center">
                            <div className="p-3 rounded-xl bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 mb-3">
                                <CreditCard className="w-6 h-6" />
                            </div>
                            <p className="font-medium">Run Payroll</p>
                        </CardContent>
                    </Card>
                </Link>
                <Link to="/scheduling">
                    <Card className="hover:shadow-md transition-all hover-lift cursor-pointer h-full" data-testid="quick-scheduling">
                        <CardContent className="p-6 flex flex-col items-center text-center">
                            <div className="p-3 rounded-xl bg-amber-100 dark:bg-amber-900/30 text-amber-600 mb-3">
                                <Clock className="w-6 h-6" />
                            </div>
                            <p className="font-medium">Scheduling</p>
                        </CardContent>
                    </Card>
                </Link>
                <Link to="/documents">
                    <Card className="hover:shadow-md transition-all hover-lift cursor-pointer h-full" data-testid="quick-documents">
                        <CardContent className="p-6 flex flex-col items-center text-center">
                            <div className="p-3 rounded-xl bg-purple-100 dark:bg-purple-900/30 text-purple-600 mb-3">
                                <FileText className="w-6 h-6" />
                            </div>
                            <p className="font-medium">Documents</p>
                        </CardContent>
                    </Card>
                </Link>
            </div>
        </div>
    );
}
