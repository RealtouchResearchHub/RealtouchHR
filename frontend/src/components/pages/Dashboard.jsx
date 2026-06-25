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
    Users, Calendar, Clock, ArrowRight, TrendingUp, AlertTriangle,
    CheckCircle2, Plus, FileText, ShieldCheck, CreditCard,
} from 'lucide-react';
import {
    BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip,
    PieChart, Pie,
} from 'recharts';
import { cn, getStatusColor } from '../../lib/utils';
import { requestOrDefault } from '../../lib/loaders';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const STATE_MESSAGES = {
    not_assessed:   'No compliance scan has been run yet.',
    demo_data_only: 'Only demo data present. Add real employees first.',
    setup_incomplete: 'Complete company setup to enable scanning.',
    needs_attention: 'Some compliance items need attention.',
    high_risk:       'Compliance issues require urgent attention.',
    compliant:       'All employees meet compliance requirements.',
};

const STATUS_COLORS = {
    active:      '#22c55e',
    onboarding:  '#818cf8',
    on_leave:    '#f59e0b',
    suspended:   '#ef4444',
    draft:       '#94a3b8',
    notice_period: '#f97316',
    leaver:      '#64748b',
    archived:    '#cbd5e1',
};

function ComplianceDonut({ score }) {
    if (score === null || score === undefined) return null;
    const data = [
        { name: 'Score', value: score, fill: score >= 90 ? '#22c55e' : score >= 70 ? '#f59e0b' : '#ef4444' },
        { name: 'Gap', value: 100 - score, fill: '#e2e8f0' },
    ];
    return (
        <PieChart width={140} height={140}>
            <Pie data={data} cx={65} cy={65} innerRadius={50} outerRadius={65} dataKey="value" startAngle={90} endAngle={-270} strokeWidth={0}>
                {data.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
            </Pie>
        </PieChart>
    );
}

export default function Dashboard() {
    const { user, company, token, refreshCompany } = useAuth();
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
                    { total_employees: 0, active_employees: 0, on_leave_today: 0, pending_approvals: 0,
                      compliance_score: null, compliance_state: 'not_assessed', documents_expiring: 0,
                      status_breakdown: {}, next_payroll_date: null, compliance_issues: [] },
                    'dashboard stats'
                ),
                requestOrDefault(
                    axios.get(`${API_URL}/api/employees`, { headers, withCredentials: true }),
                    [], 'dashboard employees'
                ),
                requestOrDefault(
                    axios.get(`${API_URL}/api/leave`, { headers, withCredentials: true }),
                    [], 'dashboard leave'
                ),
                requestOrDefault(
                    axios.get(`${API_URL}/api/demo/status`, { headers, withCredentials: true }),
                    { demo_mode: false }, 'demo status'
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

    useEffect(() => { fetchData(); }, []);

    const handleStartTour = async (steps) => {
        localStorage.setItem('demo_tour_steps', JSON.stringify(steps));
        localStorage.setItem('demo_tour_active', 'true');
        window.dispatchEvent(new Event('demo-tour-start'));
        // Refresh company in case it was auto-created for this new user
        await refreshCompany();
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
    const complianceIssues = stats?.compliance_issues || [];

    const statusBreakdown = stats?.status_breakdown || {};
    const statusChartData = Object.entries(statusBreakdown).map(([status, count]) => ({
        name: status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        count,
        fill: STATUS_COLORS[status] || '#94a3b8',
    }));

    const kpiCards = [
        {
            title: 'Total Employees',
            value: stats?.total_employees || 0,
            icon: Users,
            color: 'text-indigo-600 bg-indigo-100 dark:bg-indigo-900/30',
            link: '/employees',
            sub: `${stats?.active_employees || 0} active`,
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
            title: 'Documents Expiring',
            value: stats?.documents_expiring || 0,
            icon: FileText,
            color: 'text-orange-600 bg-orange-100 dark:bg-orange-900/30',
            link: '/documents',
            sub: 'within 30 days',
        },
        {
            title: 'Compliance Score',
            value: complianceIsAssessed ? `${complianceScore}%` : '—',
            icon: ShieldCheck,
            color: complianceIsAssessed
                ? (complianceScore >= 90 ? 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30'
                    : complianceScore >= 70 ? 'text-amber-600 bg-amber-100 dark:bg-amber-900/30'
                    : 'text-rose-600 bg-rose-100 dark:bg-rose-900/30')
                : 'text-slate-500 bg-slate-100 dark:bg-slate-800',
            link: '/settings',
            sub: complianceIsAssessed
                ? STATE_MESSAGES[complianceState]?.split('.')[0] || ''
                : 'Not assessed yet',
        },
    ];

    return (
        <div className="space-y-6" data-testid="dashboard-page">
            {/* Welcome Header */}
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans'] flex items-center gap-2">
                        Welcome back, {user?.name?.split(' ')[0]}!
                    </h1>
                    <p className="mt-1 text-muted-foreground">
                        {company?.name ? `${company.name} · ` : ''}Here's what's happening with your company today.
                    </p>
                </div>
                {stats?.next_payroll_date && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground border rounded-lg px-3 py-2 whitespace-nowrap">
                        <CreditCard className="w-4 h-4" />
                        Next payroll: <strong>{new Date(stats.next_payroll_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</strong>
                    </div>
                )}
            </div>

            {/* Next Best Action */}
            <NextActionBanner action={stats?.next_action} />

            {/* Demo launcher — compact */}
            <DemoLauncherCard
                isSeeded={demoStatus.demo_mode}
                onStart={handleStartTour}
                onReset={fetchData}
                compact
            />

            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                {kpiCards.map((kpi, i) => (
                    <Link key={i} to={kpi.link}>
                        <Card className="hover:shadow-md transition-all hover-lift cursor-pointer h-full" data-testid={`kpi-${kpi.title.toLowerCase().replace(/\s+/g, '-')}`}>
                            <CardContent className="p-4">
                                <div className="flex items-start justify-between gap-2">
                                    <div className="min-w-0">
                                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide truncate">{kpi.title}</p>
                                        <p className="text-2xl font-bold font-['Plus_Jakarta_Sans'] mt-0.5">{kpi.value}</p>
                                        {kpi.sub && <p className="text-xs text-muted-foreground mt-0.5 truncate">{kpi.sub}</p>}
                                    </div>
                                    <div className={cn('p-2 rounded-lg flex-shrink-0', kpi.color)}>
                                        <kpi.icon className="w-4 h-4" />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                ))}
            </div>

            {/* Main 3-column row */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                {/* Compliance Overview */}
                <Card className="lg:col-span-4" data-testid="compliance-overview-card">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-base flex items-center gap-2">
                            <CheckCircle2 className={cn('w-4 h-4', complianceIsAssessed ? 'text-emerald-600' : 'text-slate-400')} />
                            Compliance Overview
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {complianceIsAssessed ? (
                            <>
                                <div className="flex items-center gap-4">
                                    <div className="relative">
                                        <ComplianceDonut score={complianceScore} />
                                        <div className="absolute inset-0 flex items-center justify-center">
                                            <div className="text-center">
                                                <span className="text-2xl font-bold">{complianceScore}%</span>
                                                <p className="text-xs text-muted-foreground">Overall</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex-1 space-y-1.5 text-sm">
                                        <div className="flex items-center justify-between">
                                            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> Compliant</span>
                                            <span className="font-medium">{complianceScore}%</span>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-400 inline-block" /> Attention</span>
                                            <span className="font-medium">{Math.max(0, 100 - complianceScore - 10)}%</span>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-rose-500 inline-block" /> Issues</span>
                                            <span className="font-medium">{Math.min(100, 100 - complianceScore)}%</span>
                                        </div>
                                    </div>
                                </div>

                                {complianceIssues.length > 0 && (
                                    <div className="mt-4 border-t pt-3">
                                        <p className="text-xs font-semibold text-muted-foreground uppercase mb-2">Needs attention</p>
                                        <div className="space-y-1.5">
                                            {complianceIssues.slice(0, 3).map((issue, i) => (
                                                <div key={i} className="flex items-start gap-2 text-xs">
                                                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                                                    <span className="text-muted-foreground truncate">{issue.employee_name}: {issue.issue}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="flex flex-col items-center py-6 text-center">
                                <ComplianceScore score={null} state={complianceState} size="md" />
                                <p className="mt-3 text-sm text-muted-foreground">{STATE_MESSAGES[complianceState]}</p>
                                <Link to="/ukvi" className="mt-3">
                                    <Button size="sm" variant="outline">Run Compliance Scan</Button>
                                </Link>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Employee Status Chart */}
                <Card className="lg:col-span-4" data-testid="employee-status-card">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-base">Employee Status</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {statusChartData.length > 0 ? (
                            <>
                                <ResponsiveContainer width="100%" height={140}>
                                    <BarChart data={statusChartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                                        <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                                        <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                                        <Tooltip />
                                        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                            {statusChartData.map((entry, i) => (
                                                <Cell key={i} fill={entry.fill} />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                                {stats?.next_payroll_date && (
                                    <div className="mt-3 pt-3 border-t flex items-center gap-2 text-sm">
                                        <CreditCard className="w-4 h-4 text-indigo-500" />
                                        <span className="text-muted-foreground">Next payroll:</span>
                                        <span className="font-medium">
                                            {new Date(stats.next_payroll_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                                        </span>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
                                No employees yet
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Employee Directory */}
                <Card className="lg:col-span-4" data-testid="employees-preview-card">
                    <CardHeader className="pb-2 flex flex-row items-center justify-between">
                        <CardTitle className="text-base">Employee Directory</CardTitle>
                        <Link to="/employees">
                            <Button variant="ghost" size="sm" className="h-7 text-xs">
                                View all <ArrowRight className="w-3 h-3 ml-1" />
                            </Button>
                        </Link>
                    </CardHeader>
                    <CardContent>
                        {employees.length === 0 ? (
                            <div className="text-center py-6">
                                <Users className="w-10 h-10 mx-auto text-muted-foreground/50" />
                                <p className="mt-3 text-sm text-muted-foreground">No employees yet</p>
                                <Link to="/employees/new">
                                    <Button size="sm" className="mt-3" data-testid="add-first-employee-btn">
                                        <Plus className="w-3.5 h-3.5 mr-1.5" /> Add Employee
                                    </Button>
                                </Link>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {employees.map((emp) => {
                                    const hasAlert = emp.compliance_score !== null && emp.compliance_score < 80;
                                    const initials = `${emp.first_name?.[0] || ''}${emp.last_name?.[0] || ''}`;
                                    return (
                                        <Link key={emp.employee_id} to={`/employees/${emp.employee_id}`}
                                            className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-accent transition-colors">
                                            <div className="flex items-center gap-2.5">
                                                {emp.avatar_url ? (
                                                    <img src={emp.avatar_url} alt={initials} className="w-8 h-8 rounded-full object-cover flex-shrink-0" />
                                                ) : (
                                                    <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center flex-shrink-0">
                                                        <span className="text-xs font-semibold text-indigo-700 dark:text-indigo-300">{initials}</span>
                                                    </div>
                                                )}
                                                <div className="min-w-0">
                                                    <p className="text-sm font-medium truncate">{emp.first_name} {emp.last_name}</p>
                                                    <p className="text-xs text-muted-foreground truncate">{emp.job_title || emp.department || '—'}</p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-1.5 flex-shrink-0">
                                                <Badge className={getStatusColor(emp.status)} variant="secondary">
                                                    {emp.status || 'active'}
                                                </Badge>
                                                {hasAlert && <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />}
                                            </div>
                                        </Link>
                                    );
                                })}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* All Employees Table (quick overview) */}
            {employees.length > 0 && (
                <Card data-testid="all-employees-preview">
                    <CardHeader className="pb-3 flex flex-row items-center justify-between">
                        <CardTitle className="text-base">All Employees</CardTitle>
                        <Link to="/employees">
                            <Button variant="ghost" size="sm" className="text-xs">
                                View full list <ArrowRight className="w-3 h-3 ml-1" />
                            </Button>
                        </Link>
                    </CardHeader>
                    <CardContent className="p-0">
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b bg-muted/40">
                                        <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Employee</th>
                                        <th className="text-left px-4 py-2.5 font-medium text-muted-foreground hidden md:table-cell">Department</th>
                                        <th className="text-left px-4 py-2.5 font-medium text-muted-foreground hidden lg:table-cell">Job Title</th>
                                        <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Status</th>
                                        <th className="text-left px-4 py-2.5 font-medium text-muted-foreground hidden md:table-cell">Start Date</th>
                                        <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Compliance</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {employees.map((emp, idx) => {
                                        const initials = `${emp.first_name?.[0] || ''}${emp.last_name?.[0] || ''}`;
                                        const cs = emp.compliance_score;
                                        const csColor = cs === null ? 'text-muted-foreground' : cs >= 90 ? 'text-emerald-600' : cs >= 70 ? 'text-amber-600' : 'text-rose-600';
                                        return (
                                            <tr key={emp.employee_id}
                                                className={cn('border-b last:border-0 hover:bg-accent/50 cursor-pointer', idx % 2 ? 'bg-muted/10' : '')}
                                                onClick={() => window.location.href = `/employees/${emp.employee_id}`}
                                            >
                                                <td className="px-4 py-2.5">
                                                    <div className="flex items-center gap-2.5">
                                                        {emp.avatar_url ? (
                                                            <img src={emp.avatar_url} alt={initials} className="w-7 h-7 rounded-full object-cover" />
                                                        ) : (
                                                            <div className="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-xs font-semibold text-indigo-700">
                                                                {initials}
                                                            </div>
                                                        )}
                                                        <div>
                                                            <p className="font-medium">{emp.first_name} {emp.last_name}</p>
                                                            <p className="text-xs text-muted-foreground">{emp.email}</p>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-2.5 text-muted-foreground hidden md:table-cell">{emp.department || '—'}</td>
                                                <td className="px-4 py-2.5 text-muted-foreground hidden lg:table-cell">{emp.job_title || '—'}</td>
                                                <td className="px-4 py-2.5">
                                                    <Badge className={getStatusColor(emp.status)} variant="secondary">{emp.status || 'active'}</Badge>
                                                </td>
                                                <td className="px-4 py-2.5 text-muted-foreground hidden md:table-cell">
                                                    {emp.start_date ? emp.start_date.slice(0, 10) : '—'}
                                                </td>
                                                <td className="px-4 py-2.5">
                                                    <span className={cn('font-medium text-sm', csColor)}>
                                                        {cs !== null && cs !== undefined ? `${cs}%` : 'Unscanned'}
                                                    </span>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Quick Actions */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                    { to: '/employees/new', icon: Users, label: 'Add Employee', color: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600', testId: 'quick-add-employee' },
                    { to: '/payroll/new', icon: CreditCard, label: 'Run Payroll', color: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600', testId: 'quick-run-payroll' },
                    { to: '/scheduling', icon: Clock, label: 'Scheduling', color: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600', testId: 'quick-scheduling' },
                    { to: '/documents', icon: FileText, label: 'Documents', color: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600', testId: 'quick-documents' },
                ].map(({ to, icon: Icon, label, color, testId }) => (
                    <Link key={to} to={to}>
                        <Card className="hover:shadow-md transition-all hover-lift cursor-pointer h-full" data-testid={testId}>
                            <CardContent className="p-4 flex flex-col items-center text-center">
                                <div className={cn('p-2.5 rounded-xl mb-2', color)}>
                                    <Icon className="w-5 h-5" />
                                </div>
                                <p className="font-medium text-sm">{label}</p>
                            </CardContent>
                        </Card>
                    </Link>
                ))}
            </div>

            {/* What's New */}
            <Card data-testid="whats-new-card">
                <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-indigo-600" />
                        What's New in RealtouchHR
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        {[
                            { date: 'Jun 2026', title: 'UKVI Compliance Scanner', desc: '2 scans/month on all plans.', tag: 'New' },
                            { date: 'Jun 2026', title: 'Employee Lifecycle Statuses', desc: 'Draft → Onboarding → Active → Archived.', tag: 'New' },
                            { date: 'Jun 2026', title: 'RTI Sandbox Go-Live Checklist', desc: '15-item production readiness gate.', tag: 'Improved' },
                            { date: 'Jun 2026', title: 'Updated Plan Pricing', desc: 'Starter £29 · Pro £39 · Enterprise £129.', tag: 'Updated' },
                        ].map((item, i) => (
                            <div key={i} className="flex items-start gap-2.5 p-3 rounded-lg border text-sm">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                        <p className="font-medium">{item.title}</p>
                                        <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${item.tag === 'New' ? 'bg-emerald-100 text-emerald-700' : item.tag === 'Improved' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>{item.tag}</span>
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
                                </div>
                                <span className="text-xs text-muted-foreground whitespace-nowrap">{item.date}</span>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
