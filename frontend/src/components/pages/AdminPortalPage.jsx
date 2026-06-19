import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../ui/dialog';
import { toast } from 'sonner';
import {
    Users, UserPlus, Shield, Trash2, Clock, Mail, Send,
    Loader2, AlertTriangle, Key, Activity, RefreshCw, Copy, Download, Lock,
    LayoutDashboard, Settings, Package, Star, Bell, Building2, CreditCard,
    CheckCircle2, XCircle, ToggleLeft, ToggleRight,
} from 'lucide-react';
import { Switch } from '../ui/switch';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// ---------------------------------------------------------------------------
// Danger Zone re-auth dialog
// ---------------------------------------------------------------------------
function DangerReauthDialog({ open, onOpenChange, title, desc, onConfirmed }) {
    const { token: dialogToken } = useAuth();
    const [password, setPassword] = React.useState('');
    const [verifying, setVerifying] = React.useState(false);
    const [err, setErr] = React.useState('');

    const handleClose = () => { setPassword(''); setErr(''); onOpenChange(false); };

    const handleVerify = async (e) => {
        e.preventDefault();
        if (!password) { setErr('Password is required'); return; }
        setVerifying(true); setErr('');
        try {
            const headers = { Authorization: `Bearer ${dialogToken}` };
            await axios.post(`${API_URL}/api/admin/danger-zone/verify`, { password }, { headers, withCredentials: true });
            handleClose();
            onConfirmed();
        } catch (ex) {
            setErr(ex.response?.data?.detail || 'Verification failed');
        } finally {
            setVerifying(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-rose-700">
                        <AlertTriangle className="w-5 h-5" /> {title}
                    </DialogTitle>
                </DialogHeader>
                <form onSubmit={handleVerify} className="space-y-4">
                    <p className="text-sm text-muted-foreground">{desc}</p>
                    <div className="rounded-lg bg-rose-50 dark:bg-rose-950/20 border border-rose-200 p-3 text-sm text-rose-700 dark:text-rose-300">
                        This action is destructive and <strong>cannot be undone</strong>. Re-enter your password to confirm.
                    </div>
                    <div>
                        <Label>Your password</Label>
                        <Input
                            type="password"
                            className="mt-1"
                            value={password}
                            onChange={e => { setPassword(e.target.value); setErr(''); }}
                            placeholder="Enter your password to confirm"
                            autoFocus
                            data-testid="danger-zone-password"
                        />
                        {err && <p className="text-xs text-rose-600 mt-1">{err}</p>}
                    </div>
                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={handleClose}>Cancel</Button>
                        <Button type="submit" disabled={verifying} className="bg-rose-600 hover:bg-rose-700 text-white" data-testid="danger-zone-confirm">
                            {verifying ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Verifying…</> : 'Confirm action'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

const ROLES = [
    { id: 'owner', label: 'Owner', desc: 'Full platform control including billing and danger zone', color: 'bg-purple-100 text-purple-800 dark:bg-purple-950/40 dark:text-purple-200' },
    { id: 'admin', label: 'Administrator', desc: 'Full system access except billing ownership transfer', color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-200' },
    { id: 'hr_admin', label: 'HR Admin', desc: 'Manage employees, leave, documents, UKVI', color: 'bg-blue-100 text-blue-800 dark:bg-blue-950/40 dark:text-blue-200' },
    { id: 'hr_manager', label: 'HR Manager', desc: 'View and manage HR records, approve leave', color: 'bg-sky-100 text-sky-800 dark:bg-sky-950/40 dark:text-sky-200' },
    { id: 'payroll_admin', label: 'Payroll Admin', desc: 'Run payroll, manage RTI, HMRC submissions', color: 'bg-teal-100 text-teal-800 dark:bg-teal-950/40 dark:text-teal-200' },
    { id: 'compliance_manager', label: 'Compliance Manager', desc: 'UKVI compliance, right to work, audit logs', color: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200' },
    { id: 'manager', label: 'Line Manager', desc: 'Approve team leave, timesheets, and performance', color: 'bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-200' },
    { id: 'auditor', label: 'Auditor', desc: 'Read-only access to audit logs and reports', color: 'bg-slate-100 text-slate-800 dark:bg-slate-900/40 dark:text-slate-200' },
    { id: 'employee', label: 'Employee', desc: 'Self-service portal access only', color: 'bg-stone-100 text-stone-800 dark:bg-stone-900/40 dark:text-stone-200' },
    { id: 'viewer', label: 'Viewer', desc: 'Read-only access to basic data', color: 'bg-zinc-100 text-zinc-800 dark:bg-zinc-900/40 dark:text-zinc-200' },
];

const MODULES = [
    { key: 'payroll', label: 'Payroll', desc: 'Pay runs, payslips, PAYE calculations' },
    { key: 'hmrc_rti', label: 'HMRC RTI', desc: 'Real Time Information FPS/EPS submissions' },
    { key: 'ukvi_compliance', label: 'UKVI Compliance', desc: 'Visa tracking, RTW checks, CoS register' },
    { key: 'leave_management', label: 'Leave Management', desc: 'Leave requests, balances, approvals' },
    { key: 'performance', label: 'Performance', desc: 'Appraisals, objectives, reviews' },
    { key: 'training', label: 'Training', desc: 'Course catalogue and completion tracking' },
    { key: 'documents', label: 'Documents', desc: 'Document management and e-signatures' },
    { key: 'time_tracking', label: 'Time Tracking', desc: 'Timesheets, clock-in/out, shifts' },
    { key: 'hr_analytics', label: 'HR Analytics', desc: 'Workforce reports and data insights' },
    { key: 'gdpr', label: 'GDPR Centre', desc: 'DSAR, DPIA, breach reporting, processors' },
];

const PREMIUM_FEATURES = [
    { key: 'ukvi_compliance_scanner', label: 'UKVI Compliance Scanner', desc: '2 automated scans per billing month', plans: 'All plans' },
    { key: 'ukvi_report_download', label: 'UKVI Report Downloads', desc: 'PDF/DOCX compliance reports', plans: 'Professional + Enterprise' },
    { key: 'hmrc_rti', label: 'HMRC RTI Submissions', desc: 'FPS/EPS live submission to HMRC', plans: 'Professional + Enterprise' },
    { key: 'enterprise_multi_entity', label: 'Multi-Entity Support', desc: 'Manage multiple companies', plans: 'Enterprise' },
    { key: 'enterprise_sso', label: 'SSO / SAML', desc: 'Single sign-on via SCIM/SAML', plans: 'Enterprise' },
    { key: 'ai_copilot', label: 'AI Copilot', desc: 'AI-powered HR assistant', plans: 'All plans' },
];

export default function AdminPortalPage() {
    const { user, token: authToken } = useAuth();
    const [users, setUsers] = useState([]);
    const [invites, setInvites] = useState([]);
    const [auditLog, setAuditLog] = useState([]);
    const [loading, setLoading] = useState(true);
    const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
    const [inviteForm, setInviteForm] = useState({ email: '', name: '', role: 'hr_manager' });
    const [securityPolicy, setSecurityPolicy] = useState(null);
    const [exportLoading, setExportLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const [companyModules, setCompanyModules] = useState([]);
    const [moduleTogglingKey, setModuleTogglingKey] = useState(null);
    const [dangerDialog, setDangerDialog] = useState(null); // { title, desc, action }

    const token = () => authToken;

    const fetchAll = async () => {
        setLoading(true);
        try {
            const headers = { Authorization: `Bearer ${token()}` };
            const [uRes, iRes, aRes, sRes, mRes] = await Promise.all([
                axios.get(`${API_URL}/api/users`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/users/invites`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/enterprise/audit-log?limit=50`, { headers, withCredentials: true }).catch(() => ({ data: { audit_log: [] } })),
                axios.get(`${API_URL}/api/company/security-policy`, { headers, withCredentials: true }).catch(() => null),
                axios.get(`${API_URL}/api/admin/modules`, { headers, withCredentials: true }).catch(() => ({ data: { modules: [] } })),
            ]);
            setUsers(uRes.data.users || []);
            setInvites(iRes.data.invites || []);
            setAuditLog(aRes.data.audit_log || aRes.data.logs || []);
            if (sRes) setSecurityPolicy(sRes.data);
            setCompanyModules(mRes.data.modules || []);
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to load admin data');
        } finally {
            setLoading(false);
        }
    };

    const toggleModule = async (moduleKey, enabled) => {
        setModuleTogglingKey(moduleKey);
        try {
            const headers = { Authorization: `Bearer ${token()}` };
            await axios.patch(`${API_URL}/api/admin/modules/${moduleKey}`, { module_key: moduleKey, enabled }, { headers, withCredentials: true });
            setCompanyModules(prev => prev.map(m => m.key === moduleKey ? { ...m, enabled } : m));
            toast.success(`${moduleKey.replace('_', ' ')} ${enabled ? 'enabled' : 'disabled'}`);
        } catch (e) {
            toast.error(e.response?.data?.detail || 'Module toggle failed');
        } finally {
            setModuleTogglingKey(null);
        }
    };

    const downloadCompanyData = async () => {
        setExportLoading(true);
        try {
            const headers = { Authorization: `Bearer ${token()}` };
            const res = await axios.get(`${API_URL}/api/company/data-export`, { headers, withCredentials: true, responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const a = document.createElement('a');
            a.href = url; a.download = `company_data_export_${new Date().toISOString().slice(0, 10)}.json`;
            a.click(); window.URL.revokeObjectURL(url);
            toast.success('Export downloaded');
        } catch (e) { toast.error(e.response?.data?.detail || 'Export failed'); }
        finally { setExportLoading(false); }
    };

    const updateSecurityPolicy = async (key, value) => {
        try {
            const headers = { Authorization: `Bearer ${token()}` };
            const newPolicy = { ...(securityPolicy?.policy || {}), [key]: value };
            await axios.put(`${API_URL}/api/company/security-policy`, newPolicy, { headers, withCredentials: true });
            setSecurityPolicy({ ...securityPolicy, policy: newPolicy });
            toast.success('Policy updated');
        } catch (e) { toast.error('Failed'); }
    };

    useEffect(() => { fetchAll(); }, []);

    const handleInvite = async (e) => {
        e.preventDefault();
        setSending(true);
        try {
            const res = await axios.post(`${API_URL}/api/users/invite`, inviteForm, {
                headers: { Authorization: `Bearer ${token()}` }, withCredentials: true,
            });
            toast.success(`Invitation sent to ${inviteForm.email}`);
            setInviteDialogOpen(false);
            setInviteForm({ email: '', name: '', role: 'hr_manager' });
            fetchAll();
            // Copy link for convenience
            if (res.data.invite_link) {
                navigator.clipboard?.writeText(res.data.invite_link).catch(() => {});
            }
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Invite failed');
        } finally {
            setSending(false);
        }
    };

    const updateRole = async (userId, newRole) => {
        try {
            await axios.put(
                `${API_URL}/api/users/${userId}/role`,
                { role: newRole },
                { headers: { Authorization: `Bearer ${token()}` }, withCredentials: true }
            );
            toast.success('Role updated');
            fetchAll();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Role update failed');
        }
    };

    const removeUser = async (userId) => {
        if (!window.confirm('Remove this user from your company? This cannot be undone.')) return;
        try {
            await axios.delete(`${API_URL}/api/users/${userId}`, {
                headers: { Authorization: `Bearer ${token()}` }, withCredentials: true,
            });
            toast.success('User removed');
            fetchAll();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Remove failed');
        }
    };

    const revokeInvite = async (inviteId) => {
        try {
            await axios.delete(`${API_URL}/api/users/invites/${inviteId}`, {
                headers: { Authorization: `Bearer ${token()}` }, withCredentials: true,
            });
            toast.success('Invite revoked');
            fetchAll();
        } catch (err) {
            toast.error('Revoke failed');
        }
    };

    const canManage = user?.role === 'owner';
    const canInvite = user?.role === 'owner' || user?.role === 'admin';

    if (user?.role !== 'owner' && user?.role !== 'admin') {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Card className="max-w-md">
                    <CardContent className="p-8 text-center">
                        <Shield className="w-12 h-12 text-rose-500 mx-auto mb-3" />
                        <h3 className="text-xl font-bold">Access restricted</h3>
                        <p className="text-muted-foreground mt-2 text-sm">
                            Only Owners and Administrators can access the Admin Portal.
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="space-y-6" data-testid="admin-portal-page">
            <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Admin Portal</h1>
                    <p className="text-muted-foreground mt-1">
                        Manage your team, permissions, and company-wide settings.
                    </p>
                </div>
                {canInvite && (
                    <Button onClick={() => setInviteDialogOpen(true)} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="invite-user-btn">
                        <UserPlus className="w-4 h-4 mr-2" /> Invite user
                    </Button>
                )}
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                </div>
            ) : (
                <Tabs defaultValue="overview" className="space-y-4">
                    <TabsList className="flex-wrap h-auto gap-1">
                        <TabsTrigger value="overview" data-testid="tab-overview"><LayoutDashboard className="w-3.5 h-3.5 mr-1.5" /> Overview</TabsTrigger>
                        <TabsTrigger value="team" data-testid="tab-team"><Users className="w-3.5 h-3.5 mr-1.5" /> Team</TabsTrigger>
                        <TabsTrigger value="invites" data-testid="tab-invites"><Mail className="w-3.5 h-3.5 mr-1.5" /> Invites</TabsTrigger>
                        <TabsTrigger value="roles" data-testid="tab-roles"><Shield className="w-3.5 h-3.5 mr-1.5" /> Roles & Permissions</TabsTrigger>
                        <TabsTrigger value="modules" data-testid="tab-modules"><Package className="w-3.5 h-3.5 mr-1.5" /> Modules</TabsTrigger>
                        <TabsTrigger value="premium" data-testid="tab-premium"><Star className="w-3.5 h-3.5 mr-1.5" /> Premium Features</TabsTrigger>
                        <TabsTrigger value="security" data-testid="tab-security-policy"><Lock className="w-3.5 h-3.5 mr-1.5" /> Security</TabsTrigger>
                        <TabsTrigger value="audit" data-testid="tab-audit"><Activity className="w-3.5 h-3.5 mr-1.5" /> Audit Log</TabsTrigger>
                        <TabsTrigger value="data" data-testid="tab-data"><Download className="w-3.5 h-3.5 mr-1.5" /> Data Export</TabsTrigger>
                        <TabsTrigger value="notifications" data-testid="tab-notifications"><Bell className="w-3.5 h-3.5 mr-1.5" /> Alerts</TabsTrigger>
                        <TabsTrigger value="company" data-testid="tab-company"><Building2 className="w-3.5 h-3.5 mr-1.5" /> Company</TabsTrigger>
                        <TabsTrigger value="billing" data-testid="tab-billing"><CreditCard className="w-3.5 h-3.5 mr-1.5" /> Billing</TabsTrigger>
                        <TabsTrigger value="danger" data-testid="tab-danger"><AlertTriangle className="w-3.5 h-3.5 mr-1.5" /> Danger Zone</TabsTrigger>
                    </TabsList>

                    {/* OVERVIEW TAB */}
                    <TabsContent value="overview">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <Card>
                                <CardContent className="p-5">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-950/40 flex items-center justify-center">
                                            <Users className="w-5 h-5 text-indigo-600" />
                                        </div>
                                        <div>
                                            <p className="text-xs text-muted-foreground">Team Members</p>
                                            <p className="text-2xl font-bold">{users.length}</p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="p-5">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-950/40 flex items-center justify-center">
                                            <Mail className="w-5 h-5 text-amber-600" />
                                        </div>
                                        <div>
                                            <p className="text-xs text-muted-foreground">Pending Invites</p>
                                            <p className="text-2xl font-bold">{invites.filter(i => i.status === 'pending').length}</p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="p-5">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-950/40 flex items-center justify-center">
                                            <Activity className="w-5 h-5 text-emerald-600" />
                                        </div>
                                        <div>
                                            <p className="text-xs text-muted-foreground">Audit Events (last 50)</p>
                                            <p className="text-2xl font-bold">{auditLog.length}</p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                        <Card className="mt-4">
                            <CardHeader>
                                <CardTitle className="text-base">Quick Actions</CardTitle>
                            </CardHeader>
                            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {[
                                    { label: 'Invite a team member', icon: <UserPlus className="w-4 h-4" />, action: () => setInviteDialogOpen(true) },
                                    { label: 'View audit log', icon: <Activity className="w-4 h-4" />, action: () => document.querySelector('[data-testid="tab-audit"]')?.click() },
                                    { label: 'Security settings', icon: <Lock className="w-4 h-4" />, action: () => document.querySelector('[data-testid="tab-security-policy"]')?.click() },
                                    { label: 'Export company data', icon: <Download className="w-4 h-4" />, action: downloadCompanyData },
                                ].map((a, i) => (
                                    <Button key={i} variant="outline" className="justify-start" onClick={a.action}>
                                        {a.icon} <span className="ml-2">{a.label}</span>
                                    </Button>
                                ))}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* TEAM TAB */}
                    <TabsContent value="team">
                        <Card>
                            <CardHeader>
                                <CardTitle>Company users</CardTitle>
                                <CardDescription>All users who have access to this company. Owner can change roles and remove members.</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b text-xs uppercase tracking-wider text-muted-foreground">
                                                <th className="text-left p-3">Name</th>
                                                <th className="text-left p-3">Email</th>
                                                <th className="text-left p-3">Role</th>
                                                <th className="text-left p-3">Last login</th>
                                                <th className="text-right p-3">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {users.map((u) => (
                                                <tr key={u.user_id} className="border-b hover:bg-accent/50" data-testid={`user-row-${u.user_id}`}>
                                                    <td className="p-3 font-medium">{u.name}</td>
                                                    <td className="p-3 text-muted-foreground">{u.email}</td>
                                                    <td className="p-3">
                                                        {canManage && u.user_id !== user.user_id && u.role !== 'owner' ? (
                                                            <Select value={u.role} onValueChange={(v) => updateRole(u.user_id, v)}>
                                                                <SelectTrigger className="w-40 h-8" data-testid={`role-select-${u.user_id}`}>
                                                                    <SelectValue />
                                                                </SelectTrigger>
                                                                <SelectContent>
                                                                    {ROLES.map((r) => (
                                                                        <SelectItem key={r.id} value={r.id}>{r.label}</SelectItem>
                                                                    ))}
                                                                </SelectContent>
                                                            </Select>
                                                        ) : (
                                                            <Badge variant="outline" className={
                                                                u.role === 'owner' ? 'bg-amber-50 border-amber-300 text-amber-700 dark:bg-amber-950/30'
                                                                : u.role === 'admin' ? 'bg-indigo-50 border-indigo-300 text-indigo-700 dark:bg-indigo-950/30'
                                                                : 'bg-slate-50 border-slate-200 text-slate-700 dark:bg-slate-900/30'
                                                            }>
                                                                {ROLES.find(r => r.id === u.role)?.label || u.role}
                                                            </Badge>
                                                        )}
                                                    </td>
                                                    <td className="p-3 text-muted-foreground text-xs">
                                                        {u.last_login ? new Date(u.last_login).toLocaleString() : '—'}
                                                    </td>
                                                    <td className="p-3 text-right">
                                                        {canManage && u.user_id !== user.user_id && u.role !== 'owner' && (
                                                            <Button variant="ghost" size="sm" onClick={() => removeUser(u.user_id)} className="text-rose-600 hover:text-rose-700" data-testid={`remove-user-${u.user_id}`}>
                                                                <Trash2 className="w-4 h-4" />
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

                    {/* INVITES TAB */}
                    <TabsContent value="invites">
                        <Card>
                            <CardHeader>
                                <CardTitle>Pending invitations</CardTitle>
                                <CardDescription>Invites that have been sent but not yet accepted.</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {!invites.length ? (
                                    <p className="text-center py-8 text-muted-foreground">No invitations yet. Click "Invite user" above to add team members.</p>
                                ) : (
                                    <div className="space-y-2">
                                        {invites.map((inv) => (
                                            <div key={inv.invite_id} className="flex items-center justify-between p-3 border rounded-lg" data-testid={`invite-row-${inv.invite_id}`}>
                                                <div>
                                                    <p className="font-medium">{inv.name} <span className="text-muted-foreground font-normal">· {inv.email}</span></p>
                                                    <p className="text-xs text-muted-foreground mt-0.5">
                                                        {ROLES.find(r => r.id === inv.role)?.label || inv.role} · invited by {inv.invited_by_name} · expires {new Date(inv.expires_at).toLocaleDateString()}
                                                    </p>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <Badge className={
                                                        inv.status === 'pending' ? 'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-950/30'
                                                        : inv.status === 'accepted' ? 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-950/30'
                                                        : 'bg-slate-50 border-slate-200 text-slate-700'
                                                    }>{(inv.status || 'pending').toUpperCase()}</Badge>
                                                    {inv.status === 'pending' && (
                                                        <Button variant="ghost" size="sm" onClick={() => revokeInvite(inv.invite_id)} data-testid={`revoke-${inv.invite_id}`}>
                                                            <Trash2 className="w-4 h-4 text-rose-600" />
                                                        </Button>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* ROLES & PERMISSIONS TAB */}
                    <TabsContent value="roles">
                        <Card>
                            <CardHeader>
                                <CardTitle>Roles & Permissions</CardTitle>
                                <CardDescription>
                                    RealtouchHR uses role-based access control (RBAC). Each user is assigned one role.
                                    The Owner cannot be changed. Change roles in the Team tab.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {ROLES.map((r) => (
                                    <div key={r.id} className="flex items-start gap-4 p-4 rounded-lg border">
                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${r.color}`}>
                                            {r.label}
                                        </span>
                                        <div>
                                            <p className="text-sm text-muted-foreground">{r.desc}</p>
                                            <p className="text-xs text-muted-foreground mt-0.5">
                                                {users.filter(u => u.role === r.id).length} user(s) with this role
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* MODULES & FEATURES TAB */}
                    <TabsContent value="modules">
                        <Card>
                            <CardHeader>
                                <CardTitle>Modules & Features</CardTitle>
                                <CardDescription>
                                    Enable or disable modules for your company. Disabled modules are hidden in navigation and blocked at the API level. Changes are audit-logged.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {(companyModules.length > 0 ? companyModules : MODULES.map(m => ({ ...m, enabled: true }))).map((mod) => (
                                    <div key={mod.key} className="flex items-center justify-between p-4 rounded-lg border">
                                        <div>
                                            <p className="font-medium text-sm">{mod.label}</p>
                                            <p className="text-xs text-muted-foreground">{mod.desc || ''}</p>
                                            {mod.plan_required && (
                                                <span className="text-xs text-indigo-600 mt-0.5">Requires: {mod.plan_required} plan</span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2">
                                            {mod.enabled
                                                ? <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                                                : <XCircle className="w-4 h-4 text-rose-400" />}
                                            <span className={`text-xs ${mod.enabled ? 'text-emerald-600' : 'text-rose-500'}`}>
                                                {mod.enabled ? 'Enabled' : 'Disabled'}
                                            </span>
                                            <Switch
                                                checked={mod.enabled}
                                                disabled={moduleTogglingKey === mod.key}
                                                onCheckedChange={(checked) => toggleModule(mod.key, checked)}
                                                data-testid={`module-toggle-${mod.key}`}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* PREMIUM FEATURES TAB */}
                    <TabsContent value="premium">
                        <Card>
                            <CardHeader>
                                <CardTitle>Premium Features</CardTitle>
                                <CardDescription>
                                    Features available on specific subscription plans. Upgrade your plan in Billing to unlock more features.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {PREMIUM_FEATURES.map((f) => (
                                    <div key={f.key} className="flex items-start justify-between p-4 rounded-lg border">
                                        <div className="flex items-start gap-3">
                                            <Star className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                                            <div>
                                                <p className="font-medium text-sm">{f.label}</p>
                                                <p className="text-xs text-muted-foreground">{f.desc}</p>
                                            </div>
                                        </div>
                                        <span className="text-xs bg-purple-100 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 px-2 py-0.5 rounded-full flex-shrink-0">
                                            {f.plans}
                                        </span>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* AUDIT TAB */}
                    <TabsContent value="audit">
                        <Card>
                            <CardHeader>
                                <CardTitle>Audit log</CardTitle>
                                <CardDescription>Every action performed in your company is logged for compliance (GDPR + HMRC 7-year retention).</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {!auditLog.length ? (
                                    <p className="text-center py-8 text-muted-foreground">No audit entries yet.</p>
                                ) : (
                                    <div className="space-y-1 max-h-[500px] overflow-y-auto">
                                        {auditLog.map((a, i) => (
                                            <div key={a.audit_id || i} className="flex items-start gap-3 p-2 text-sm border-b last:border-0" data-testid={`audit-row-${i}`}>
                                                <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full mt-2 flex-shrink-0" />
                                                <div className="flex-1">
                                                    <p className="font-medium">{a.action?.replace(/_/g, ' ')}</p>
                                                    <p className="text-xs text-muted-foreground mt-0.5">
                                                        {a.user_name || 'System'} · {a.entity_type}{a.entity_id ? ` (${a.entity_id.substring(0, 16)}…)` : ''}
                                                        {a.timestamp && ` · ${new Date(a.timestamp).toLocaleString()}`}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* SECURITY POLICY TAB */}
                    <TabsContent value="security">
                        <Card>
                            <CardHeader>
                                <CardTitle>Company security policy</CardTitle>
                                <CardDescription>Enforce 2FA, session timeouts and password minimums across all staff in this company.</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {securityPolicy ? (
                                    <div className="space-y-4">
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                            <div className="p-3 rounded border">
                                                <p className="text-xs text-muted-foreground">Users</p>
                                                <p className="text-2xl font-semibold">{securityPolicy.stats.total_users}</p>
                                            </div>
                                            <div className="p-3 rounded border">
                                                <p className="text-xs text-muted-foreground">Admins</p>
                                                <p className="text-2xl font-semibold">{securityPolicy.stats.total_admins}</p>
                                            </div>
                                            <div className="p-3 rounded border">
                                                <p className="text-xs text-muted-foreground">2FA coverage</p>
                                                <p className="text-2xl font-semibold">{securityPolicy.stats.twofa_coverage_percent}%</p>
                                            </div>
                                        </div>
                                        <div className="space-y-3 pt-3 border-t">
                                            <div className="flex items-center justify-between p-3 rounded border">
                                                <div>
                                                    <p className="font-medium text-sm">Force 2FA for admins</p>
                                                    <p className="text-xs text-muted-foreground">Owners + admins must enable TOTP on next login.</p>
                                                </div>
                                                <Switch checked={securityPolicy.policy.force_2fa_for_admins} onCheckedChange={(c) => updateSecurityPolicy('force_2fa_for_admins', c)} data-testid="toggle-force-2fa-admins" />
                                            </div>
                                            <div className="flex items-center justify-between p-3 rounded border">
                                                <div>
                                                    <p className="font-medium text-sm">Force 2FA for all staff</p>
                                                    <p className="text-xs text-muted-foreground">Every user including employees must enable TOTP.</p>
                                                </div>
                                                <Switch checked={securityPolicy.policy.force_2fa_for_all} onCheckedChange={(c) => updateSecurityPolicy('force_2fa_for_all', c)} data-testid="toggle-force-2fa-all" />
                                            </div>
                                            <div className="grid grid-cols-2 gap-3">
                                                <div>
                                                    <Label className="text-xs">Session timeout (minutes)</Label>
                                                    <Input type="number" value={securityPolicy.policy.session_timeout_minutes} onChange={(e) => setSecurityPolicy({ ...securityPolicy, policy: { ...securityPolicy.policy, session_timeout_minutes: Number(e.target.value) } })} onBlur={(e) => updateSecurityPolicy('session_timeout_minutes', Number(e.target.value))} data-testid="input-session-timeout" />
                                                </div>
                                                <div>
                                                    <Label className="text-xs">Password min length</Label>
                                                    <Input type="number" value={securityPolicy.policy.password_min_length} onChange={(e) => setSecurityPolicy({ ...securityPolicy, policy: { ...securityPolicy.policy, password_min_length: Number(e.target.value) } })} onBlur={(e) => updateSecurityPolicy('password_min_length', Number(e.target.value))} data-testid="input-password-length" />
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ) : <Loader2 className="w-5 h-5 animate-spin" />}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* DATA EXPORT TAB */}
                    <TabsContent value="data">
                        <Card>
                            <CardHeader>
                                <CardTitle>Full company data export</CardTitle>
                                <CardDescription>Download a complete JSON of every record in your tenant — employees, payroll, leave, audits, compliance, policies, training, absence, performance, cases, GDPR records.</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                <div className="p-3 rounded border bg-amber-50 dark:bg-amber-950/20 border-amber-200 text-amber-900 dark:text-amber-100 text-sm">
                                    <strong>Note:</strong> Sensitive credentials (password hashes, 2FA secrets, backup codes) are intentionally excluded. The export is signed in your audit log.
                                </div>
                                <Button onClick={downloadCompanyData} disabled={exportLoading} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="company-export-btn">
                                    {exportLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
                                    Download full export (.json)
                                </Button>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* NOTIFICATIONS TAB */}
                    <TabsContent value="notifications">
                        <Card>
                            <CardHeader>
                                <CardTitle>Notifications & Alerts</CardTitle>
                                <CardDescription>
                                    Configure which events trigger notifications for your team.
                                    Notifications are sent in-app and optionally by email.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {[
                                    { label: 'UKVI alert raised', desc: 'When a new compliance alert is triggered for a visa holder' },
                                    { label: 'Visa expiry within 90 days', desc: 'Alert HR when an employee\'s visa is about to expire' },
                                    { label: 'Right to Work expiry within 60 days', desc: 'Remind HR to re-verify time-limited RTW documents' },
                                    { label: 'RTI submission accepted/rejected', desc: 'Notify payroll admin of HMRC response' },
                                    { label: 'New employee onboarding complete', desc: 'Alert HR when all readiness flags are green' },
                                    { label: 'Leave request pending approval', desc: 'Notify line managers of pending leave requests' },
                                ].map((item, i) => (
                                    <div key={i} className="flex items-center justify-between p-3 rounded-lg border">
                                        <div>
                                            <p className="text-sm font-medium">{item.label}</p>
                                            <p className="text-xs text-muted-foreground">{item.desc}</p>
                                        </div>
                                        <Switch defaultChecked={true} />
                                    </div>
                                ))}
                                <p className="text-xs text-muted-foreground mt-2">
                                    Full notification webhook configuration is available in Settings → Integrations.
                                </p>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* COMPANY SETTINGS TAB */}
                    <TabsContent value="company">
                        <Card>
                            <CardHeader>
                                <CardTitle>Company Settings</CardTitle>
                                <CardDescription>
                                    Core company configuration — HMRC references, payroll frequency, and compliance settings.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                                    {[
                                        { label: 'PAYE Reference', desc: 'Required for HMRC RTI submissions' },
                                        { label: 'Accounts Office Reference', desc: 'For employer payment summaries' },
                                        { label: 'Payroll Frequency', desc: 'Monthly, weekly, or bi-weekly' },
                                        { label: 'Sponsor Licence Number', desc: 'Required if you employ sponsored workers' },
                                        { label: 'Sponsor Licence Expiry', desc: 'Alert before expiry to avoid compliance gaps' },
                                        { label: 'Company Currency', desc: 'Default currency for salaries and payroll' },
                                    ].map((s, i) => (
                                        <div key={i} className="p-3 rounded-lg border bg-slate-50 dark:bg-slate-900/30">
                                            <p className="font-medium text-sm">{s.label}</p>
                                            <p className="text-xs text-muted-foreground mt-0.5">{s.desc}</p>
                                        </div>
                                    ))}
                                </div>
                                <p className="text-sm text-muted-foreground">
                                    Edit company settings in <strong>Settings → Company Profile</strong>.
                                </p>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* BILLING TAB */}
                    <TabsContent value="billing">
                        <Card>
                            <CardHeader>
                                <CardTitle>Billing & Subscription</CardTitle>
                                <CardDescription>Manage your subscription plan and view payment history.</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                    {[
                                        { label: 'Starter', price: '£29', employees: '10', features: 'Core HR, Payroll, UKVI Scanner' },
                                        { label: 'Professional', price: '£39', employees: '50', features: '+ HMRC RTI, UKVI Reports, Analytics' },
                                        { label: 'Enterprise', price: '£129', employees: 'Unlimited', features: '+ Multi-entity, SSO, Dedicated support' },
                                    ].map((plan) => (
                                        <div key={plan.label} className="p-4 rounded-lg border text-center">
                                            <p className="font-bold">{plan.label}</p>
                                            <p className="text-2xl font-bold text-indigo-600 mt-1">{plan.price}<span className="text-sm text-muted-foreground font-normal">/mo</span></p>
                                            <p className="text-xs text-muted-foreground mt-1">Up to {plan.employees} employees</p>
                                            <p className="text-xs text-muted-foreground mt-1">{plan.features}</p>
                                        </div>
                                    ))}
                                </div>
                                <div className="flex justify-start mt-2">
                                    <Button
                                        variant="outline"
                                        onClick={() => window.location.href = '/billing'}
                                    >
                                        <CreditCard className="w-4 h-4 mr-2" /> Go to full Billing page
                                    </Button>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    Payslip PDF downloads are £5 per payslip (preview free). UKVI scans: 2 per billing month on all plans.
                                </p>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* DANGER TAB */}
                    <TabsContent value="danger">
                        <Card className="border-rose-200 bg-rose-50/40 dark:bg-rose-950/20">
                            <CardHeader>
                                <div className="flex items-center gap-2">
                                    <AlertTriangle className="w-5 h-5 text-rose-600" />
                                    <CardTitle className="text-rose-900 dark:text-rose-100">Danger zone</CardTitle>
                                </div>
                                <CardDescription>Operations here are destructive and cannot be undone. Your password is required before any action proceeds.</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <DangerItem
                                    title="Run record retention"
                                    desc="Archive records older than HMRC 6-7 year windows to {collection}_archive, then delete from live collections."
                                    action={() => setDangerDialog({
                                        title: 'Run record retention',
                                        desc: 'Archive + delete records older than HMRC retention windows. This cannot be undone.',
                                        action: async () => {
                                            try {
                                                await axios.post(`${API_URL}/api/admin/retention/run?dry_run=false`, {}, {
                                                    headers: { Authorization: `Bearer ${token()}` }, withCredentials: true,
                                                });
                                                toast.success('Retention run complete');
                                            } catch (err) {
                                                toast.error(err.response?.data?.detail || 'Failed');
                                            }
                                        }
                                    })}
                                    buttonText="Run retention job"
                                />
                                <DangerItem
                                    title="Clear demo data"
                                    desc="Remove all seeded demo employees and payslips. Only affects records marked demo_seeded=true."
                                    action={() => setDangerDialog({
                                        title: 'Clear demo data',
                                        desc: 'Remove all demo-seeded employees, payslips and payroll records for this company.',
                                        action: async () => {
                                            try {
                                                await axios.post(`${API_URL}/api/demo/reset`, {}, {
                                                    headers: { Authorization: `Bearer ${token()}` }, withCredentials: true,
                                                });
                                                toast.success('Demo data cleared');
                                            } catch (err) {
                                                toast.error('Failed');
                                            }
                                        }
                                    })}
                                    buttonText="Clear demo"
                                />
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
            )}

            {/* DANGER ZONE RE-AUTH DIALOG */}
            {dangerDialog && (
                <DangerReauthDialog
                    open={!!dangerDialog}
                    onOpenChange={(open) => { if (!open) setDangerDialog(null); }}
                    title={dangerDialog.title}
                    desc={dangerDialog.desc}
                    onConfirmed={dangerDialog.action}
                    data-testid="danger-reauth-dialog"
                />
            )}

            {/* INVITE DIALOG */}
            <Dialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen}>
                <DialogContent data-testid="invite-dialog">
                    <DialogHeader>
                        <DialogTitle>Invite team member</DialogTitle>
                    </DialogHeader>
                    <form onSubmit={handleInvite} className="space-y-4">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label>Name</Label>
                                <Input value={inviteForm.name} onChange={(e) => setInviteForm({ ...inviteForm, name: e.target.value })} required data-testid="invite-name" />
                            </div>
                            <div>
                                <Label>Email</Label>
                                <Input type="email" value={inviteForm.email} onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })} required data-testid="invite-email" />
                            </div>
                        </div>
                        <div>
                            <Label>Role</Label>
                            <Select value={inviteForm.role} onValueChange={(v) => setInviteForm({ ...inviteForm, role: v })}>
                                <SelectTrigger data-testid="invite-role"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {ROLES.map((r) => (
                                        <SelectItem key={r.id} value={r.id}>
                                            <div>
                                                <div className="font-medium">{r.label}</div>
                                                <div className="text-xs text-muted-foreground">{r.desc}</div>
                                            </div>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setInviteDialogOpen(false)}>Cancel</Button>
                            <Button type="submit" disabled={sending} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="send-invite-btn">
                                {sending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
                                Send invitation
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
}

function DangerItem({ title, desc, action, buttonText }) {
    return (
        <div className="flex items-start justify-between gap-4 p-4 border rounded-lg bg-white dark:bg-slate-900">
            <div className="flex-1">
                <p className="font-semibold">{title}</p>
                <p className="text-xs text-muted-foreground mt-1">{desc}</p>
            </div>
            <Button variant="outline" className="border-rose-300 text-rose-700 hover:bg-rose-100 dark:hover:bg-rose-950/40" onClick={action}>
                {buttonText}
            </Button>
        </div>
    );
}
