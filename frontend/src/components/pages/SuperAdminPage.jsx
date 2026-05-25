import React, { useEffect, useState, useCallback } from 'react';
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
    Search, Loader2, Activity, Sparkles, Eye, PowerOff, Package,
    ToggleLeft, CreditCard, Save, X, ChevronRight, CalendarPlus,
    UserX, UserCheck, Trash2, Flag, RefreshCw, Mail, Clock,
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../ui/sheet';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const hdrs = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });
const ax = (method, url, data) =>
    axios({ method, url: `${API_URL}${url}`, data, headers: hdrs(), withCredentials: true });

function StatusBadge({ c }) {
    if (c.suspended)    return <Badge className="bg-rose-100 text-rose-700">Suspended</Badge>;
    if (c.is_sandbox)   return <Badge className="bg-slate-100 text-slate-700">Sandbox</Badge>;
    if (c.trial_active) return <Badge className="bg-amber-100 text-amber-700">Trial</Badge>;
    return <Badge className="bg-emerald-100 text-emerald-700">Active</Badge>;
}

export default function SuperAdminPage() {
    const { user } = useAuth();
    const [metrics, setMetrics]       = useState(null);
    const [companies, setCompanies]   = useState([]);
    const [auditLog, setAuditLog]     = useState([]);
    const [plans, setPlans]           = useState([]);
    const [allUsers, setAllUsers]     = useState([]);
    const [flags, setFlags]           = useState([]);
    const [loading, setLoading]       = useState(true);
    const [search, setSearch]         = useState('');
    const [userSearch, setUserSearch] = useState('');
    const [error, setError]           = useState(null);

    // Dialogs
    const [moduleDialog, setModuleDialog]   = useState(null);
    const [planDialog, setPlanDialog]       = useState(null);
    const [planForm, setPlanForm]           = useState({ plan_id: '', name: '', price: 0, employee_limit: 10, features: '' });
    const [detailSheet, setDetailSheet]     = useState(null);   // {company, users, txs}
    const [trialDialog, setTrialDialog]     = useState(null);   // company_id
    const [trialDays, setTrialDays]         = useState(14);
    const [setPlanDialog2, setSetPlanDialog2] = useState(null); // company_id
    const [selectedPlan, setSelectedPlan]   = useState('');
    const [deleteDialog, setDeleteDialog]   = useState(null);   // company_id
    const [newFlagKey, setNewFlagKey]       = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        const safe = async (promise) => { try { return await promise; } catch (e) { return { error: e }; } };
        const [mRes, cRes, aRes, pRes, uRes, fRes] = await Promise.all([
            safe(ax('get', '/api/super-admin/metrics')),
            safe(ax('get', '/api/super-admin/companies')),
            safe(ax('get', '/api/super-admin/audit-log?limit=100')),
            safe(ax('get', '/api/super-admin/plans')),
            safe(ax('get', '/api/super-admin/users')),
            safe(ax('get', '/api/super-admin/feature-flags')),
        ]);

        // Surface the first 403 as the page-level error (access denied)
        const firstAuthErr = [mRes, cRes, aRes, pRes, uRes, fRes].find(
            r => r?.error?.response?.status === 403
        );
        if (firstAuthErr) {
            setError(firstAuthErr.error.response.data?.detail || 'Platform admin only');
            setLoading(false);
            return;
        }

        if (!mRes.error) setMetrics(mRes.data);
        if (!cRes.error) setCompanies(cRes.data.companies || []);
        if (!aRes.error) setAuditLog(aRes.data.audit_log || []);
        if (!pRes.error) setPlans(pRes.data.plans || []);
        if (!uRes.error) setAllUsers(uRes.data.users || []);
        if (!fRes.error) setFlags(fRes.data.flags || []);

        // Log non-auth errors to console but don't block the page
        [mRes, cRes, aRes, pRes, uRes, fRes].forEach((r, i) => {
            if (r?.error) console.warn(`Super-admin load[${i}] failed:`, r.error?.response?.data || r.error?.message);
        });

        setError(null);
        setLoading(false);
    }, []);

    useEffect(() => { load(); }, [load]);

    // ── Company detail sheet ──────────────────────────────────────
    const openDetail = async (company_id) => {
        try {
            const res = await ax('get', `/api/super-admin/companies/${company_id}`);
            setDetailSheet(res.data);
        } catch { toast.error('Failed to load company detail'); }
    };

    // ── Module toggle ────────────────────────────────────────────
    const openModules = async (company_id, name) => {
        try {
            const res = await ax('get', `/api/super-admin/companies/${company_id}/modules`);
            setModuleDialog({ company_id, name, modules: res.data.modules });
        } catch { toast.error('Failed to load modules'); }
    };
    const toggleModule = async (module_key, enabled) => {
        try {
            await ax('post', `/api/super-admin/companies/${moduleDialog.company_id}/modules`, { module_key, enabled });
            setModuleDialog(d => ({ ...d, modules: d.modules.map(m => m.key === module_key ? { ...m, enabled } : m) }));
        } catch { toast.error('Failed'); }
    };

    // ── Plan editor ──────────────────────────────────────────────
    const openPlanEditor = (plan) => {
        setPlanForm({ plan_id: plan.plan_id, name: plan.name, price: plan.price, employee_limit: plan.employee_limit, features: (plan.features || []).join('\n') });
        setPlanDialog(plan);
    };
    const savePlan = async () => {
        try {
            const features = planForm.features.split('\n').map(s => s.trim()).filter(Boolean);
            await ax('put', `/api/super-admin/plans/${planForm.plan_id}`, { ...planForm, price: Number(planForm.price), employee_limit: Number(planForm.employee_limit), features, currency: 'gbp' });
            toast.success('Plan saved'); setPlanDialog(null); load();
        } catch { toast.error('Failed to save plan'); }
    };

    // ── Suspend / restore ────────────────────────────────────────
    const suspend = async (company_id) => {
        const reason = window.prompt('Reason for suspension:');
        if (!reason) return;
        try {
            await ax('post', `/api/super-admin/companies/${company_id}/suspend`, { reason });
            toast.success('Company suspended'); load();
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };
    const restore = async (company_id) => {
        try {
            await ax('post', `/api/super-admin/companies/${company_id}/restore`, {});
            toast.success('Company restored'); load();
        } catch { toast.error('Restore failed'); }
    };

    // ── Trial extension ──────────────────────────────────────────
    const extendTrial = async () => {
        try {
            await ax('post', `/api/super-admin/companies/${trialDialog}/extend-trial`, { days: trialDays });
            toast.success(`Trial extended by ${trialDays} days`);
            setTrialDialog(null); load();
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };

    // ── Set plan ──────────────────────────────────────────────────
    const assignPlan = async () => {
        if (!selectedPlan) return;
        try {
            await ax('post', `/api/super-admin/companies/${setPlanDialog2}/set-plan`, { plan_id: selectedPlan });
            toast.success('Plan updated'); setSetPlanDialog2(null); load();
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };

    // ── Delete company ────────────────────────────────────────────
    const deleteCompany = async (company_id) => {
        try {
            await ax('post', `/api/super-admin/companies/${company_id}/delete`, { confirm: company_id });
            toast.success('Company deleted'); setDeleteDialog(null); load();
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };

    // ── User disable / enable ─────────────────────────────────────
    const toggleUser = async (user_id, disabled) => {
        try {
            await ax('post', `/api/super-admin/users/${user_id}/${disabled ? 'disable' : 'enable'}`, {});
            toast.success(disabled ? 'User disabled' : 'User re-enabled');
            setAllUsers(u => u.map(x => x.user_id === user_id ? { ...x, disabled } : x));
        } catch { toast.error('Failed'); }
    };

    // ── Feature flags ─────────────────────────────────────────────
    const toggleFlag = async (key, enabled) => {
        try {
            await ax('put', `/api/super-admin/feature-flags/${key}`, { enabled });
            setFlags(f => f.map(x => x.key === key ? { ...x, enabled } : x));
            toast.success(`Flag ${key} ${enabled ? 'enabled' : 'disabled'}`);
        } catch { toast.error('Failed'); }
    };
    const createFlag = async () => {
        if (!newFlagKey.trim()) return;
        try {
            await ax('put', `/api/super-admin/feature-flags/${newFlagKey.trim()}`, { enabled: false, description: '' });
            setNewFlagKey(''); load();
        } catch { toast.error('Failed'); }
    };

    // ── Kill switch ───────────────────────────────────────────────
    const killSwitch = async () => {
        if (!window.confirm('Activate GLOBAL kill switch? This disables all paid features for ALL companies.')) return;
        const reason = window.prompt('Reason:');
        if (!reason) return;
        try {
            await ax('post', '/api/super-admin/emergency/kill-switch', { enabled: true, reason });
            toast.success('Kill switch activated');
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };

    // ── Impersonate ───────────────────────────────────────────────
    const impersonate = async (companyId) => {
        try {
            const detailRes = await ax('get', `/api/super-admin/companies/${companyId}`);
            const target = (detailRes.data?.users || []).find(u => u.role === 'owner');
            if (!target) return toast.error('No owner found');
            const reason = window.prompt(`Impersonate ${target.email}?\nReason (required):`);
            if (!reason) return;
            const res = await ax('post', '/api/super-admin/impersonate', { user_id: target.user_id, reason });
            sessionStorage.setItem('original_admin_token', localStorage.getItem('token'));
            localStorage.setItem('token', res.data.token);
            toast.success(`Impersonating ${target.name} for 30 min`);
            setTimeout(() => { window.location.href = '/dashboard'; }, 800);
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };

    // ─────────────────────────────────────────────────────────────
    if (error) return (
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

    if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-indigo-600" /></div>;

    const filteredCompanies = companies.filter(c => !search || c.name?.toLowerCase().includes(search.toLowerCase()));
    const filteredUsers = allUsers.filter(u => !userSearch ||
        u.email?.toLowerCase().includes(userSearch.toLowerCase()) ||
        u.name?.toLowerCase().includes(userSearch.toLowerCase())
    );

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                    <div className="flex items-center gap-2">
                        <Shield className="w-6 h-6 text-rose-600" />
                        <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Super Admin</h1>
                    </div>
                    <p className="text-muted-foreground mt-1">Platform owner control plane — multi-tenant overview.</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={load}>
                        <RefreshCw className="w-4 h-4 mr-1" /> Refresh
                    </Button>
                    <Button variant="outline" className="border-rose-300 text-rose-700 hover:bg-rose-50" onClick={killSwitch}>
                        <PowerOff className="w-4 h-4 mr-2" /> Emergency kill switch
                    </Button>
                </div>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {[
                    { label: 'Total companies',  value: metrics?.total_companies,    icon: Building2,     color: 'text-indigo-600' },
                    { label: 'On trial',         value: metrics?.trial_companies,    icon: Sparkles,      color: 'text-amber-600' },
                    { label: 'Sandbox',          value: metrics?.sandbox_companies,  icon: Eye,           color: 'text-slate-600' },
                    { label: 'Suspended',        value: metrics?.suspended_companies,icon: ShieldOff,     color: 'text-rose-600' },
                    { label: 'MRR (GBP)',        value: '£' + (metrics?.mrr_gbp || 0), icon: PoundSterling, color: 'text-emerald-600' },
                    { label: 'Total users',      value: metrics?.total_users,        icon: Users,         color: 'text-blue-600' },
                    { label: 'Total employees',  value: metrics?.total_employees,    icon: Users,         color: 'text-blue-500' },
                    { label: 'Paid subs',        value: metrics?.paid_subscriptions, icon: PoundSterling, color: 'text-emerald-500' },
                ].map((m, i) => {
                    const Icon = m.icon;
                    return (
                        <Card key={i}><CardContent className="p-4">
                            <div className="flex items-center gap-2 mb-1">
                                <Icon className={`w-3.5 h-3.5 ${m.color}`} />
                                <p className="text-xs text-muted-foreground">{m.label}</p>
                            </div>
                            <p className="text-2xl font-bold">{m.value ?? '—'}</p>
                        </CardContent></Card>
                    );
                })}
            </div>

            <Tabs defaultValue="companies">
                <TabsList className="flex-wrap h-auto gap-1">
                    <TabsTrigger value="companies"><Building2 className="w-4 h-4 mr-1" />Companies ({companies.length})</TabsTrigger>
                    <TabsTrigger value="users"><Users className="w-4 h-4 mr-1" />Users ({allUsers.length})</TabsTrigger>
                    <TabsTrigger value="plans"><CreditCard className="w-4 h-4 mr-1" />Plans</TabsTrigger>
                    <TabsTrigger value="flags"><Flag className="w-4 h-4 mr-1" />Feature Flags</TabsTrigger>
                    <TabsTrigger value="audit"><Activity className="w-4 h-4 mr-1" />Audit Log</TabsTrigger>
                </TabsList>

                {/* ── Companies ── */}
                <TabsContent value="companies">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between flex-wrap gap-3">
                                <CardTitle>All companies</CardTitle>
                                <div className="relative w-64">
                                    <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                                    <Input className="pl-9 h-9" placeholder="Search…" value={search} onChange={e => setSearch(e.target.value)} />
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
                                            <th className="text-left p-2">Plan</th>
                                            <th className="text-right p-2">Users</th>
                                            <th className="text-right p-2">Employees</th>
                                            <th className="text-left p-2">Created</th>
                                            <th className="text-right p-2">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {filteredCompanies.map(c => (
                                            <tr key={c.company_id} className="border-b hover:bg-accent/50">
                                                <td className="p-2">
                                                    <div className="font-medium">{c.name}</div>
                                                    <div className="text-xs text-muted-foreground">{c.company_id}</div>
                                                    {c.suspended_reason && <div className="text-xs text-rose-600 mt-0.5">{c.suspended_reason}</div>}
                                                </td>
                                                <td className="p-2"><StatusBadge c={c} /></td>
                                                <td className="p-2 text-xs text-muted-foreground">{c.plan_id || '—'}</td>
                                                <td className="p-2 text-right">{c.user_count}</td>
                                                <td className="p-2 text-right">{c.employee_count}</td>
                                                <td className="p-2 text-xs text-muted-foreground">{c.created_at?.slice(0, 10)}</td>
                                                <td className="p-2 text-right">
                                                    <div className="flex items-center justify-end gap-1">
                                                        <Button size="icon" variant="ghost" className="h-7 w-7" title="View detail" onClick={() => openDetail(c.company_id)}>
                                                            <ChevronRight className="w-3.5 h-3.5" />
                                                        </Button>
                                                        <Button size="icon" variant="ghost" className="h-7 w-7" title="Impersonate owner" onClick={() => impersonate(c.company_id)}>
                                                            <Eye className="w-3.5 h-3.5" />
                                                        </Button>
                                                        <Button size="icon" variant="ghost" className="h-7 w-7" title="Toggle modules" onClick={() => openModules(c.company_id, c.name)}>
                                                            <Package className="w-3.5 h-3.5" />
                                                        </Button>
                                                        <Button size="icon" variant="ghost" className="h-7 w-7" title="Extend trial" onClick={() => { setTrialDialog(c.company_id); setTrialDays(14); }}>
                                                            <CalendarPlus className="w-3.5 h-3.5 text-amber-600" />
                                                        </Button>
                                                        <Button size="icon" variant="ghost" className="h-7 w-7" title="Set plan" onClick={() => { setSetPlanDialog2(c.company_id); setSelectedPlan(c.plan_id || ''); }}>
                                                            <CreditCard className="w-3.5 h-3.5 text-indigo-600" />
                                                        </Button>
                                                        {c.suspended ? (
                                                            <Button size="icon" variant="ghost" className="h-7 w-7" title="Restore" onClick={() => restore(c.company_id)}>
                                                                <Shield className="w-3.5 h-3.5 text-emerald-600" />
                                                            </Button>
                                                        ) : (
                                                            <Button size="icon" variant="ghost" className="h-7 w-7" title="Suspend" onClick={() => suspend(c.company_id)}>
                                                                <ShieldOff className="w-3.5 h-3.5 text-rose-600" />
                                                            </Button>
                                                        )}
                                                        <Button size="icon" variant="ghost" className="h-7 w-7" title="Delete company" onClick={() => setDeleteDialog(c.company_id)}>
                                                            <Trash2 className="w-3.5 h-3.5 text-rose-500" />
                                                        </Button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ── Users ── */}
                <TabsContent value="users">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between flex-wrap gap-3">
                                <CardTitle>All users</CardTitle>
                                <div className="relative w-64">
                                    <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                                    <Input className="pl-9 h-9" placeholder="Search by name or email…" value={userSearch} onChange={e => setUserSearch(e.target.value)} />
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b text-xs uppercase tracking-wider text-muted-foreground">
                                            <th className="text-left p-2">User</th>
                                            <th className="text-left p-2">Company</th>
                                            <th className="text-left p-2">Role</th>
                                            <th className="text-left p-2">2FA</th>
                                            <th className="text-left p-2">Status</th>
                                            <th className="text-left p-2">Joined</th>
                                            <th className="text-right p-2">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {filteredUsers.map(u => {
                                            const co = companies.find(c => c.company_id === u.company_id);
                                            return (
                                                <tr key={u.user_id} className="border-b hover:bg-accent/50">
                                                    <td className="p-2">
                                                        <div className="font-medium">{u.name}</div>
                                                        <div className="text-xs text-muted-foreground">{u.email}</div>
                                                    </td>
                                                    <td className="p-2 text-xs text-muted-foreground">{co?.name || u.company_id || '—'}</td>
                                                    <td className="p-2">
                                                        <Badge variant="outline" className="text-xs capitalize">{u.role}</Badge>
                                                    </td>
                                                    <td className="p-2">
                                                        {u.totp_enabled
                                                            ? <Badge className="bg-emerald-100 text-emerald-700 text-xs">On</Badge>
                                                            : <Badge variant="outline" className="text-xs text-muted-foreground">Off</Badge>}
                                                    </td>
                                                    <td className="p-2">
                                                        {u.disabled
                                                            ? <Badge className="bg-rose-100 text-rose-700 text-xs">Disabled</Badge>
                                                            : <Badge className="bg-emerald-100 text-emerald-700 text-xs">Active</Badge>}
                                                    </td>
                                                    <td className="p-2 text-xs text-muted-foreground">{u.created_at?.slice(0, 10)}</td>
                                                    <td className="p-2 text-right">
                                                        {u.disabled ? (
                                                            <Button size="sm" variant="outline" onClick={() => toggleUser(u.user_id, false)}>
                                                                <UserCheck className="w-3.5 h-3.5 mr-1 text-emerald-600" /> Enable
                                                            </Button>
                                                        ) : (
                                                            <Button size="sm" variant="outline" onClick={() => toggleUser(u.user_id, true)}>
                                                                <UserX className="w-3.5 h-3.5 mr-1 text-rose-600" /> Disable
                                                            </Button>
                                                        )}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ── Plans ── */}
                <TabsContent value="plans">
                    <Card>
                        <CardHeader><CardTitle>Subscription Plans</CardTitle></CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {plans.map(p => (
                                    <Card key={p.plan_id} className="border-2">
                                        <CardHeader>
                                            <div className="flex items-center justify-between">
                                                <CardTitle className="text-lg">{p.name}</CardTitle>
                                                {p.overridden && <Badge variant="secondary">Overridden</Badge>}
                                            </div>
                                        </CardHeader>
                                        <CardContent>
                                            <p className="text-3xl font-bold mb-2">£{p.price}<span className="text-sm font-normal text-muted-foreground">/mo</span></p>
                                            <p className="text-xs text-muted-foreground mb-3">Employee limit: {p.employee_limit === -1 ? 'Unlimited' : p.employee_limit}</p>
                                            <ul className="text-xs space-y-1 text-muted-foreground mb-4">
                                                {(p.features || []).slice(0, 5).map((f, i) => <li key={i}>· {f}</li>)}
                                            </ul>
                                            <Button size="sm" variant="outline" onClick={() => openPlanEditor(p)}>Edit price / features</Button>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ── Feature Flags ── */}
                <TabsContent value="flags">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between flex-wrap gap-3">
                                <div>
                                    <CardTitle>Global Feature Flags</CardTitle>
                                    <p className="text-xs text-muted-foreground mt-1">Flags apply platform-wide. Per-company overrides can be set from the company detail drawer.</p>
                                </div>
                                <div className="flex gap-2">
                                    <Input placeholder="new.flag.key" className="h-9 w-48" value={newFlagKey} onChange={e => setNewFlagKey(e.target.value)} />
                                    <Button size="sm" onClick={createFlag}>Add flag</Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            {flags.length === 0 ? (
                                <p className="text-sm text-muted-foreground text-center py-8">No feature flags configured yet.</p>
                            ) : (
                                <div className="space-y-2">
                                    {flags.map(f => (
                                        <div key={f.key} className="flex items-center justify-between p-3 border rounded-lg">
                                            <div>
                                                <p className="font-mono text-sm font-medium">{f.key}</p>
                                                {f.description && <p className="text-xs text-muted-foreground">{f.description}</p>}
                                                {f.updated_at && <p className="text-xs text-muted-foreground">Updated {f.updated_at?.slice(0, 16)}</p>}
                                            </div>
                                            <Switch checked={!!f.enabled} onCheckedChange={v => toggleFlag(f.key, v)} />
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ── Audit Log ── */}
                <TabsContent value="audit">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Activity className="w-5 h-5 text-indigo-600" />
                                <CardTitle>Platform audit log (last 100)</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-1 max-h-[600px] overflow-y-auto">
                                {auditLog.map((a, i) => (
                                    <div key={a.audit_id || i} className="text-sm p-2 border-b last:border-0">
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <p className="font-medium">{a.action?.replace(/_/g, ' ')}</p>
                                                <p className="text-xs text-muted-foreground">
                                                    {a.user_name || 'System'} → {a.entity_type} {a.entity_id && `(${a.entity_id.substring(0, 20)})`}
                                                </p>
                                                {a.details && Object.keys(a.details).length > 0 && (
                                                    <p className="text-xs text-muted-foreground font-mono">{JSON.stringify(a.details)}</p>
                                                )}
                                            </div>
                                            <span className="text-xs text-muted-foreground whitespace-nowrap ml-4">{new Date(a.timestamp).toLocaleString()}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* ── Company detail sheet ── */}
            <Sheet open={!!detailSheet} onOpenChange={o => !o && setDetailSheet(null)}>
                <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
                    <SheetHeader>
                        <SheetTitle className="flex items-center gap-2">
                            <Building2 className="w-5 h-5" />
                            {detailSheet?.company?.name}
                        </SheetTitle>
                    </SheetHeader>
                    {detailSheet && (
                        <div className="space-y-6 mt-6">
                            {/* Company info */}
                            <div className="grid grid-cols-2 gap-3 text-sm">
                                {[
                                    ['ID', detailSheet.company.company_id],
                                    ['Plan', detailSheet.company.plan_id || '—'],
                                    ['Status', detailSheet.company.suspended ? 'Suspended' : detailSheet.company.trial_active ? 'Trial' : 'Active'],
                                    ['Trial ends', detailSheet.company.trial_ends_at?.slice(0, 10) || '—'],
                                    ['Employees', detailSheet.employees_count],
                                    ['Industry', detailSheet.company.industry || '—'],
                                    ['Created', detailSheet.company.created_at?.slice(0, 10)],
                                    ['2FA policy', detailSheet.company.security_policy?.force_2fa_for_all ? 'Enforced' : 'Optional'],
                                ].map(([k, v]) => (
                                    <div key={k} className="bg-muted/40 rounded p-2">
                                        <p className="text-xs text-muted-foreground">{k}</p>
                                        <p className="font-medium">{v ?? '—'}</p>
                                    </div>
                                ))}
                            </div>

                            {/* Quick actions */}
                            <div className="flex flex-wrap gap-2">
                                <Button size="sm" variant="outline" onClick={() => { setDetailSheet(null); setTimeout(() => impersonate(detailSheet.company.company_id), 100); }}>
                                    <Eye className="w-3.5 h-3.5 mr-1" /> Impersonate owner
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => { setDetailSheet(null); setTrialDialog(detailSheet.company.company_id); setTrialDays(14); }}>
                                    <CalendarPlus className="w-3.5 h-3.5 mr-1" /> Extend trial
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => { setDetailSheet(null); setSetPlanDialog2(detailSheet.company.company_id); setSelectedPlan(detailSheet.company.plan_id || ''); }}>
                                    <CreditCard className="w-3.5 h-3.5 mr-1" /> Set plan
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => { setDetailSheet(null); openModules(detailSheet.company.company_id, detailSheet.company.name); }}>
                                    <Package className="w-3.5 h-3.5 mr-1" /> Modules
                                </Button>
                                {detailSheet.company.suspended ? (
                                    <Button size="sm" variant="outline" onClick={() => { restore(detailSheet.company.company_id); setDetailSheet(null); }}>
                                        <Shield className="w-3.5 h-3.5 mr-1 text-emerald-600" /> Restore
                                    </Button>
                                ) : (
                                    <Button size="sm" variant="outline" onClick={() => { setDetailSheet(null); suspend(detailSheet.company.company_id); }}>
                                        <ShieldOff className="w-3.5 h-3.5 mr-1 text-rose-600" /> Suspend
                                    </Button>
                                )}
                            </div>

                            {/* Users */}
                            <div>
                                <h3 className="font-semibold mb-2">Users ({detailSheet.users?.length})</h3>
                                <div className="space-y-1">
                                    {detailSheet.users?.map(u => (
                                        <div key={u.user_id} className="flex items-center justify-between text-sm p-2 border rounded">
                                            <div>
                                                <span className="font-medium">{u.name}</span>
                                                <span className="text-muted-foreground ml-2">{u.email}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Badge variant="outline" className="text-xs capitalize">{u.role}</Badge>
                                                {u.totp_enabled && <Badge className="bg-emerald-100 text-emerald-700 text-xs">2FA</Badge>}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Recent transactions */}
                            {detailSheet.recent_transactions?.length > 0 && (
                                <div>
                                    <h3 className="font-semibold mb-2">Recent transactions</h3>
                                    <div className="space-y-1">
                                        {detailSheet.recent_transactions.slice(0, 10).map((t, i) => (
                                            <div key={i} className="flex items-center justify-between text-sm p-2 border rounded">
                                                <div>
                                                    <span className="font-medium capitalize">{t.type}</span>
                                                    <span className="text-xs text-muted-foreground ml-2">{t.description}</span>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <span>£{t.amount}</span>
                                                    <Badge className={t.payment_status === 'paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'} >{t.payment_status}</Badge>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </SheetContent>
            </Sheet>

            {/* ── Module toggle dialog ── */}
            <Dialog open={!!moduleDialog} onOpenChange={o => !o && setModuleDialog(null)}>
                <DialogContent className="max-w-lg">
                    <DialogHeader><DialogTitle>Modules · {moduleDialog?.name}</DialogTitle></DialogHeader>
                    <p className="text-xs text-muted-foreground">Disabled modules are hidden from the tenant sidebar.</p>
                    <div className="space-y-2 max-h-[400px] overflow-y-auto">
                        {(moduleDialog?.modules || []).map(m => (
                            <div key={m.key} className="flex items-center justify-between p-2 border rounded">
                                <Label htmlFor={`mod-${m.key}`} className="text-sm cursor-pointer flex-1">{m.name}</Label>
                                <Switch id={`mod-${m.key}`} checked={m.enabled} onCheckedChange={c => toggleModule(m.key, c)} />
                            </div>
                        ))}
                    </div>
                </DialogContent>
            </Dialog>

            {/* ── Plan editor dialog ── */}
            <Dialog open={!!planDialog} onOpenChange={o => !o && setPlanDialog(null)}>
                <DialogContent>
                    <DialogHeader><DialogTitle>Edit plan · {planForm.name}</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div><Label>Display name</Label><Input value={planForm.name} onChange={e => setPlanForm({ ...planForm, name: e.target.value })} /></div>
                        <div className="grid grid-cols-2 gap-2">
                            <div><Label>Price (£/month)</Label><Input type="number" step="0.01" value={planForm.price} onChange={e => setPlanForm({ ...planForm, price: e.target.value })} /></div>
                            <div><Label>Employee limit (-1 = unlimited)</Label><Input type="number" value={planForm.employee_limit} onChange={e => setPlanForm({ ...planForm, employee_limit: e.target.value })} /></div>
                        </div>
                        <div><Label>Features (one per line)</Label>
                            <textarea className="w-full p-2 border rounded text-sm bg-background" rows={6} value={planForm.features} onChange={e => setPlanForm({ ...planForm, features: e.target.value })} />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setPlanDialog(null)}><X className="w-4 h-4 mr-1" />Cancel</Button>
                        <Button onClick={savePlan}><Save className="w-4 h-4 mr-1" />Save</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ── Extend trial dialog ── */}
            <Dialog open={!!trialDialog} onOpenChange={o => !o && setTrialDialog(null)}>
                <DialogContent className="max-w-sm">
                    <DialogHeader><DialogTitle className="flex items-center gap-2"><CalendarPlus className="w-5 h-5 text-amber-600" />Extend trial</DialogTitle></DialogHeader>
                    <p className="text-sm text-muted-foreground">Days will be added to the current trial end date.</p>
                    <div className="flex items-center gap-3 mt-2">
                        <Label>Days to add</Label>
                        <Input type="number" min={1} max={365} value={trialDays} onChange={e => setTrialDays(Number(e.target.value))} className="w-24" />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setTrialDialog(null)}>Cancel</Button>
                        <Button onClick={extendTrial} className="bg-amber-600 hover:bg-amber-700">Extend +{trialDays} days</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ── Set plan dialog ── */}
            <Dialog open={!!setPlanDialog2} onOpenChange={o => !o && setSetPlanDialog2(null)}>
                <DialogContent className="max-w-sm">
                    <DialogHeader><DialogTitle className="flex items-center gap-2"><CreditCard className="w-5 h-5 text-indigo-600" />Assign plan</DialogTitle></DialogHeader>
                    <Select value={selectedPlan} onValueChange={setSelectedPlan}>
                        <SelectTrigger><SelectValue placeholder="Choose a plan…" /></SelectTrigger>
                        <SelectContent>
                            {plans.map(p => <SelectItem key={p.plan_id} value={p.plan_id}>{p.name} — £{p.price}/mo</SelectItem>)}
                        </SelectContent>
                    </Select>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setSetPlanDialog2(null)}>Cancel</Button>
                        <Button onClick={assignPlan} disabled={!selectedPlan}>Assign plan</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ── Delete dialog ── */}
            <Dialog open={!!deleteDialog} onOpenChange={o => !o && setDeleteDialog(null)}>
                <DialogContent className="max-w-sm">
                    <DialogHeader><DialogTitle className="flex items-center gap-2 text-rose-600"><AlertTriangle className="w-5 h-5" />Delete company</DialogTitle></DialogHeader>
                    <p className="text-sm">This permanently deletes the company and <strong>all associated data</strong> (employees, payroll, documents, users). This cannot be undone.</p>
                    <p className="text-xs text-muted-foreground mt-2 font-mono break-all">{deleteDialog}</p>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteDialog(null)}>Cancel</Button>
                        <Button variant="destructive" onClick={() => deleteCompany(deleteDialog)}>Delete permanently</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
