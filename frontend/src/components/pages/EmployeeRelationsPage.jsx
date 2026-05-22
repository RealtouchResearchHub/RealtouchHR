import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../ui/dialog';
import { toast } from 'sonner';
import {
    Shield, FileText, AlertTriangle, Plus, Loader2, Eye,
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }, withCredentials: true });

export default function EmployeeRelationsPage() {
    const [employees, setEmployees] = useState([]);
    const [cases, setCases] = useState([]);
    const [types, setTypes] = useState({ case_types: [], statuses: [], severities: [] });
    const [loading, setLoading] = useState(true);
    const [createOpen, setCreateOpen] = useState(false);
    const [viewCase, setViewCase] = useState(null);
    const [form, setForm] = useState({
        employee_id: '', case_type: 'disciplinary', title: '', description: '',
        severity: '', incident_date: '', confidential: true,
    });
    const [error, setError] = useState(null);

    const load = async () => {
        try {
            const [eRes, cRes, tRes] = await Promise.all([
                axios.get(`${API_URL}/api/employees`, auth()),
                axios.get(`${API_URL}/api/cases`, auth()),
                axios.get(`${API_URL}/api/cases/types`, auth()),
            ]);
            setEmployees(eRes.data || []);
            setCases(cRes.data.cases || []);
            setTypes(tRes.data || {});
            setError(null);
        } catch (err) {
            const detail = err.response?.data?.detail || 'Failed to load cases';
            if (err.response?.status === 403) setError(detail);
            else toast.error(detail);
        } finally {
            setLoading(false);
        }
    };
    useEffect(() => { load(); }, []);

    const create = async (e) => {
        e.preventDefault();
        try {
            await axios.post(`${API_URL}/api/cases`, form, auth());
            toast.success('Case created');
            setCreateOpen(false);
            setForm({ employee_id: '', case_type: 'disciplinary', title: '', description: '', severity: '', incident_date: '', confidential: true });
            load();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed');
        }
    };

    const closeCase = async (case_id) => {
        const outcome = window.prompt('Outcome / decision (required to close):');
        if (!outcome) return;
        try {
            await axios.post(`${API_URL}/api/cases/${case_id}/close`, { outcome }, auth());
            toast.success('Case closed');
            setViewCase(null);
            load();
        } catch (err) {
            toast.error('Failed to close');
        }
    };

    const empName = (id) => {
        const e = employees.find(x => x.employee_id === id);
        return e ? `${e.first_name} ${e.last_name}` : id;
    };

    if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-indigo-600" /></div>;

    if (error) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Card className="max-w-md">
                    <CardContent className="p-8 text-center">
                        <Shield className="w-12 h-12 text-rose-500 mx-auto mb-3" />
                        <h3 className="text-xl font-bold">Access restricted</h3>
                        <p className="text-muted-foreground mt-2 text-sm">{error}</p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="space-y-6" data-testid="er-page">
            <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Employee Relations</h1>
                    <p className="text-muted-foreground mt-1">Disciplinary cases, grievances, and investigations — confidential by default.</p>
                </div>
                <Button onClick={() => setCreateOpen(true)} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="new-case-btn">
                    <Plus className="w-4 h-4 mr-2" /> New case
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Shield className="w-5 h-5 text-indigo-600" /> Open & closed cases ({cases.length})
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {!cases.length ? <p className="text-center py-8 text-muted-foreground">No cases yet.</p> : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b text-xs uppercase tracking-wider text-muted-foreground">
                                        <th className="text-left p-2">Case</th>
                                        <th className="text-left p-2">Employee</th>
                                        <th className="text-left p-2">Type</th>
                                        <th className="text-left p-2">Severity</th>
                                        <th className="text-left p-2">Status</th>
                                        <th className="text-left p-2">Created</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {cases.map((c) => (
                                        <tr key={c.case_id} className="border-b hover:bg-accent/50" data-testid={`case-row-${c.case_id}`}>
                                            <td className="p-2 font-mono text-xs">{c.case_number}</td>
                                            <td className="p-2">{empName(c.employee_id)}</td>
                                            <td className="p-2 capitalize">{c.case_type.replace(/_/g, ' ')}</td>
                                            <td className="p-2">{c.severity ? <Badge variant="outline">{c.severity.replace(/_/g, ' ')}</Badge> : '—'}</td>
                                            <td className="p-2">
                                                <Badge className={
                                                    c.status === 'closed' ? 'bg-slate-100 text-slate-700'
                                                    : c.status === 'investigating' ? 'bg-amber-100 text-amber-700'
                                                    : 'bg-indigo-100 text-indigo-700'
                                                }>{c.status.replace(/_/g, ' ').toUpperCase()}</Badge>
                                            </td>
                                            <td className="p-2 text-xs text-muted-foreground">{c.created_at?.slice(0, 10)}</td>
                                            <td className="p-2 text-right">
                                                <Button size="sm" variant="outline" onClick={() => setViewCase(c)} data-testid={`view-${c.case_id}`}>
                                                    <Eye className="w-3.5 h-3.5" />
                                                </Button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Create dialog */}
            <Dialog open={createOpen} onOpenChange={setCreateOpen}>
                <DialogContent data-testid="case-dialog">
                    <DialogHeader><DialogTitle>New case</DialogTitle></DialogHeader>
                    <form onSubmit={create} className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label>Employee</Label>
                                <Select value={form.employee_id} onValueChange={(v) => setForm({ ...form, employee_id: v })}>
                                    <SelectTrigger data-testid="case-employee"><SelectValue placeholder="Choose…" /></SelectTrigger>
                                    <SelectContent>{employees.map(e => <SelectItem key={e.employee_id} value={e.employee_id}>{e.first_name} {e.last_name}</SelectItem>)}</SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label>Type</Label>
                                <Select value={form.case_type} onValueChange={(v) => setForm({ ...form, case_type: v })}>
                                    <SelectTrigger data-testid="case-type"><SelectValue /></SelectTrigger>
                                    <SelectContent>{(types.case_types || []).map(t => <SelectItem key={t} value={t}>{t.replace(/_/g, ' ')}</SelectItem>)}</SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div><Label>Title</Label><Input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} data-testid="case-title" /></div>
                        <div><Label>Description</Label><Textarea required rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label>Severity (optional)</Label>
                                <Select value={form.severity} onValueChange={(v) => setForm({ ...form, severity: v })}>
                                    <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                                    <SelectContent>{(types.severities || []).map(s => <SelectItem key={s} value={s}>{s.replace(/_/g, ' ')}</SelectItem>)}</SelectContent>
                                </Select>
                            </div>
                            <div><Label>Incident date</Label><Input type="date" value={form.incident_date} onChange={(e) => setForm({ ...form, incident_date: e.target.value })} /></div>
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
                            <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="save-case-btn">Create case</Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* View dialog */}
            <Dialog open={!!viewCase} onOpenChange={(v) => !v && setViewCase(null)}>
                <DialogContent className="max-w-2xl" data-testid="case-view-dialog">
                    {viewCase && (
                        <>
                            <DialogHeader>
                                <DialogTitle className="flex items-center gap-2">
                                    <FileText className="w-5 h-5" /> {viewCase.case_number}
                                </DialogTitle>
                            </DialogHeader>
                            <div className="space-y-3 text-sm">
                                <div className="grid grid-cols-2 gap-3">
                                    <div><strong>Employee:</strong> {empName(viewCase.employee_id)}</div>
                                    <div><strong>Type:</strong> {viewCase.case_type}</div>
                                    <div><strong>Severity:</strong> {viewCase.severity || '—'}</div>
                                    <div><strong>Status:</strong> {viewCase.status}</div>
                                </div>
                                <div>
                                    <strong>Title:</strong> {viewCase.title}
                                </div>
                                <div className="p-3 bg-slate-50 dark:bg-slate-900/30 rounded">
                                    {viewCase.description}
                                </div>
                                {viewCase.outcome && (
                                    <div className="p-3 bg-emerald-50 dark:bg-emerald-950/30 rounded border-l-4 border-emerald-500">
                                        <strong>Outcome:</strong> {viewCase.outcome}
                                    </div>
                                )}
                                {viewCase.events && viewCase.events.length > 0 && (
                                    <div>
                                        <strong>Timeline:</strong>
                                        <div className="mt-1 space-y-1">
                                            {viewCase.events.map((e) => (
                                                <div key={e.event_id} className="text-xs border-l-2 pl-2">
                                                    <span className="text-muted-foreground">{new Date(e.timestamp).toLocaleString()}</span>: {e.title}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                            <DialogFooter>
                                <Button variant="outline" onClick={() => setViewCase(null)}>Close</Button>
                                {viewCase.status !== 'closed' && (
                                    <Button className="bg-rose-600 hover:bg-rose-700 text-white"
                                        onClick={() => closeCase(viewCase.case_id)}
                                        data-testid="close-case-btn">
                                        <AlertTriangle className="w-4 h-4 mr-2" /> Close case
                                    </Button>
                                )}
                            </DialogFooter>
                        </>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
