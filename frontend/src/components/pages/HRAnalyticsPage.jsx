import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { toast } from 'sonner';
import { CalendarClock, BarChart3, Network, Loader2, Download, AlertTriangle, TrendingUp, Users, LayoutList, GitBranch } from 'lucide-react';
import { cn } from '../../lib/utils';

import { useAuth } from '../../contexts/AuthContext';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

export default function HRAnalyticsPage() {
    const { token } = useAuth();
    const auth = () => ({ headers: { Authorization: `Bearer ${token}` }, withCredentials: true });
    const [tab, setTab] = useState('calendar');
    const [calendar, setCalendar] = useState(null);
    const [summary, setSummary] = useState(null);
    const [tree, setTree] = useState(null);
    const [loading, setLoading] = useState(true);
    const [orgView, setOrgView] = useState('list');

    const load = async () => {
        setLoading(true);
        try {
            const [c, s, t] = await Promise.allSettled([
                axios.get(`${API_URL}/api/compliance-calendar?days_ahead=180`, auth()),
                axios.get(`${API_URL}/api/hr-reports/summary`, auth()),
                axios.get(`${API_URL}/api/org-chart`, auth()),
            ]);
            if (c.status === 'fulfilled') setCalendar(c.value.data);
            if (s.status === 'fulfilled') setSummary(s.value.data);
            if (t.status === 'fulfilled') setTree(t.value.data);
        } catch (e) { /* ignore */ } finally { setLoading(false); }
    };
    useEffect(() => { load(); }, []);

    const sev = (s) => ({ high: 'bg-red-100 text-red-700', medium: 'bg-amber-100 text-amber-700', low: 'bg-slate-100 text-slate-700' }[s]);

    const downloadHeadcount = async () => {
        try {
            const res = await axios.get(`${API_URL}/api/hr-reports/headcount.csv`, { ...auth(), responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const a = document.createElement('a');
            a.href = url; a.download = `headcount_${new Date().toISOString().slice(0,10)}.csv`;
            a.click(); window.URL.revokeObjectURL(url);
            toast.success('Downloaded');
        } catch (e) { toast.error('Failed'); }
    };

    return (
        <div className="space-y-6" data-testid="hr-analytics-page">
            <div>
                <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">HR Analytics</h1>
                <p className="text-muted-foreground mt-1">Compliance calendar, workforce reports, and organisation chart.</p>
            </div>

            <Tabs value={tab} onValueChange={setTab}>
                <TabsList>
                    <TabsTrigger value="calendar" data-testid="tab-calendar"><CalendarClock className="w-4 h-4 mr-2" /> Compliance Calendar</TabsTrigger>
                    <TabsTrigger value="reports" data-testid="tab-reports"><BarChart3 className="w-4 h-4 mr-2" /> Reports</TabsTrigger>
                    <TabsTrigger value="orgchart" data-testid="tab-orgchart"><Network className="w-4 h-4 mr-2" /> Org Chart</TabsTrigger>
                </TabsList>

                <TabsContent value="calendar">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle>Next 180 days</CardTitle>
                            {calendar && (
                                <div className="flex gap-2">
                                    <Badge className={sev('high')}>{calendar.summary.high} high</Badge>
                                    <Badge className={sev('medium')}>{calendar.summary.medium} medium</Badge>
                                    <Badge className={sev('low')}>{calendar.summary.low} low</Badge>
                                </div>
                            )}
                        </CardHeader>
                        <CardContent>
                            {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : !calendar || calendar.events.length === 0 ? (
                                <p className="text-sm text-muted-foreground">Nothing on the compliance calendar in the next 180 days. Good standing.</p>
                            ) : (
                                <div className="space-y-1" data-testid="calendar-events">
                                    {calendar.events.map((e, i) => (
                                        <div key={i} className="flex items-center justify-between p-3 border rounded-lg">
                                            <div className="flex items-center gap-3">
                                                <div className="text-xs text-muted-foreground font-mono w-24">{e.date}</div>
                                                <div>
                                                    <p className="text-sm font-medium">{e.title}</p>
                                                    <p className="text-xs text-muted-foreground capitalize">{e.category.replace('_', ' ')}</p>
                                                </div>
                                            </div>
                                            <Badge className={sev(e.severity)}>{e.severity}</Badge>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="reports">
                    {summary ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                <Stat label="Active headcount" value={summary.headcount.active} icon={Users} />
                                <Stat label="Starters (12m)" value={summary.starters_last_12m} icon={TrendingUp} />
                                <Stat label="Leavers (12m)" value={summary.leavers_last_12m} icon={AlertTriangle} />
                                <Stat label="Turnover" value={`${summary.turnover_percent}%`} icon={BarChart3} />
                            </div>
                            <Card>
                                <CardHeader className="flex flex-row items-center justify-between">
                                    <CardTitle>Headcount</CardTitle>
                                    <Button size="sm" variant="outline" onClick={downloadHeadcount} data-testid="export-headcount-btn"><Download className="w-4 h-4 mr-2" />Export CSV</Button>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    <Breakdown title="By department" data={summary.department_breakdown} />
                                    <Breakdown title="By gender" data={summary.gender_breakdown} />
                                </CardContent>
                            </Card>
                            <Card>
                                <CardHeader><CardTitle>Absence (rolling 12m)</CardTitle></CardHeader>
                                <CardContent>
                                    <p className="text-sm">Total days lost: <strong>{summary.absence.total_days_12m}</strong></p>
                                    <p className="text-sm">Episodes: <strong>{summary.absence.episodes_12m}</strong></p>
                                    <p className="text-sm">Average days per employee: <strong>{summary.absence.avg_days_per_employee}</strong></p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardHeader><CardTitle>Mandatory training compliance</CardTitle></CardHeader>
                                <CardContent>
                                    <div className="flex items-baseline gap-3">
                                        <span className="text-3xl font-bold">{summary.training_compliance_percent}%</span>
                                        <span className="text-sm text-muted-foreground">{summary.training_completed_total} of {summary.training_required_total} required completions</span>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    ) : <Loader2 className="w-6 h-6 animate-spin" />}
                </TabsContent>

                <TabsContent value="orgchart">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle>Organisation Chart</CardTitle>
                            <div className="flex gap-1 border rounded-lg p-1">
                                <Button
                                    size="sm"
                                    variant={orgView === 'list' ? 'default' : 'ghost'}
                                    className="h-7 px-2"
                                    onClick={() => setOrgView('list')}
                                >
                                    <LayoutList className="w-3.5 h-3.5 mr-1" /> List
                                </Button>
                                <Button
                                    size="sm"
                                    variant={orgView === 'tree' ? 'default' : 'ghost'}
                                    className="h-7 px-2"
                                    onClick={() => setOrgView('tree')}
                                >
                                    <GitBranch className="w-3.5 h-3.5 mr-1" /> Tree
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            {tree && tree.tree && tree.tree.length > 0 ? (
                                <>
                                    <p className="text-xs text-muted-foreground mb-4">
                                        {tree.stats.total_employees} employees · {tree.stats.total_managers} managers · {tree.stats.max_depth} levels
                                    </p>
                                    {tree.stats.total_managers === 0 && (
                                        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800 px-4 py-3 text-sm text-amber-800 dark:text-amber-300 flex items-start gap-2">
                                            <span className="mt-0.5 shrink-0">⚠</span>
                                            <span>No line managers assigned yet — the chart shows all employees at the same level. Go to each employee's <strong>Employment</strong> tab and set their <strong>Line Manager</strong> to build the hierarchy.</span>
                                        </div>
                                    )}
                                    {orgView === 'list' ? (
                                        <div className="space-y-1" data-testid="org-list">
                                            {tree.tree.map((n) => <OrgNode key={n.employee_id} node={n} depth={0} />)}
                                        </div>
                                    ) : (
                                        <div className="overflow-x-auto pb-4" data-testid="org-tree-visual">
                                            <div className="flex gap-10 min-w-max py-6 px-4 justify-center">
                                                {tree.tree.map((n) => (
                                                    <OrgTreeNode key={n.employee_id} node={n} isRoot={true} />
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </>
                            ) : <p className="text-sm text-muted-foreground">No employees with line manager relationships yet. Set line managers on employee profiles to build the chart.</p>}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}

function Stat({ label, value, icon: Icon }) {
    return (
        <Card>
            <CardContent className="p-4 flex items-center justify-between">
                <div>
                    <p className="text-xs text-muted-foreground">{label}</p>
                    <p className="text-2xl font-semibold">{value}</p>
                </div>
                <Icon className="w-5 h-5 text-indigo-500" />
            </CardContent>
        </Card>
    );
}

function Breakdown({ title, data }) {
    const entries = Object.entries(data || {});
    const total = entries.reduce((s, [, v]) => s + v, 0) || 1;
    return (
        <div>
            <p className="text-sm font-medium mb-1">{title}</p>
            <div className="space-y-1">
                {entries.map(([k, v]) => (
                    <div key={k} className="flex items-center gap-2 text-xs">
                        <span className="w-32 truncate">{k}</span>
                        <div className="flex-1 h-2 bg-muted rounded overflow-hidden">
                            <div className="h-full bg-indigo-500" style={{ width: `${(v / total) * 100}%` }} />
                        </div>
                        <span className="w-10 text-right tabular-nums">{v}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function OrgNode({ node, depth }) {
    return (
        <div style={{ marginLeft: depth * 18 }}>
            <div className="flex items-center gap-2 p-2 rounded border bg-card my-1">
                {node.avatar_url ? (
                    <img src={node.avatar_url} alt={node.name} className="w-7 h-7 rounded-full object-cover flex-shrink-0" />
                ) : (
                    <div className="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center text-xs font-semibold text-indigo-700 dark:text-indigo-200 flex-shrink-0">
                        {(node.name || '').split(' ').map((s) => s[0]).slice(0, 2).join('')}
                    </div>
                )}
                <div>
                    <p className="text-sm font-medium">{node.name || 'Unnamed'}</p>
                    <p className="text-xs text-muted-foreground">{node.title || '—'} {node.department ? `· ${node.department}` : ''}</p>
                </div>
            </div>
            {(node.reports || []).map((c) => <OrgNode key={c.employee_id} node={c} depth={depth + 1} />)}
        </div>
    );
}

const DEPT_RING = {
    'Engineering':  'ring-indigo-400',
    'Product':      'ring-purple-400',
    'Design':       'ring-pink-400',
    'Sales':        'ring-emerald-400',
    'HR':           'ring-teal-400',
    'Finance':      'ring-amber-400',
    'Management':   'ring-violet-500',
    'Operations':   'ring-cyan-400',
    'Marketing':    'ring-rose-400',
};
const DEPT_BG = {
    'Engineering':  'bg-indigo-100 dark:bg-indigo-900',
    'Product':      'bg-purple-100 dark:bg-purple-900',
    'Design':       'bg-pink-100 dark:bg-pink-900',
    'Sales':        'bg-emerald-100 dark:bg-emerald-900',
    'HR':           'bg-teal-100 dark:bg-teal-900',
    'Finance':      'bg-amber-100 dark:bg-amber-900',
    'Management':   'bg-violet-100 dark:bg-violet-900',
    'Operations':   'bg-cyan-100 dark:bg-cyan-900',
    'Marketing':    'bg-rose-100 dark:bg-rose-900',
};
const DEPT_TEXT = {
    'Engineering':  'text-indigo-700 dark:text-indigo-300',
    'Product':      'text-purple-700 dark:text-purple-300',
    'Design':       'text-pink-700 dark:text-pink-300',
    'Sales':        'text-emerald-700 dark:text-emerald-300',
    'HR':           'text-teal-700 dark:text-teal-300',
    'Finance':      'text-amber-700 dark:text-amber-300',
    'Management':   'text-violet-700 dark:text-violet-300',
    'Operations':   'text-cyan-700 dark:text-cyan-300',
    'Marketing':    'text-rose-700 dark:text-rose-300',
};

function OrgTreeCard({ node, isRoot = false }) {
    const initials = (node.name || '').split(' ').map(s => s[0]).slice(0, 2).join('');
    const dept = node.department || '';
    const ring = DEPT_RING[dept] || 'ring-slate-400';
    const bg   = DEPT_BG[dept]   || 'bg-slate-100 dark:bg-slate-800';
    const txt  = DEPT_TEXT[dept]  || 'text-slate-700 dark:text-slate-300';
    const avatarSize = isRoot ? 'w-20 h-20' : 'w-16 h-16';
    const initialsSize = isRoot ? 'text-2xl' : 'text-lg';

    return (
        <div className="flex flex-col items-center select-none">
            {/* Circular avatar with ring */}
            <div className={cn(
                avatarSize,
                'rounded-full ring-4 ring-offset-2 ring-offset-background overflow-hidden shadow-md flex-shrink-0',
                ring
            )}>
                {node.avatar_url ? (
                    <img src={node.avatar_url} alt={node.name} className="w-full h-full object-cover" />
                ) : (
                    <div className={cn('w-full h-full flex items-center justify-center font-bold', bg, initialsSize, txt)}>
                        {initials}
                    </div>
                )}
            </div>
            {/* Name card */}
            <div className="mt-3 bg-card border border-border rounded-xl shadow-sm px-3 py-2.5 text-center w-36 hover:shadow-md transition-shadow">
                <p className="text-xs font-bold text-foreground leading-tight">{node.name || 'Unnamed'}</p>
                {node.title && <p className="text-[10px] text-muted-foreground mt-0.5 leading-tight">{node.title}</p>}
                {node.department && <p className={cn('text-[10px] font-semibold mt-1', txt)}>{node.department}</p>}
            </div>
        </div>
    );
}

function OrgTreeNode({ node, isRoot = false }) {
    const reports = node.reports || [];

    return (
        <div className="flex flex-col items-center">
            <OrgTreeCard node={node} isRoot={isRoot} />

            {reports.length > 0 && (
                <>
                    {/* Vertical stem from parent down */}
                    <div className="w-0.5 h-8 bg-border" />
                    {/* Children row with connecting bar */}
                    <div className="flex items-start">
                        {reports.map((child, i) => {
                            const isFirst = i === 0;
                            const isLast  = i === reports.length - 1;
                            const isOnly  = reports.length === 1;
                            return (
                                <div key={child.employee_id} className="flex flex-col items-center relative px-5">
                                    {/* Horizontal bar segments form a continuous bar across siblings */}
                                    {!isOnly && (
                                        <div className={cn(
                                            'absolute top-0 h-0.5 bg-border',
                                            isFirst ? 'left-1/2 right-0' :
                                            isLast  ? 'left-0 right-1/2' :
                                                      'left-0 right-0'
                                        )} />
                                    )}
                                    {/* Vertical stem down from bar to child */}
                                    <div className="w-0.5 h-8 bg-border" />
                                    <OrgTreeNode node={child} />
                                </div>
                            );
                        })}
                    </div>
                </>
            )}
        </div>
    );
}
