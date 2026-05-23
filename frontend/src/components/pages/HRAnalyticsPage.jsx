import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { toast } from 'sonner';
import { CalendarClock, BarChart3, Network, Loader2, Download, AlertTriangle, TrendingUp, Users } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }, withCredentials: true });

export default function HRAnalyticsPage() {
    const [tab, setTab] = useState('calendar');
    const [calendar, setCalendar] = useState(null);
    const [summary, setSummary] = useState(null);
    const [tree, setTree] = useState(null);
    const [loading, setLoading] = useState(true);

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
                        <CardHeader><CardTitle>Organisation Chart</CardTitle></CardHeader>
                        <CardContent>
                            {tree && tree.tree && tree.tree.length > 0 ? (
                                <div className="space-y-4" data-testid="org-tree">
                                    <p className="text-xs text-muted-foreground">
                                        {tree.stats.total_employees} employees · {tree.stats.total_managers} managers · {tree.stats.max_depth} levels
                                    </p>
                                    {tree.tree.map((n) => <OrgNode key={n.employee_id} node={n} depth={0} />)}
                                </div>
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
                <div className="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center text-xs font-semibold text-indigo-700 dark:text-indigo-200">
                    {(node.name || '').split(' ').map((s) => s[0]).slice(0, 2).join('')}
                </div>
                <div>
                    <p className="text-sm font-medium">{node.name || 'Unnamed'}</p>
                    <p className="text-xs text-muted-foreground">{node.title || '—'} {node.department ? `· ${node.department}` : ''}</p>
                </div>
            </div>
            {(node.reports || []).map((c) => <OrgNode key={c.employee_id} node={c} depth={depth + 1} />)}
        </div>
    );
}
