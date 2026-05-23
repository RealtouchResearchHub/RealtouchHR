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
} from 'lucide-react';
import { Switch } from '../ui/switch';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const ROLES = [
    { id: 'admin', label: 'Administrator', desc: 'Full system access (except billing & ownership transfer)' },
    { id: 'hr_manager', label: 'HR Manager', desc: 'Manage employees, leave, documents, UKVI' },
    { id: 'payroll_admin', label: 'Payroll Admin', desc: 'Run payroll, manage RTI, compliance' },
    { id: 'manager', label: 'Line Manager', desc: 'Approve team leave and timesheets' },
    { id: 'employee', label: 'Employee', desc: 'Self-service access only' },
    { id: 'viewer', label: 'Viewer', desc: 'Read-only access' },
];

export default function AdminPortalPage() {
    const { user } = useAuth();
    const [users, setUsers] = useState([]);
    const [invites, setInvites] = useState([]);
    const [auditLog, setAuditLog] = useState([]);
    const [loading, setLoading] = useState(true);
    const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
    const [inviteForm, setInviteForm] = useState({ email: '', name: '', role: 'hr_manager' });
    const [securityPolicy, setSecurityPolicy] = useState(null);
    const [exportLoading, setExportLoading] = useState(false);
    const [sending, setSending] = useState(false);

    const token = () => localStorage.getItem('token');

    const fetchAll = async () => {
        setLoading(true);
        try {
            const headers = { Authorization: `Bearer ${token()}` };
            const [uRes, iRes, aRes, sRes] = await Promise.all([
                axios.get(`${API_URL}/api/users`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/users/invites`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/enterprise/audit-log?limit=50`, { headers, withCredentials: true }).catch(() => ({ data: { audit_log: [] } })),
                axios.get(`${API_URL}/api/company/security-policy`, { headers, withCredentials: true }).catch(() => null),
            ]);
            setUsers(uRes.data.users || []);
            setInvites(iRes.data.invites || []);
            setAuditLog(aRes.data.audit_log || aRes.data.logs || []);
            if (sRes) setSecurityPolicy(sRes.data);
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to load admin data');
        } finally {
            setLoading(false);
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
                <Tabs defaultValue="team" className="space-y-4">
                    <TabsList>
                        <TabsTrigger value="team" data-testid="tab-team"><Users className="w-4 h-4 mr-2" /> Team ({users.length})</TabsTrigger>
                        <TabsTrigger value="invites" data-testid="tab-invites"><Mail className="w-4 h-4 mr-2" /> Invites ({invites.filter(i => i.status === 'pending').length})</TabsTrigger>
                        <TabsTrigger value="audit" data-testid="tab-audit"><Activity className="w-4 h-4 mr-2" /> Audit Log</TabsTrigger>
                        <TabsTrigger value="security" data-testid="tab-security-policy"><Lock className="w-4 h-4 mr-2" /> Security</TabsTrigger>
                        <TabsTrigger value="data" data-testid="tab-data"><Download className="w-4 h-4 mr-2" /> Data export</TabsTrigger>
                        <TabsTrigger value="danger" data-testid="tab-danger"><AlertTriangle className="w-4 h-4 mr-2" /> Danger Zone</TabsTrigger>
                    </TabsList>

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

                    {/* DANGER TAB */}
                    <TabsContent value="danger">
                        <Card className="border-rose-200 bg-rose-50/40 dark:bg-rose-950/20">
                            <CardHeader>
                                <div className="flex items-center gap-2">
                                    <AlertTriangle className="w-5 h-5 text-rose-600" />
                                    <CardTitle className="text-rose-900 dark:text-rose-100">Danger zone</CardTitle>
                                </div>
                                <CardDescription>Operations here are destructive and cannot be undone.</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <DangerItem
                                    title="Run record retention"
                                    desc="Archive records older than HMRC 6-7 year windows to {collection}_archive, then delete from live collections."
                                    action={async () => {
                                        if (!window.confirm('Archive + delete records older than retention windows? This cannot be undone.')) return;
                                        try {
                                            await axios.post(`${API_URL}/api/admin/retention/run?dry_run=false`, {}, {
                                                headers: { Authorization: `Bearer ${token()}` }, withCredentials: true,
                                            });
                                            toast.success('Retention run complete');
                                        } catch (err) {
                                            toast.error(err.response?.data?.detail || 'Failed');
                                        }
                                    }}
                                    buttonText="Run retention job"
                                />
                                <DangerItem
                                    title="Clear demo data"
                                    desc="Remove all seeded demo employees and payslips. Only affects records marked demo_seeded=true."
                                    action={async () => {
                                        if (!window.confirm('Clear all demo data for this company?')) return;
                                        try {
                                            await axios.post(`${API_URL}/api/demo/reset`, {}, {
                                                headers: { Authorization: `Bearer ${token()}` }, withCredentials: true,
                                            });
                                            toast.success('Demo data cleared');
                                        } catch (err) {
                                            toast.error('Failed');
                                        }
                                    }}
                                    buttonText="Clear demo"
                                />
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
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
