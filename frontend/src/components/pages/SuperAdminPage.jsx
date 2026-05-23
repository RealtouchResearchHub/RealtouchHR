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
    Search, Loader2, Activity, Sparkles, Eye, PowerOff, Package, ToggleLeft, CreditCard, Save, X,
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function SuperAdminPage() {
    const { user } = useAuth();
    const [metrics, setMetrics] = useState(null);
    const [companies, setCompanies] = useState([]);
    const [auditLog, setAuditLog] = useState([]);
    const [plans, setPlans] = useState([]);
    const [moduleDialog, setModuleDialog] = useState(null);  // {company_id, name, modules}
    const [planDialog, setPlanDialog] = useState(null);       // selected plan
    const [planForm, setPlanForm] = useState({ plan_id: '', name: '', price: 0, employee_limit: 10, features: '' });
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [error, setError] = useState(null);
    const token = () => localStorage.getItem('token');

    const load = async () => {
        setLoading(true);
        try {
            const headers = { Authorization: `Bearer ${token()}` };
            const [mRes, cRes, aRes, pRes] = await Promise.all([
                axios.get(`${API_URL}/api/super-admin/metrics`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/super-admin/companies`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/super-admin/audit-log?limit=50`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/super-admin/plans`, { headers, withCredentials: true }),
            ]);
            setMetrics(mRes.data);
            setCompanies(cRes.data.companies || []);
            setAuditLog(aRes.data.audit_log || []);
            setPlans(pRes.data.plans || []);
            setError(null);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to load platform data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    const openModulesDialog = async (company_id, name) => {
        try {
            const headers = { Authorization: `Bearer ${token()}` };
            const res = await axios.get(`${API_URL}/api/super-admin/companies/${company_id}/modules`, { headers, withCredentials: true });
            setModuleDialog({ company_id, name, modules: res.data.modules });
        } catch (e) { toast.error('Failed to load modules'); }
    };

    const toggleModule = async (module_key, enabled) => {
        try {
            const headers = { Authorization: `Bearer ${token()}` };
            await axios.post(`${API_URL}/api/super-admin/companies/${moduleDialog.company_id}/modules`,
                { module_key, enabled }, { headers, withCredentials: true });
            setModuleDialog({ ...moduleDialog, modules: moduleDialog.modules.map((m) => m.key === module_key ? { ...m, enabled } : m) });
        } catch (e) { toast.error('Failed'); }
    };

    const openPlanEditor = (plan) => {
        setPlanForm({
            plan_id: plan.plan_id, name: plan.name, price: plan.price,
            employee_limit: plan.employee_limit, features: (plan.features || []).join('\n')
        });
        setPlanDialog(plan);
    };

    const savePlan = async () => {
        try {
            const headers = { Authorization: `Bearer ${token()}` };
            const features = planForm.features.split('\n').map((s) => s.trim()).filter(Boolean);
            await axios.put(`${API_URL}/api/super-admin/plans/${planForm.plan_id}`,
                { ...planForm, price: Number(planForm.price), employee_limit: Number(planForm.employee_limit), features, currency: 'gbp' },
                { headers, withCredentials: true });
            toast.success('Plan saved');
            setPlanDialog(null);
            load();
        } catch (e) { toast.error('Failed'); }
    };

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
                    <TabsTrigger value="plans" data-testid="tab-plans"><CreditCard className="w-4 h-4 mr-1" />Plans</TabsTrigger>
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
                                                    <Button size="sm" variant="outline" onClick={() => openModulesDialog(c.company_id, c.name)}
                                                        data-testid={`modules-${c.company_id}`} title="Modules">
                                                        <Package className="w-3.5 h-3.5" />
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

                <TabsContent value="plans">
                    <Card>
                        <CardHeader>
                            <CardTitle>Subscription Plans</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {plans.map((p) => (
                                    <Card key={p.plan_id} className="border-2" data-testid={`plan-card-${p.plan_id}`}>
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
                                            <Button size="sm" variant="outline" onClick={() => openPlanEditor(p)} data-testid={`edit-plan-${p.plan_id}`}>Edit price/features</Button>
                                        </CardContent>
                                    </Card>
                                ))}
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

            {/* Module toggle dialog */}
            <Dialog open={!!moduleDialog} onOpenChange={(o) => !o && setModuleDialog(null)}>
                <DialogContent className="max-w-lg">
                    <DialogHeader><DialogTitle>Modules · {moduleDialog?.name}</DialogTitle></DialogHeader>
                    <p className="text-xs text-muted-foreground">Disable modules for this tenant. Disabled modules are hidden from their sidebar and protected APIs return 403.</p>
                    <div className="space-y-2 max-h-[400px] overflow-y-auto" data-testid="module-toggle-list">
                        {(moduleDialog?.modules || []).map((m) => (
                            <div key={m.key} className="flex items-center justify-between p-2 border rounded">
                                <Label htmlFor={`mod-${m.key}`} className="text-sm cursor-pointer flex-1">{m.name}</Label>
                                <Switch id={`mod-${m.key}`} checked={m.enabled} onCheckedChange={(c) => toggleModule(m.key, c)} data-testid={`module-toggle-${m.key}`} />
                            </div>
                        ))}
                    </div>
                </DialogContent>
            </Dialog>

            {/* Plan editor dialog */}
            <Dialog open={!!planDialog} onOpenChange={(o) => !o && setPlanDialog(null)}>
                <DialogContent>
                    <DialogHeader><DialogTitle>Edit plan · {planForm.name}</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div><Label>Display name</Label><Input value={planForm.name} onChange={(e) => setPlanForm({ ...planForm, name: e.target.value })} /></div>
                        <div className="grid grid-cols-2 gap-2">
                            <div><Label>Price (£/month)</Label><Input type="number" step="0.01" value={planForm.price} onChange={(e) => setPlanForm({ ...planForm, price: e.target.value })} data-testid="plan-price-input" /></div>
                            <div><Label>Employee limit (-1 unlimited)</Label><Input type="number" value={planForm.employee_limit} onChange={(e) => setPlanForm({ ...planForm, employee_limit: e.target.value })} /></div>
                        </div>
                        <div><Label>Features (one per line)</Label>
                            <textarea className="w-full p-2 border rounded text-sm bg-background" rows={6} value={planForm.features} onChange={(e) => setPlanForm({ ...planForm, features: e.target.value })} />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setPlanDialog(null)}><X className="w-4 h-4 mr-1" />Cancel</Button>
                        <Button onClick={savePlan} data-testid="save-plan-btn"><Save className="w-4 h-4 mr-1" />Save</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
