import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../ui/select';
import { toast } from 'sonner';
import { FileSearch, AlertOctagon, Building2, ClipboardList, Plus, Loader2, Clock, ShieldAlert } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }, withCredentials: true });

export default function DPOCenterPage() {
    const [tab, setTab] = useState('dpa');
    const [dpas, setDpas] = useState([]);
    const [dsars, setDsars] = useState([]);
    const [breaches, setBreaches] = useState([]);
    const [processors, setProcessors] = useState([]);
    const [retention, setRetention] = useState(null);
    const [dialog, setDialog] = useState(null);
    const [form, setForm] = useState({});
    const [loading, setLoading] = useState(true);

    const load = async () => {
        setLoading(true);
        try {
            const [a, b, c, d, e] = await Promise.allSettled([
                axios.get(`${API_URL}/api/dpo/processing-activities`, auth()),
                axios.get(`${API_URL}/api/dpo/dsar`, auth()),
                axios.get(`${API_URL}/api/dpo/breaches`, auth()),
                axios.get(`${API_URL}/api/dpo/processors`, auth()),
                axios.get(`${API_URL}/api/dpo/retention-schedule`, auth()),
            ]);
            if (a.status === 'fulfilled') setDpas(a.value.data.activities || []);
            if (b.status === 'fulfilled') setDsars(b.value.data.requests || []);
            if (c.status === 'fulfilled') setBreaches(c.value.data.breaches || []);
            if (d.status === 'fulfilled') setProcessors(d.value.data.processors || []);
            if (e.status === 'fulfilled') setRetention(e.value.data);
        } catch (err) { /* ignore */ }
        finally { setLoading(false); }
    };
    useEffect(() => { load(); }, []);

    const submit = async () => {
        try {
            let endpoint = '';
            let payload = { ...form };
            if (dialog === 'dpa') endpoint = '/api/dpo/processing-activities';
            else if (dialog === 'dsar') endpoint = '/api/dpo/dsar';
            else if (dialog === 'breach') endpoint = '/api/dpo/breaches';
            else if (dialog === 'processor') endpoint = '/api/dpo/processors';
            await axios.post(`${API_URL}${endpoint}`, payload, auth());
            toast.success('Created');
            setDialog(null); setForm({});
            load();
        } catch (e) {
            toast.error(e.response?.data?.detail || 'Failed');
        }
    };

    const updateDsar = async (dsar_id, status) => {
        try {
            await axios.post(`${API_URL}/api/dpo/dsar/${dsar_id}/update`, { status }, auth());
            toast.success('Updated');
            load();
        } catch (e) { toast.error('Failed'); }
    };

    return (
        <div className="space-y-6" data-testid="dpo-center-page">
            <div>
                <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Data Protection — Compliance Register</h1>
                <p className="text-muted-foreground mt-1">Article 30 records, DSAR tracker, breach register, processor list, and retention schedule.</p>
            </div>

            <Tabs value={tab} onValueChange={setTab}>
                <TabsList>
                    <TabsTrigger value="dpa" data-testid="tab-dpa"><ClipboardList className="w-4 h-4 mr-2" />Processing Activities</TabsTrigger>
                    <TabsTrigger value="dsar" data-testid="tab-dsar"><FileSearch className="w-4 h-4 mr-2" />DSAR Tracker</TabsTrigger>
                    <TabsTrigger value="breach" data-testid="tab-breach"><AlertOctagon className="w-4 h-4 mr-2" />Breaches</TabsTrigger>
                    <TabsTrigger value="processors" data-testid="tab-processors"><Building2 className="w-4 h-4 mr-2" />Processors</TabsTrigger>
                    <TabsTrigger value="retention" data-testid="tab-retention"><Clock className="w-4 h-4 mr-2" />Retention</TabsTrigger>
                </TabsList>

                {/* DPA — Article 30 */}
                <TabsContent value="dpa">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div><CardTitle>Data Processing Activities</CardTitle><CardDescription>UK GDPR Article 30 record of all processing.</CardDescription></div>
                            <Button onClick={() => { setForm({ activity_name: '', purpose: '', legal_basis: 'contract', data_categories: [], data_subjects: [], retention_period: '', recipients: [] }); setDialog('dpa'); }} data-testid="new-dpa-btn"><Plus className="w-4 h-4 mr-1" /> Add</Button>
                        </CardHeader>
                        <CardContent>
                            {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : dpas.length === 0 ? <p className="text-sm text-muted-foreground">No activities recorded.</p> : (
                                <div className="space-y-2">
                                    {dpas.map((a) => (
                                        <div key={a.dpa_id} className="p-3 border rounded-lg">
                                            <p className="font-medium">{a.activity_name}</p>
                                            <p className="text-xs text-muted-foreground mt-1">{a.purpose}</p>
                                            <div className="flex flex-wrap gap-1 mt-2">
                                                <Badge variant="outline">Basis: {a.legal_basis}</Badge>
                                                {a.retention_period && <Badge variant="outline">Retain: {a.retention_period}</Badge>}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* DSAR */}
                <TabsContent value="dsar">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div><CardTitle>Subject Access Requests</CardTitle><CardDescription>Statutory 30-day response window per UK GDPR Article 12.</CardDescription></div>
                            <Button onClick={() => { setForm({ subject_email: '', subject_name: '', request_type: 'access', description: '' }); setDialog('dsar'); }} data-testid="new-dsar-btn"><Plus className="w-4 h-4 mr-1" /> Log DSAR</Button>
                        </CardHeader>
                        <CardContent>
                            {dsars.length === 0 ? <p className="text-sm text-muted-foreground">No DSARs logged.</p> : (
                                <div className="space-y-2" data-testid="dsar-list">
                                    {dsars.map((r) => (
                                        <div key={r.dsar_id} className="p-3 border rounded-lg flex items-start justify-between">
                                            <div className="flex-1">
                                                <p className="font-medium">{r.subject_name || r.subject_email}</p>
                                                <p className="text-xs text-muted-foreground">{r.subject_email} · {r.request_type}</p>
                                                {r.description && <p className="text-sm mt-1">{r.description}</p>}
                                                <div className="flex flex-wrap gap-1 mt-1">
                                                    <Badge className={r.status === 'completed' ? 'bg-emerald-100 text-emerald-700' : r.status === 'open' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100'}>{r.status}</Badge>
                                                    {r.overdue && <Badge className="bg-red-100 text-red-700">OVERDUE</Badge>}
                                                    {!r.overdue && r.status === 'open' && r.days_to_deadline !== null && <Badge variant="outline">{r.days_to_deadline} days left</Badge>}
                                                </div>
                                            </div>
                                            {r.status === 'open' && (
                                                <div className="flex gap-1">
                                                    <Button size="sm" variant="outline" onClick={() => updateDsar(r.dsar_id, 'in_progress')}>In progress</Button>
                                                    <Button size="sm" variant="default" onClick={() => updateDsar(r.dsar_id, 'completed')} data-testid={`dsar-complete-${r.dsar_id}`}>Complete</Button>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Breach */}
                <TabsContent value="breach">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div><CardTitle>Breach Incident Register</CardTitle><CardDescription>UK GDPR Article 33 — ICO must be notified within 72 hours of detection (where required).</CardDescription></div>
                            <Button onClick={() => { setForm({ title: '', description: '', severity: 'medium', discovered_at: new Date().toISOString().slice(0,10), affected_data_subjects: '', affected_data_categories: [], mitigation_steps: '' }); setDialog('breach'); }} data-testid="new-breach-btn"><Plus className="w-4 h-4 mr-1" /> Log breach</Button>
                        </CardHeader>
                        <CardContent>
                            {breaches.length === 0 ? <p className="text-sm text-muted-foreground">No breaches recorded.</p> : (
                                <div className="space-y-2">
                                    {breaches.map((b) => (
                                        <div key={b.breach_id} className="p-3 border rounded-lg">
                                            <div className="flex items-start justify-between">
                                                <div>
                                                    <p className="font-medium flex items-center gap-2"><ShieldAlert className="w-4 h-4 text-red-500" /> {b.title}</p>
                                                    <p className="text-xs text-muted-foreground mt-1">Discovered: {b.discovered_at} · ICO 72h deadline: {b.ico_72h_deadline?.slice(0,16)?.replace('T',' ')}</p>
                                                    <p className="text-sm mt-2">{b.description}</p>
                                                </div>
                                                <Badge className={b.severity === 'critical' ? 'bg-red-200 text-red-900' : b.severity === 'high' ? 'bg-red-100 text-red-700' : b.severity === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100'}>{b.severity}</Badge>
                                            </div>
                                            <div className="mt-2 flex flex-wrap gap-1">
                                                <Badge variant="outline">{b.status}</Badge>
                                                <Badge variant={b.ico_notified ? 'default' : 'outline'}>{b.ico_notified ? 'ICO notified' : 'ICO not notified'}</Badge>
                                                <Badge variant={b.individuals_notified ? 'default' : 'outline'}>{b.individuals_notified ? 'Individuals notified' : 'Not notified'}</Badge>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Processors */}
                <TabsContent value="processors">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div><CardTitle>Processors & Sub-processors</CardTitle><CardDescription>Third parties processing personal data on your behalf.</CardDescription></div>
                            <Button onClick={() => { setForm({ name: '', purpose: '', country: '', contact_email: '', data_categories: [], dpa_signed: false, sub_processors: [] }); setDialog('processor'); }} data-testid="new-processor-btn"><Plus className="w-4 h-4 mr-1" /> Add</Button>
                        </CardHeader>
                        <CardContent>
                            {processors.length === 0 ? <p className="text-sm text-muted-foreground">No processors recorded.</p> : (
                                <div className="space-y-2">
                                    {processors.map((p) => (
                                        <div key={p.processor_id} className="p-3 border rounded-lg">
                                            <p className="font-medium">{p.name}</p>
                                            <p className="text-xs text-muted-foreground">{p.purpose}{p.country ? ` · ${p.country}` : ''}</p>
                                            <div className="flex gap-1 mt-1">
                                                <Badge variant={p.dpa_signed ? 'default' : 'outline'}>{p.dpa_signed ? 'DPA signed' : 'DPA pending'}</Badge>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Retention */}
                <TabsContent value="retention">
                    <Card>
                        <CardHeader>
                            <CardTitle>Retention Schedule</CardTitle>
                            <CardDescription>Default UK statutory retention periods for HR records.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {retention ? (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead className="bg-muted text-left">
                                            <tr><th className="p-2">Category</th><th className="p-2">Retention</th><th className="p-2">Legal basis</th></tr>
                                        </thead>
                                        <tbody>
                                            {retention.defaults.map((r, i) => (
                                                <tr key={i} className="border-t"><td className="p-2">{r.category}</td><td className="p-2 font-medium">{r.retention}</td><td className="p-2 text-xs text-muted-foreground">{r.basis}</td></tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : <Loader2 className="w-5 h-5 animate-spin" />}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* Dialogs */}
            <Dialog open={!!dialog} onOpenChange={(o) => !o && setDialog(null)}>
                <DialogContent className="max-w-lg">
                    <DialogHeader><DialogTitle className="capitalize">New {dialog}</DialogTitle></DialogHeader>
                    {dialog === 'dpa' && (
                        <div className="space-y-2">
                            <Input placeholder="Activity name" value={form.activity_name || ''} onChange={(e) => setForm({ ...form, activity_name: e.target.value })} />
                            <Textarea placeholder="Purpose" rows={2} value={form.purpose || ''} onChange={(e) => setForm({ ...form, purpose: e.target.value })} />
                            <Select value={form.legal_basis || 'contract'} onValueChange={(v) => setForm({ ...form, legal_basis: v })}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {['consent','contract','legal_obligation','vital_interests','public_task','legitimate_interests'].map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
                                </SelectContent>
                            </Select>
                            <Input placeholder="Retention period" value={form.retention_period || ''} onChange={(e) => setForm({ ...form, retention_period: e.target.value })} />
                        </div>
                    )}
                    {dialog === 'dsar' && (
                        <div className="space-y-2">
                            <Input placeholder="Subject email" value={form.subject_email || ''} onChange={(e) => setForm({ ...form, subject_email: e.target.value })} />
                            <Input placeholder="Subject name" value={form.subject_name || ''} onChange={(e) => setForm({ ...form, subject_name: e.target.value })} />
                            <Select value={form.request_type || 'access'} onValueChange={(v) => setForm({ ...form, request_type: v })}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {['access','rectification','erasure','portability','restriction','objection'].map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                                </SelectContent>
                            </Select>
                            <Textarea placeholder="Description" rows={2} value={form.description || ''} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                        </div>
                    )}
                    {dialog === 'breach' && (
                        <div className="space-y-2">
                            <Input placeholder="Title" value={form.title || ''} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                            <Textarea placeholder="Description" rows={3} value={form.description || ''} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                            <Select value={form.severity || 'medium'} onValueChange={(v) => setForm({ ...form, severity: v })}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>{['low','medium','high','critical'].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                            </Select>
                            <Input type="date" value={form.discovered_at || ''} onChange={(e) => setForm({ ...form, discovered_at: e.target.value })} />
                        </div>
                    )}
                    {dialog === 'processor' && (
                        <div className="space-y-2">
                            <Input placeholder="Processor name" value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                            <Input placeholder="Purpose" value={form.purpose || ''} onChange={(e) => setForm({ ...form, purpose: e.target.value })} />
                            <Input placeholder="Country" value={form.country || ''} onChange={(e) => setForm({ ...form, country: e.target.value })} />
                            <Input placeholder="Contact email" value={form.contact_email || ''} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} />
                        </div>
                    )}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDialog(null)}>Cancel</Button>
                        <Button onClick={submit} data-testid="dpo-submit-btn">Save</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
