import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { toast } from 'sonner';
import {
    Building2, Users, PoundSterling, AlertTriangle, Shield, ShieldOff,
    Search, Loader2, Activity, Sparkles, Eye, PowerOff,
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function SuperAdminPage() {
    const { user } = useAuth();
    const [metrics, setMetrics] = useState(null);
    const [companies, setCompanies] = useState([]);
    const [auditLog, setAuditLog] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [error, setError] = useState(null);
    const token = () => localStorage.getItem('token');

    const load = async () => {
        setLoading(true);
        try {
            const headers = { Authorization: `Bearer ${token()}` };
            const [mRes, cRes, aRes] = await Promise.all([
                axios.get(`${API_URL}/api/super-admin/metrics`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/super-admin/companies`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/super-admin/audit-log?limit=50`, { headers, withCredentials: true }),
            ]);
            setMetrics(mRes.data);
            setCompanies(cRes.data.companies || []);
            setAuditLog(aRes.data.audit_log || []);
            setError(null);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to load platform data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    const suspend = async (company_id) => {
        const reason = window.prompt('Reason for suspension:');
        if (!reason) return;
        try {
            await axios.post(`${API_URL}/api/super-admin/companies/${company_id}/suspend`,
                { reason },
                { headers: { Authorization: `Bearer ${token()}` }, withCredentials: true });
            toast.success('Company suspended');
            load();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Suspension failed');
        }
    };

    const restore = async (company_id) => {
        try {
            await axios.post(`${API_URL}/api/super-admin/companies/${company_id}/restore`, {},
                { headers: { Authorization: `Bearer ${token()}` }, withCredentials: true });
            toast.success('Company restored');
            load();
        } catch (err) {
            toast.error('Restore failed');
        }
    };

    const killSwitch = async () => {
        const enabled = window.confirm('Activate GLOBAL kill switch? This disables all paid features for ALL companies.');
        if (!enabled) return;
        const reason = window.prompt('Reason:');
        if (!reason) return;
        try {
            await axios.post(`${API_URL}/api/super-admin/emergency/kill-switch`,
                { enabled: true, reason },
                { headers: { Authorization: `Bearer ${token()}` }, withCredentials: true });
            toast.success('Kill switch activated');
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed');
        }
    };

    const impersonate = async (companyId) => {
        // Fetch users for this company
        const detailRes = await axios.get(`${API_URL}/api/super-admin/companies/${companyId}`,
            { headers: { Authorization: `Bearer ${token()}` }, withCredentials: true });
        const target = (detailRes.data?.users || []).find(u => u.role === 'owner');
        if (!target) return toast.error('No owner found');
        const reason = window.prompt(`Impersonate ${target.email} as ${target.name}?\nReason (required):`);
        if (!reason) return;
        try {
            const res = await axios.post(`${API_URL}/api/super-admin/impersonate`,
                { user_id: target.user_id, reason },
                { headers: { Authorization: `Bearer ${token()}` }, withCredentials: true });
            const platformToken = token();
            sessionStorage.setItem('original_admin_token', platformToken);
            localStorage.setItem('token', res.data.token);
            toast.success(`Impersonating ${target.name} for 30 min`);
            setTimeout(() => { window.location.href = '/dashboard'; }, 800);
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed');
        }
    };

    if (error) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Card className="max-w-md">
                    <CardContent className="p-8 text-center">
                        <Shield className="w-12 h-12 text-rose-500 mx-auto mb-3" />
                        <h3 className="text-xl font-bold">Platform admin access required</h3>
                        <p className="text-muted-foreground mt-2 text-sm">{error}</p>
                        <p className="text-xs text-muted-foreground mt-4">
                            Your email must be in the <code className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">PLATFORM_ADMINS</code> env list or have <code>is_platform_admin=true</code> on the user record.
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (loading) {
        return <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-indigo-600" /></div>;
    }

    const filtered = companies.filter(c => !search || c.name?.toLowerCase().includes(search.toLowerCase()));

    return (
        <div className="space-y-6" data-testid="super-admin-page">
            <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                    <div className="flex items-center gap-2">
                        <Shield className="w-6 h-6 text-rose-600" />
                        <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Super Admin</h1>
                    </div>
                    <p className="text-muted-foreground mt-1">Platform owner control plane — multi-tenant overview.</p>
                </div>
                <Button variant="outline" className="border-rose-300 text-rose-700 hover:bg-rose-50"
                    onClick={killSwitch} data-testid="kill-switch-btn">
                    <PowerOff className="w-4 h-4 mr-2" /> Emergency kill switch
                </Button>
            </div>

            {/* Metrics grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {[
                    { label: 'Total companies', value: metrics?.total_companies, icon: Building2, color: 'text-indigo-600' },
                    { label: 'On trial', value: metrics?.trial_companies, icon: Sparkles, color: 'text-amber-600' },
                    { label: 'Sandbox', value: metrics?.sandbox_companies, icon: Eye, color: 'text-slate-600' },
                    { label: 'Suspended', value: metrics?.suspended_companies, icon: ShieldOff, color: 'text-rose-600' },
                    { label: 'MRR (GBP)', value: '£' + (metrics?.mrr_gbp || 0), icon: PoundSterling, color: 'text-emerald-600' },
                    { label: 'Total users', value: metrics?.total_users, icon: Users, color: 'text-blue-600' },
                    { label: 'Total employees', value: metrics?.total_employees, icon: Users, color: 'text-blue-500' },
                    { label: 'Paid subs', value: metrics?.paid_subscriptions, icon: PoundSterling, color: 'text-emerald-500' },
                ].map((m, i) => {
                    const Icon = m.icon;
                    return (
                        <Card key={i} data-testid={`metric-card-${i}`}>
                            <CardContent className="p-4">
                                <div className="flex items-center gap-2 mb-1">
                                    <Icon className={`w-3.5 h-3.5 ${m.color}`} />
                                    <p className="text-xs text-muted-foreground">{m.label}</p>
                                </div>
                                <p className="text-2xl font-bold">{m.value ?? '—'}</p>
                            </CardContent>
                        </Card>
                    );
                })}
            </div>

            <Tabs defaultValue="companies">
                <TabsList>
                    <TabsTrigger value="companies" data-testid="tab-companies">Companies ({companies.length})</TabsTrigger>
                    <TabsTrigger value="audit" data-testid="tab-audit-log">Audit Log</TabsTrigger>
                </TabsList>

                <TabsContent value="companies">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between flex-wrap gap-3">
                                <CardTitle>All companies</CardTitle>
                                <div className="relative w-64">
                                    <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                                    <Input className="pl-9 h-9" placeholder="Search…" value={search}
                                        onChange={(e) => setSearch(e.target.value)} data-testid="search-input" />
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b text-xs uppercase tracking-wider text-muted-foreground">
                                            <th className="text-left p-2">Company</th>
                                            <th className="text-left p-2">Status</th>
                                            <th className="text-right p-2">Users</th>
                                            <th className="text-right p-2">Employees</th>
                                            <th className="text-left p-2">Created</th>
                                            <th className="text-right p-2">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {filtered.map((c) => (
                                            <tr key={c.company_id} className="border-b hover:bg-accent/50" data-testid={`company-row-${c.company_id}`}>
                                                <td className="p-2">
                                                    <div className="font-medium">{c.name}</div>
                                                    <div className="text-xs text-muted-foreground">{c.company_id}</div>
                                                </td>
                                                <td className="p-2">
                                                    {c.suspended ? <Badge className="bg-rose-100 text-rose-700">SUSPENDED</Badge>
                                                        : c.is_sandbox ? <Badge className="bg-slate-100 text-slate-700">SANDBOX</Badge>
                                                        : c.trial_active ? <Badge className="bg-amber-100 text-amber-700">TRIAL</Badge>
                                                        : <Badge className="bg-emerald-100 text-emerald-700">ACTIVE</Badge>}
                                                </td>
                                                <td className="p-2 text-right">{c.user_count}</td>
                                                <td className="p-2 text-right">{c.employee_count}</td>
                                                <td className="p-2 text-xs text-muted-foreground">
                                                    {c.created_at?.slice(0, 10)}
                                                </td>
                                                <td className="p-2 text-right space-x-2">
                                                    <Button size="sm" variant="outline" onClick={() => impersonate(c.company_id)}
                                                        data-testid={`impersonate-${c.company_id}`}>
                                                        <Eye className="w-3.5 h-3.5" />
                                                    </Button>
                                                    {c.suspended ? (
                                                        <Button size="sm" variant="outline" onClick={() => restore(c.company_id)}
                                                            data-testid={`restore-${c.company_id}`}>
                                                            <Shield className="w-3.5 h-3.5" />
                                                        </Button>
                                                    ) : (
                                                        <Button size="sm" variant="outline" className="text-rose-600"
                                                            onClick={() => suspend(c.company_id)}
                                                            data-testid={`suspend-${c.company_id}`}>
                                                            <ShieldOff className="w-3.5 h-3.5" />
                                                        </Button>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="audit">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Activity className="w-5 h-5 text-indigo-600" />
                                <CardTitle>Platform audit log (last 50)</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-1 max-h-[500px] overflow-y-auto">
                                {auditLog.map((a, i) => (
                                    <div key={a.audit_id || i} className="text-sm p-2 border-b last:border-0" data-testid={`audit-${i}`}>
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <p className="font-medium">{a.action?.replace(/_/g, ' ')}</p>
                                                <p className="text-xs text-muted-foreground">
                                                    {a.user_name || 'System'} → {a.entity_type} ({(a.entity_id || '').substring(0, 16)}…)
                                                </p>
                                            </div>
                                            <span className="text-xs text-muted-foreground">{new Date(a.timestamp).toLocaleString()}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
