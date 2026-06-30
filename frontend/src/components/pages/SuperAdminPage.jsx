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
    UserCog, Zap, PlusCircle, Lock, HeartPulse, CheckCircle2,
    AlertCircle, XCircle, Server, LogOut, Send, RotateCcw,
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../ui/sheet';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { Textarea } from '../ui/textarea';

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
    const [metrics, setMetrics]           = useState(null);
    const [companies, setCompanies]       = useState([]);
    const [auditLog, setAuditLog]         = useState([]);
    const [platformAuditLog, setPlatformAuditLog] = useState([]);
    const [plans, setPlans]               = useState([]);
    const [allUsers, setAllUsers]         = useState([]);
    const [flags, setFlags]               = useState([]);
    const [operators, setOperators]       = useState([]);
    const [emergencyActions, setEmergencyActions] = useState([]);
    const [loading, setLoading]           = useState(true);
    const [search, setSearch]             = useState('');
    const [userSearch, setUserSearch]     = useState('');
    const [error, setError]               = useState(null);
    const [newOperatorForm, setNewOperatorForm] = useState({ email: '', name: '', role: 'platform_support' });
    const [securitySettings, setSecuritySettings] = useState(null);
    const [designatedAdmins, setDesignatedAdmins] = useState([]);
    const [securityForm, setSecurityForm]     = useState({});
    const [savingSecSettings, setSavingSecSettings] = useState(false);
    const [systemHealth, setSystemHealth]     = useState(null);
    const [healthLoading, setHealthLoading]   = useState(false);
    const [discountUsages, setDiscountUsages] = useState([]);
    const [discountSummary, setDiscountSummary] = useState([]);
    const [emailTpl, setEmailTpl] = useState({ subject: '', html_body: '', from_name: 'RealtouchHR', from_email: '', is_default: true });
    const [emailTplSaving, setEmailTplSaving] = useState(false);
    const [emailTplTesting, setEmailTplTesting] = useState(false);
    const [emailPreviewOpen, setEmailPreviewOpen] = useState(false);

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
    const [deleteUserDialog, setDeleteUserDialog] = useState(null); // user_id
    const [newFlagKey, setNewFlagKey]       = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        const safe = async (promise) => { try { return await promise; } catch (e) { return { error: e }; } };
        const [mRes, cRes, aRes, pRes, uRes, fRes, opRes, emgRes, paRes, secRes, hlthRes, discRes, tplRes] = await Promise.all([
            safe(ax('get', '/api/super-admin/metrics')),
            safe(ax('get', '/api/super-admin/companies')),
            safe(ax('get', '/api/super-admin/audit-log?limit=100')),
            safe(ax('get', '/api/super-admin/plans')),
            safe(ax('get', '/api/super-admin/users')),
            safe(ax('get', '/api/super-admin/feature-flags')),
            safe(ax('get', '/api/super-admin/operators')),
            safe(ax('get', '/api/super-admin/emergency-actions')),
            safe(ax('get', '/api/super-admin/audit-log?limit=50')),
            safe(ax('get', '/api/super-admin/security/settings')),
            safe(ax('get', '/api/super-admin/system/health')),
            safe(ax('get', '/api/super-admin/discount-codes')),
            safe(ax('get', '/api/super-admin/email-templates/welcome')),
        ]);

        const firstAuthErr = [mRes, cRes].find(r => r?.error?.response?.status === 403);
        if (firstAuthErr) {
            setError(firstAuthErr.error.response.data?.detail || 'Platform admin only');
            setLoading(false);
            return;
        }

        if (!mRes.error) setMetrics(mRes.data);
        if (!cRes.error) setCompanies(cRes.data.companies || []);
        if (!aRes.error) setAuditLog(aRes.data.audit_log || aRes.data.logs || []);
        if (!pRes.error) setPlans(pRes.data.plans || []);
        if (!uRes.error) setAllUsers(uRes.data.users || []);
        if (!fRes.error) setFlags(fRes.data.flags || []);
        if (!opRes.error) setOperators(opRes.data.operators || []);
        if (!emgRes.error) setEmergencyActions(emgRes.data.actions || []);
        if (!paRes.error) setPlatformAuditLog(paRes.data.logs || []);
        if (!secRes.error) {
            setSecuritySettings(secRes.data.settings || {});
            setSecurityForm(secRes.data.settings || {});
            setDesignatedAdmins(secRes.data.designated_admins || []);
        }
        if (!hlthRes.error) setSystemHealth(hlthRes.data);
        if (!discRes.error) {
            setDiscountUsages(discRes.data.usages || []);
            setDiscountSummary(discRes.data.summary || []);
        }
        if (!tplRes.error) setEmailTpl(tplRes.data);

        [mRes, cRes, aRes, pRes, uRes, fRes, opRes, emgRes].forEach((r, i) => {
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

    // ── User remove (temporary) / restore / delete (permanent) ────
    const removeUser = async (user_id) => {
        const reason = window.prompt('Reason for removing this account? (Temporary — the email becomes free for a fresh signup, and the account can be restored later.)');
        if (!reason) return;
        try {
            await ax('post', `/api/super-admin/users/${user_id}/remove`, { reason });
            toast.success('Account removed. Email is now free to re-register.'); load();
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };
    const restoreUser = async (user_id) => {
        try {
            await ax('post', `/api/super-admin/users/${user_id}/restore`, {});
            toast.success('Account restored'); load();
        } catch (err) { toast.error(err.response?.data?.detail || 'Restore failed'); }
    };
    const deleteUser = async (user_id) => {
        try {
            await ax('post', `/api/super-admin/users/${user_id}/delete`, { confirm: user_id });
            toast.success('Account permanently deleted'); setDeleteUserDialog(null); load();
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };

    // ── Feature flags ─────────────────────────────────────────────
    const toggleFlag = async (key, enabled) => {
        try {
            await ax('put', `/api/super-admin/feature-flags/${key}`, { global_enabled: enabled });
            setFlags(f => f.map(x => (x.flag_key || x.key) === key ? { ...x, global_enabled: enabled, enabled } : x));
            toast.success(`Flag '${key}' ${enabled ? 'enabled' : 'disabled'} globally`);
        } catch { toast.error('Failed'); }
    };
    const createFlag = async () => {
        if (!newFlagKey.trim()) return;
        try {
            await ax('put', `/api/super-admin/feature-flags/${newFlagKey.trim()}`, { global_enabled: false });
            setNewFlagKey(''); load();
        } catch { toast.error('Failed'); }
    };

    // ── Platform Operators ────────────────────────────────────────
    const addOperator = async () => {
        if (!newOperatorForm.email) return;
        try {
            await ax('post', '/api/super-admin/operators', newOperatorForm);
            toast.success('Operator added');
            setNewOperatorForm({ email: '', name: '', role: 'platform_support' });
            load();
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };
    const removeOperator = async (operatorId) => {
        if (!window.confirm('Deactivate this operator?')) return;
        try {
            await ax('delete', `/api/super-admin/operators/${operatorId}`, {});
            toast.success('Operator deactivated'); load();
        } catch { toast.error('Failed'); }
    };

    // ── Emergency Actions ─────────────────────────────────────────
    const freezeRTI = async (companyId) => {
        const reason = window.prompt('Reason for RTI freeze:');
        if (!reason) return;
        try {
            await ax('post', `/api/super-admin/emergency/rti-freeze/${companyId}`, { reason });
            toast.success('RTI frozen'); load();
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };
    const unfreezeRTI = async (companyId) => {
        try {
            await ax('post', `/api/super-admin/emergency/rti-unfreeze/${companyId}`, {});
            toast.success('RTI unfrozen'); load();
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

    // ── Security Settings ─────────────────────────────────────────
    const saveSecuritySettings = async () => {
        setSavingSecSettings(true);
        try {
            await ax('put', '/api/super-admin/security/settings', securityForm);
            toast.success('Security settings saved');
            setSecuritySettings({ ...securityForm });
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed to save settings'); }
        finally { setSavingSecSettings(false); }
    };
    const revokeAllSessions = async () => {
        const reason = window.prompt('Reason for revoking all sessions:');
        if (!reason) return;
        try {
            const res = await ax('post', '/api/super-admin/security/revoke-all-sessions', { reason });
            toast.success(res.data.message);
        } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    };

    // ── System Health Refresh ─────────────────────────────────────
    const refreshHealth = async () => {
        setHealthLoading(true);
        try {
            const res = await ax('get', '/api/super-admin/system/health');
            setSystemHealth(res.data);
        } catch { toast.error('Failed to refresh health'); }
        finally { setHealthLoading(false); }
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
                    <TabsTrigger value="companies"><Building2 className="w-3.5 h-3.5 mr-1" />Companies ({companies.length})</TabsTrigger>
                    <TabsTrigger value="users"><Users className="w-3.5 h-3.5 mr-1" />Users ({allUsers.length})</TabsTrigger>
                    <TabsTrigger value="operators"><UserCog className="w-3.5 h-3.5 mr-1" />Operators ({operators.length})</TabsTrigger>
                    <TabsTrigger value="flags"><Flag className="w-3.5 h-3.5 mr-1" />Feature Flags</TabsTrigger>
                    <TabsTrigger value="plans"><CreditCard className="w-3.5 h-3.5 mr-1" />Plans</TabsTrigger>
                    <TabsTrigger value="emergency"><Zap className="w-3.5 h-3.5 mr-1" />Emergency</TabsTrigger>
                    <TabsTrigger value="audit"><Activity className="w-3.5 h-3.5 mr-1" />Audit Log</TabsTrigger>
                    <TabsTrigger value="security"><Lock className="w-3.5 h-3.5 mr-1" />Security</TabsTrigger>
                    <TabsTrigger value="health"><HeartPulse className="w-3.5 h-3.5 mr-1" />System Health</TabsTrigger>
                    <TabsTrigger value="discounts"><PoundSterling className="w-3.5 h-3.5 mr-1" />Discount Codes</TabsTrigger>
                    <TabsTrigger value="email"><Mail className="w-3.5 h-3.5 mr-1" />Welcome Email</TabsTrigger>
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
                                                        {u.removed
                                                            ? <Badge className="bg-amber-100 text-amber-700 text-xs">Removed</Badge>
                                                            : u.disabled
                                                            ? <Badge className="bg-rose-100 text-rose-700 text-xs">Disabled</Badge>
                                                            : <Badge className="bg-emerald-100 text-emerald-700 text-xs">Active</Badge>}
                                                    </td>
                                                    <td className="p-2 text-xs text-muted-foreground">{u.created_at?.slice(0, 10)}</td>
                                                    <td className="p-2 text-right">
                                                        <div className="flex items-center justify-end gap-1">
                                                            {u.removed ? (
                                                                <Button size="sm" variant="outline" onClick={() => restoreUser(u.user_id)}>
                                                                    <Shield className="w-3.5 h-3.5 mr-1 text-emerald-600" /> Restore
                                                                </Button>
                                                            ) : (
                                                                <>
                                                                    {u.disabled ? (
                                                                        <Button size="sm" variant="outline" onClick={() => toggleUser(u.user_id, false)}>
                                                                            <UserCheck className="w-3.5 h-3.5 mr-1 text-emerald-600" /> Enable
                                                                        </Button>
                                                                    ) : (
                                                                        <Button size="sm" variant="outline" onClick={() => toggleUser(u.user_id, true)}>
                                                                            <UserX className="w-3.5 h-3.5 mr-1 text-rose-600" /> Disable
                                                                        </Button>
                                                                    )}
                                                                    <Button size="sm" variant="ghost" title="Remove account (temporary — frees email)" onClick={() => removeUser(u.user_id)}>
                                                                        <ShieldOff className="w-3.5 h-3.5 text-amber-600" />
                                                                    </Button>
                                                                    <Button size="sm" variant="ghost" title="Reset MFA" onClick={async () => {
                                                                        if (!window.confirm(`Reset 2FA for ${u.email}?`)) return;
                                                                        try {
                                                                            await axios.post(`/api/super-admin/users/${u.user_id}/reset-mfa`);
                                                                            toast.success('2FA reset');
                                                                        } catch { toast.error('Failed to reset 2FA'); }
                                                                    }}>
                                                                        <Shield className="w-3.5 h-3.5 text-amber-600" />
                                                                    </Button>
                                                                    <Button size="sm" variant="ghost" title="Force logout" onClick={async () => {
                                                                        if (!window.confirm(`Force logout ${u.email}?`)) return;
                                                                        try {
                                                                            await axios.post(`/api/super-admin/users/${u.user_id}/force-logout`);
                                                                            toast.success('User logged out');
                                                                        } catch { toast.error('Failed to force logout'); }
                                                                    }}>
                                                                        <PowerOff className="w-3.5 h-3.5 text-rose-500" />
                                                                    </Button>
                                                                </>
                                                            )}
                                                            <Button size="sm" variant="ghost" title="Delete account permanently" onClick={() => setDeleteUserDialog(u.user_id)}>
                                                                <Trash2 className="w-3.5 h-3.5 text-rose-500" />
                                                            </Button>
                                                        </div>
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

                {/* ── Platform Operators ── */}
                <TabsContent value="operators">
                    <div className="space-y-4">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <UserCog className="w-5 h-5 text-indigo-600" />
                                    Platform Operators
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                {/* Add operator form */}
                                <div className="flex gap-2 flex-wrap p-4 rounded-lg border bg-slate-50 dark:bg-slate-900/30">
                                    <input
                                        className="flex-1 min-w-40 border rounded px-3 py-2 text-sm bg-background"
                                        placeholder="Email address"
                                        value={newOperatorForm.email}
                                        onChange={e => setNewOperatorForm(f => ({ ...f, email: e.target.value }))}
                                    />
                                    <input
                                        className="flex-1 min-w-32 border rounded px-3 py-2 text-sm bg-background"
                                        placeholder="Display name"
                                        value={newOperatorForm.name}
                                        onChange={e => setNewOperatorForm(f => ({ ...f, name: e.target.value }))}
                                    />
                                    <select
                                        className="border rounded px-3 py-2 text-sm bg-background"
                                        value={newOperatorForm.role}
                                        onChange={e => setNewOperatorForm(f => ({ ...f, role: e.target.value }))}
                                    >
                                        {['platform_owner', 'platform_admin', 'platform_support', 'platform_billing', 'platform_readonly'].map(r => (
                                            <option key={r} value={r}>{r.replace('platform_', '').replace('_', ' ')}</option>
                                        ))}
                                    </select>
                                    <Button size="sm" onClick={addOperator} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                                        <PlusCircle className="w-4 h-4 mr-1" /> Add
                                    </Button>
                                </div>

                                {/* Operators list */}
                                {operators.length === 0 ? (
                                    <p className="text-sm text-muted-foreground text-center py-4">No platform operators defined. Users in PLATFORM_ADMINS env are always allowed.</p>
                                ) : (
                                    <div className="space-y-2">
                                        {operators.map(op => (
                                            <div key={op.operator_id} className="flex items-center justify-between p-3 rounded-lg border">
                                                <div>
                                                    <p className="font-medium text-sm">{op.name || op.email}</p>
                                                    <p className="text-xs text-muted-foreground">{op.email} — {op.role}</p>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    {op.is_active ? (
                                                        <Badge className="bg-emerald-100 text-emerald-700">Active</Badge>
                                                    ) : (
                                                        <Badge variant="outline">Inactive</Badge>
                                                    )}
                                                    <Button variant="ghost" size="sm" className="text-rose-600 hover:text-rose-700" onClick={() => removeOperator(op.operator_id)}>
                                                        <X className="w-4 h-4" />
                                                    </Button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* ── Emergency Controls ── */}
                <TabsContent value="emergency">
                    <div className="space-y-4">
                        <Card className="border-rose-200">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-rose-700">
                                    <Zap className="w-5 h-5" />
                                    Emergency Controls
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                <div className="p-4 rounded-lg border border-rose-200 bg-rose-50 dark:bg-rose-950/20">
                                    <p className="font-semibold text-rose-800 dark:text-rose-200 text-sm">Global Kill Switch</p>
                                    <p className="text-xs text-muted-foreground mb-3">Disables all paid features for ALL companies immediately.</p>
                                    <Button
                                        variant="outline"
                                        className="border-rose-400 text-rose-700 hover:bg-rose-100"
                                        onClick={killSwitch}
                                    >
                                        <PowerOff className="w-4 h-4 mr-2" /> Activate Kill Switch
                                    </Button>
                                </div>

                                <div className="p-4 rounded-lg border">
                                    <p className="font-semibold text-sm">Freeze RTI Submissions</p>
                                    <p className="text-xs text-muted-foreground mb-3">Prevent a specific company from submitting RTI to HMRC.</p>
                                    <div className="flex gap-2 flex-wrap">
                                        {companies.filter(c => !c.rti_frozen).slice(0, 10).map(c => (
                                            <Button key={c.company_id} variant="outline" size="sm" onClick={() => freezeRTI(c.company_id)}>
                                                Freeze {c.name}
                                            </Button>
                                        ))}
                                        {companies.filter(c => c.rti_frozen).map(c => (
                                            <Button key={c.company_id} variant="outline" size="sm" className="border-amber-300 text-amber-700" onClick={() => unfreezeRTI(c.company_id)}>
                                                Unfreeze {c.name}
                                            </Button>
                                        ))}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Emergency action log */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-base">Emergency Action Log</CardTitle>
                            </CardHeader>
                            <CardContent>
                                {emergencyActions.length === 0 ? (
                                    <p className="text-sm text-muted-foreground text-center py-4">No emergency actions recorded.</p>
                                ) : (
                                    <div className="space-y-2">
                                        {emergencyActions.map(a => (
                                            <div key={a.action_id} className="p-3 rounded-lg border text-sm">
                                                <div className="flex items-center justify-between">
                                                    <span className="font-medium">{a.action_type}</span>
                                                    <span className="text-xs text-muted-foreground">{new Date(a.created_at).toLocaleString()}</span>
                                                </div>
                                                <p className="text-xs text-muted-foreground">By: {a.operator_email} — {a.reason}</p>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
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

                {/* ── Security ── */}
                <TabsContent value="security">
                    <div className="space-y-4">
                        {/* Designated Platform Admins */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-base">
                                    <Shield className="w-4 h-4 text-indigo-600" />
                                    Designated Platform Admins
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                {designatedAdmins.length === 0 ? (
                                    <p className="text-sm text-muted-foreground">No designated platform admins found.</p>
                                ) : (
                                    <div className="space-y-2">
                                        {designatedAdmins.map((a, i) => (
                                            <div key={i} className="flex items-center justify-between p-2 border rounded text-sm">
                                                <div>
                                                    <p className="font-medium">{a.email}</p>
                                                    <p className="text-xs text-muted-foreground">{a.name}</p>
                                                </div>
                                                {a.mfa_active
                                                    ? <Badge className="bg-emerald-100 text-emerald-700 text-xs">2FA Active</Badge>
                                                    : <Badge className="bg-amber-100 text-amber-700 text-xs">No 2FA</Badge>
                                                }
                                            </div>
                                        ))}
                                    </div>
                                )}
                                <p className="text-xs text-muted-foreground mt-3">
                                    Add admin emails via the <code className="bg-muted px-1 rounded">PLATFORM_ADMINS</code> environment variable or set <code className="bg-muted px-1 rounded">is_platform_admin=true</code> on a user record.
                                </p>
                            </CardContent>
                        </Card>

                        {/* Security Policy Settings */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-base">
                                    <Lock className="w-4 h-4 text-indigo-600" />
                                    Platform Security Policy
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                {securitySettings && (
                                    <>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <Label className="text-sm font-medium">MFA Enforcement</Label>
                                                <Select
                                                    value={securityForm.mfa_enforcement || 'optional'}
                                                    onValueChange={v => setSecurityForm(f => ({ ...f, mfa_enforcement: v }))}
                                                >
                                                    <SelectTrigger className="mt-1">
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="optional">Optional (users can choose)</SelectItem>
                                                        <SelectItem value="required_for_admins">Required for admins only</SelectItem>
                                                        <SelectItem value="required_for_all">Required for all users</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                            <div>
                                                <Label className="text-sm font-medium">Session Timeout (hours)</Label>
                                                <Input
                                                    type="number"
                                                    min={1}
                                                    max={168}
                                                    value={securityForm.session_timeout_hours || 24}
                                                    onChange={e => setSecurityForm(f => ({ ...f, session_timeout_hours: Number(e.target.value) }))}
                                                    className="mt-1"
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-sm font-medium">Max Sessions Per User</Label>
                                                <Input
                                                    type="number"
                                                    min={1}
                                                    max={20}
                                                    value={securityForm.max_sessions_per_user || 5}
                                                    onChange={e => setSecurityForm(f => ({ ...f, max_sessions_per_user: Number(e.target.value) }))}
                                                    className="mt-1"
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-sm font-medium">Login Attempt Lockout Threshold</Label>
                                                <Input
                                                    type="number"
                                                    min={3}
                                                    max={50}
                                                    value={securityForm.login_attempt_lockout || 10}
                                                    onChange={e => setSecurityForm(f => ({ ...f, login_attempt_lockout: Number(e.target.value) }))}
                                                    className="mt-1"
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-sm font-medium">Minimum Password Length</Label>
                                                <Input
                                                    type="number"
                                                    min={8}
                                                    max={64}
                                                    value={securityForm.password_min_length || 8}
                                                    onChange={e => setSecurityForm(f => ({ ...f, password_min_length: Number(e.target.value) }))}
                                                    className="mt-1"
                                                />
                                            </div>
                                        </div>
                                        <div className="flex flex-wrap gap-4 pt-1">
                                            <div className="flex items-center gap-2">
                                                <Switch
                                                    checked={!!securityForm.require_uppercase}
                                                    onCheckedChange={v => setSecurityForm(f => ({ ...f, require_uppercase: v }))}
                                                />
                                                <Label className="text-sm">Require uppercase in passwords</Label>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Switch
                                                    checked={!!securityForm.require_special_char}
                                                    onCheckedChange={v => setSecurityForm(f => ({ ...f, require_special_char: v }))}
                                                />
                                                <Label className="text-sm">Require special character in passwords</Label>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Switch
                                                    checked={!!securityForm.ip_allowlist_enabled}
                                                    onCheckedChange={v => setSecurityForm(f => ({ ...f, ip_allowlist_enabled: v }))}
                                                />
                                                <Label className="text-sm">Enable IP allowlist</Label>
                                            </div>
                                        </div>
                                        {securityForm.ip_allowlist_enabled && (
                                            <div>
                                                <Label className="text-sm font-medium">Allowed IP Addresses (one per line)</Label>
                                                <textarea
                                                    className="w-full mt-1 p-2 border rounded text-sm bg-background font-mono"
                                                    rows={4}
                                                    placeholder="e.g. 192.168.1.0/24"
                                                    value={(securityForm.ip_allowlist || []).join('\n')}
                                                    onChange={e => setSecurityForm(f => ({ ...f, ip_allowlist: e.target.value.split('\n').map(s => s.trim()).filter(Boolean) }))}
                                                />
                                            </div>
                                        )}
                                        <div className="flex items-center justify-between pt-2 border-t">
                                            <Button onClick={saveSecuritySettings} disabled={savingSecSettings}>
                                                {savingSecSettings ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Save className="w-4 h-4 mr-1" />}
                                                Save Settings
                                            </Button>
                                        </div>
                                    </>
                                )}
                                {!securitySettings && <p className="text-sm text-muted-foreground">Loading security settings…</p>}
                            </CardContent>
                        </Card>

                        {/* Session Management */}
                        <Card className="border-rose-200">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-base text-rose-700">
                                    <LogOut className="w-4 h-4" />
                                    Session Management
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                <div className="p-4 rounded-lg bg-rose-50 dark:bg-rose-950/20 border border-rose-200">
                                    <p className="font-semibold text-sm text-rose-800 dark:text-rose-200">Revoke All Active Sessions</p>
                                    <p className="text-xs text-muted-foreground mb-3">Forcibly log out every user across the entire platform. Use only in security emergencies.</p>
                                    <Button variant="outline" className="border-rose-400 text-rose-700 hover:bg-rose-100" onClick={revokeAllSessions}>
                                        <LogOut className="w-4 h-4 mr-2" /> Revoke All Sessions
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* ── System Health ── */}
                <TabsContent value="health">
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-semibold flex items-center gap-2">
                                <HeartPulse className="w-5 h-5 text-indigo-600" /> System Health
                            </h2>
                            <Button variant="outline" size="sm" onClick={refreshHealth} disabled={healthLoading}>
                                {healthLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                                <span className="ml-1">Refresh</span>
                            </Button>
                        </div>

                        {systemHealth ? (
                            <>
                                {/* Platform stats bar */}
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                    {[
                                        ['Total Companies', systemHealth.platform?.total_companies],
                                        ['Active Companies', systemHealth.platform?.active_companies],
                                        ['Active Sessions', systemHealth.platform?.active_sessions],
                                        ['Audit Events (24h)', systemHealth.platform?.audit_events_24h],
                                    ].map(([label, val]) => (
                                        <Card key={label} className="p-3">
                                            <p className="text-xs text-muted-foreground">{label}</p>
                                            <p className="text-2xl font-bold">{val ?? '—'}</p>
                                        </Card>
                                    ))}
                                </div>

                                {/* Service health cards */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {Object.entries(systemHealth.services || {}).map(([svc, info]) => {
                                        const StatusIcon = info.status === 'healthy' ? CheckCircle2
                                            : info.status === 'warning' ? AlertCircle
                                            : XCircle;
                                        const statusColor = info.status === 'healthy' ? 'text-emerald-600'
                                            : info.status === 'warning' ? 'text-amber-600'
                                            : 'text-rose-600';
                                        const svcLabel = svc.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                                        return (
                                            <Card key={svc} className="p-4">
                                                <div className="flex items-center justify-between mb-2">
                                                    <div className="flex items-center gap-2">
                                                        <Server className="w-4 h-4 text-muted-foreground" />
                                                        <span className="font-medium text-sm">{svcLabel}</span>
                                                    </div>
                                                    <div className={`flex items-center gap-1 text-xs font-semibold ${statusColor}`}>
                                                        <StatusIcon className="w-3.5 h-3.5" />
                                                        {info.status}
                                                    </div>
                                                </div>
                                                <div className="text-xs text-muted-foreground space-y-0.5">
                                                    {info.pending !== undefined && <p>Pending: {info.pending}</p>}
                                                    {info.failed !== undefined && <p>Failed: {info.failed}</p>}
                                                    {info.processed_last_7d !== undefined && <p>Processed (7d): {info.processed_last_7d}</p>}
                                                    {info.pending_notifications !== undefined && <p>Pending notifications: {info.pending_notifications}</p>}
                                                    {info.open_alerts !== undefined && <p>Open alerts: {info.open_alerts}</p>}
                                                    {info.last_activity && <p>Last activity: {new Date(info.last_activity).toLocaleString()}</p>}
                                                    {info.note && <p className="italic">{info.note}</p>}
                                                </div>
                                            </Card>
                                        );
                                    })}
                                </div>

                                <p className="text-xs text-muted-foreground text-right">
                                    Last refreshed: {new Date(systemHealth.timestamp).toLocaleString()}
                                </p>
                            </>
                        ) : (
                            <Card className="p-6 text-center">
                                <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-muted-foreground" />
                                <p className="text-sm text-muted-foreground">Loading system health…</p>
                            </Card>
                        )}
                    </div>
                </TabsContent>

                {/* ── Discount Codes ── */}
                <TabsContent value="discounts">
                    <div className="space-y-4">
                        {/* Summary cards */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            {discountSummary.length === 0 ? (
                                <Card className="col-span-3">
                                    <CardContent className="p-6 text-center text-muted-foreground text-sm">
                                        No discount code redemptions yet.
                                    </CardContent>
                                </Card>
                            ) : discountSummary.map(s => (
                                <Card key={s.code}>
                                    <CardContent className="p-4">
                                        <p className="text-xs text-muted-foreground">Code</p>
                                        <p className="text-lg font-bold font-mono">{s.code}-</p>
                                        <p className="text-sm mt-1">{s.discount_percent}% off · {s.months} months</p>
                                        <p className="text-2xl font-bold text-indigo-600 mt-2">{s.total_uses}</p>
                                        <p className="text-xs text-muted-foreground">total redemptions</p>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>

                        {/* Full usage table */}
                        <Card>
                            <CardHeader><CardTitle>Redemption Log — BGS2026-</CardTitle></CardHeader>
                            <CardContent className="p-0">
                                {discountUsages.length === 0 ? (
                                    <p className="text-sm text-muted-foreground p-6">No redemptions recorded yet. Users who enter this code at signup will appear here.</p>
                                ) : (
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm">
                                            <thead>
                                                <tr className="border-b bg-muted/40">
                                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Code</th>
                                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Name</th>
                                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Email</th>
                                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Company</th>
                                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Discount</th>
                                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Applied</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {discountUsages.map((u, i) => (
                                                    <tr key={u.usage_id || i} className="border-b last:border-0 hover:bg-accent/30">
                                                        <td className="px-4 py-3 font-mono font-semibold text-indigo-600">{u.code}-</td>
                                                        <td className="px-4 py-3">{u.user_name || '—'}</td>
                                                        <td className="px-4 py-3 text-muted-foreground">{u.user_email || '—'}</td>
                                                        <td className="px-4 py-3">{u.company_name || '—'}</td>
                                                        <td className="px-4 py-3">
                                                            <Badge className="bg-emerald-100 text-emerald-700">{u.discount_percent}% · {u.months}mo</Badge>
                                                        </td>
                                                        <td className="px-4 py-3 text-muted-foreground text-xs">
                                                            {u.applied_at ? new Date(u.applied_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* ── Welcome Email Editor ── */}
                <TabsContent value="email">
                    <div className="space-y-4">
                        <Card>
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <div>
                                        <CardTitle className="flex items-center gap-2"><Mail className="w-4 h-4" /> Welcome Email Template</CardTitle>
                                        <p className="text-sm text-muted-foreground mt-1">
                                            Sent automatically to every new signup. Use <code className="bg-muted px-1 rounded text-xs">{'{{name}}'}</code> and <code className="bg-muted px-1 rounded text-xs">{'{{company_name}}'}</code> as placeholders.
                                            {emailTpl.is_default && <span className="ml-2 text-amber-600 font-medium">(Using built-in default — save to customise)</span>}
                                        </p>
                                    </div>
                                    <div className="flex gap-2">
                                        <Button size="sm" variant="outline" onClick={() => setEmailPreviewOpen(true)}>
                                            <Eye className="w-3.5 h-3.5 mr-1" /> Preview
                                        </Button>
                                        <Button
                                            size="sm" variant="outline"
                                            disabled={emailTplTesting}
                                            onClick={async () => {
                                                setEmailTplTesting(true);
                                                try {
                                                    const r = await ax('post', '/api/super-admin/email-templates/welcome/send-test');
                                                    if (r.data.status === 'sent') toast.success(`Test email sent to ${r.data.to}`);
                                                    else if (r.data.status === 'mock') toast.info('Email service in mock mode — set RESEND_API_KEY to send real emails');
                                                    else toast.error(r.data.error || 'Failed to send test');
                                                } catch { toast.error('Failed to send test email'); }
                                                finally { setEmailTplTesting(false); }
                                            }}
                                        >
                                            {emailTplTesting ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <Send className="w-3.5 h-3.5 mr-1" />}
                                            Send Test to My Email
                                        </Button>
                                        <Button
                                            size="sm" variant="ghost" className="text-muted-foreground"
                                            onClick={async () => {
                                                if (!window.confirm('Reset to the built-in default template? Your edits will be lost.')) return;
                                                try {
                                                    await ax('post', '/api/super-admin/email-templates/welcome/reset');
                                                    const r = await ax('get', '/api/super-admin/email-templates/welcome');
                                                    setEmailTpl(r.data);
                                                    toast.success('Reset to default template');
                                                } catch { toast.error('Reset failed'); }
                                            }}
                                        >
                                            <RotateCcw className="w-3.5 h-3.5 mr-1" /> Reset to Default
                                        </Button>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1.5">
                                        <Label>From Name</Label>
                                        <Input value={emailTpl.from_name || ''} onChange={e => setEmailTpl(t => ({ ...t, from_name: e.target.value }))} placeholder="RealtouchHR" />
                                    </div>
                                    <div className="space-y-1.5">
                                        <Label>From Email</Label>
                                        <Input value={emailTpl.from_email || ''} onChange={e => setEmailTpl(t => ({ ...t, from_email: e.target.value }))} placeholder="info@realtouchhr.com" />
                                        <p className="text-xs text-muted-foreground">Must be a verified sender in your Resend account</p>
                                    </div>
                                </div>
                                <div className="space-y-1.5">
                                    <Label>Subject Line</Label>
                                    <Input value={emailTpl.subject || ''} onChange={e => setEmailTpl(t => ({ ...t, subject: e.target.value }))} placeholder="Welcome to RealtouchHR 🎉" />
                                </div>
                                <div className="space-y-1.5">
                                    <Label>HTML Body</Label>
                                    <Textarea
                                        value={emailTpl.html_body || ''}
                                        onChange={e => setEmailTpl(t => ({ ...t, html_body: e.target.value }))}
                                        className="font-mono text-xs min-h-[420px] resize-y"
                                        placeholder="Enter full HTML email body here..."
                                    />
                                </div>
                                <div className="flex justify-end">
                                    <Button
                                        disabled={emailTplSaving}
                                        onClick={async () => {
                                            setEmailTplSaving(true);
                                            try {
                                                await ax('put', '/api/super-admin/email-templates/welcome', emailTpl);
                                                setEmailTpl(t => ({ ...t, is_default: false }));
                                                toast.success('Welcome email template saved');
                                            } catch { toast.error('Failed to save template'); }
                                            finally { setEmailTplSaving(false); }
                                        }}
                                    >
                                        {emailTplSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                                        Save Template
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

            </Tabs>

            {/* ── Email Preview Modal ── */}
            <Dialog open={emailPreviewOpen} onOpenChange={setEmailPreviewOpen}>
                <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col">
                    <DialogHeader>
                        <DialogTitle>Email Preview — {emailTpl.subject}</DialogTitle>
                    </DialogHeader>
                    <div className="flex-1 overflow-hidden rounded border">
                        <iframe
                            title="email-preview"
                            srcDoc={emailTpl.html_body ? emailTpl.html_body.replace(/\{\{name\}\}/g, 'John Smith').replace(/\{\{company_name\}\}/g, 'Acme Ltd') : '<p style="padding:20px;font-family:sans-serif;color:#6b7280">No HTML content yet</p>'}
                            className="w-full h-[60vh] border-0"
                            sandbox="allow-same-origin"
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEmailPreviewOpen(false)}>Close</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

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

            {/* ── Delete user dialog ── */}
            <Dialog open={!!deleteUserDialog} onOpenChange={o => !o && setDeleteUserDialog(null)}>
                <DialogContent className="max-w-sm">
                    <DialogHeader><DialogTitle className="flex items-center gap-2 text-rose-600"><AlertTriangle className="w-5 h-5" />Delete account</DialogTitle></DialogHeader>
                    <p className="text-sm">This permanently deletes this user account. This cannot be undone. To temporarily free up the email instead (and allow restoring later), use Remove instead of Delete.</p>
                    <p className="text-xs text-muted-foreground mt-2 font-mono break-all">{deleteUserDialog}</p>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteUserDialog(null)}>Cancel</Button>
                        <Button variant="destructive" onClick={() => deleteUser(deleteUserDialog)}>Delete permanently</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
