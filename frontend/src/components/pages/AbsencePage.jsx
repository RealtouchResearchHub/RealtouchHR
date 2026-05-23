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
import { Thermometer, Plus, FileCheck2, Loader2, Activity } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }, withCredentials: true });

export default function AbsencePage() {
    const [tab, setTab] = useState('records');
    const [records, setRecords] = useState([]);
    const [bradford, setBradford] = useState(null);
    const [employees, setEmployees] = useState([]);
    const [dialog, setDialog] = useState(false);
    const [rtwDialog, setRtwDialog] = useState(null);
    const [form, setForm] = useState({ employee_id: '', start_date: '', end_date: '', reason: 'sickness', description: '', fit_note_url: '', self_certified: true });
    const [rtwNotes, setRtwNotes] = useState('');
    const [loading, setLoading] = useState(true);

    const load = async () => {
        setLoading(true);
        try {
            const [a, b, e] = await Promise.allSettled([
                axios.get(`${API_URL}/api/absence`, auth()),
                axios.get(`${API_URL}/api/absence/bradford`, auth()),
                axios.get(`${API_URL}/api/employees`, auth()),
            ]);
            if (a.status === 'fulfilled') setRecords(a.value.data.absences || []);
            if (b.status === 'fulfilled') setBradford(b.value.data);
            if (e.status === 'fulfilled') setEmployees(e.value.data?.employees || e.value.data || []);
        } catch (err) { /* ignore */ } finally { setLoading(false); }
    };
    useEffect(() => { load(); }, []);

    const submit = async () => {
        if (!form.employee_id || !form.start_date || !form.end_date) { toast.error('Employee + dates required'); return; }
        try {
            await axios.post(`${API_URL}/api/absence`, form, auth());
            toast.success('Logged');
            setDialog(false); setForm({ employee_id: '', start_date: '', end_date: '', reason: 'sickness', description: '', fit_note_url: '', self_certified: true });
            load();
        } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    };

    const submitRTW = async () => {
        if (!rtwNotes) { toast.error('Notes required'); return; }
        try {
            await axios.post(`${API_URL}/api/absence/${rtwDialog.absence_id}/return-to-work`, { notes: rtwNotes }, auth());
            toast.success('Return-to-work logged');
            setRtwDialog(null); setRtwNotes('');
            load();
        } catch (e) { toast.error('Failed'); }
    };

    const empName = (id) => {
        const e = employees.find((x) => x.employee_id === id);
        return e ? `${e.first_name} ${e.last_name}` : id;
    };

    const riskColor = (r) => ({ high: 'bg-red-100 text-red-700', medium: 'bg-amber-100 text-amber-700', low: 'bg-emerald-100 text-emerald-700' }[r]);

    return (
        <div className="space-y-6" data-testid="absence-page">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Absence & Sickness</h1>
                    <p className="text-muted-foreground mt-1">Track sickness, fit notes, return-to-work interviews and Bradford scores.</p>
                </div>
                <Button onClick={() => setDialog(true)} className="bg-indigo-600 hover:bg-indigo-700" data-testid="new-absence-btn"><Plus className="w-4 h-4 mr-1" /> Log absence</Button>
            </div>

            <Tabs value={tab} onValueChange={setTab}>
                <TabsList>
                    <TabsTrigger value="records" data-testid="tab-absence-records"><Activity className="w-4 h-4 mr-2" />Records ({records.length})</TabsTrigger>
                    <TabsTrigger value="bradford" data-testid="tab-bradford"><Thermometer className="w-4 h-4 mr-2" />Bradford Factor</TabsTrigger>
                </TabsList>

                <TabsContent value="records">
                    <Card>
                        <CardContent className="pt-6">
                            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : records.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No absences recorded.</p>
                            ) : (
                                <div className="space-y-2">
                                    {records.map((r) => (
                                        <div key={r.absence_id} className="p-3 border rounded-lg flex items-start justify-between">
                                            <div>
                                                <p className="font-medium">{empName(r.employee_id)}</p>
                                                <p className="text-xs text-muted-foreground">{r.start_date} → {r.end_date} · {r.duration_days} day(s) · {r.reason}</p>
                                                {r.description && <p className="text-sm mt-1">{r.description}</p>}
                                                <div className="flex gap-1 mt-1">
                                                    {r.fit_note_url && <Badge variant="outline">Fit note</Badge>}
                                                    {r.self_certified && <Badge variant="outline">Self-certified</Badge>}
                                                    <Badge className={r.return_to_work_done ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}>
                                                        {r.return_to_work_done ? 'RTW done' : 'RTW pending'}
                                                    </Badge>
                                                </div>
                                            </div>
                                            {!r.return_to_work_done && (
                                                <Button size="sm" variant="outline" onClick={() => setRtwDialog(r)} data-testid={`rtw-${r.absence_id}`}><FileCheck2 className="w-4 h-4 mr-1" /> RTW</Button>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="bradford">
                    <Card>
                        <CardHeader>
                            <CardTitle>Bradford Factor — rolling 12 months</CardTitle>
                            <CardDescription>Score = S² × D · S = episodes, D = days absent. Higher = more disruptive pattern.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {bradford && bradford.results.length > 0 ? (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead className="bg-muted text-left">
                                            <tr><th className="p-2">Employee</th><th className="p-2 text-right">Episodes</th><th className="p-2 text-right">Days</th><th className="p-2 text-right">Score</th><th className="p-2">Risk</th></tr>
                                        </thead>
                                        <tbody>
                                            {bradford.results.map((b) => (
                                                <tr key={b.employee_id} className="border-t">
                                                    <td className="p-2">{empName(b.employee_id)}</td>
                                                    <td className="p-2 text-right">{b.episodes}</td>
                                                    <td className="p-2 text-right">{b.days}</td>
                                                    <td className="p-2 text-right font-medium">{b.bradford_score}</td>
                                                    <td className="p-2"><Badge className={riskColor(b.risk)}>{b.risk}</Badge></td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : <p className="text-sm text-muted-foreground">No sickness data yet for the rolling 12 months.</p>}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            <Dialog open={dialog} onOpenChange={setDialog}>
                <DialogContent>
                    <DialogHeader><DialogTitle>Log absence</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div><Label>Employee</Label>
                            <Select value={form.employee_id} onValueChange={(v) => setForm({ ...form, employee_id: v })}>
                                <SelectTrigger><SelectValue placeholder="Pick employee" /></SelectTrigger>
                                <SelectContent>{employees.map((e) => <SelectItem key={e.employee_id} value={e.employee_id}>{e.first_name} {e.last_name}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            <div><Label>Start</Label><Input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></div>
                            <div><Label>End</Label><Input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></div>
                        </div>
                        <div><Label>Reason</Label>
                            <Select value={form.reason} onValueChange={(v) => setForm({ ...form, reason: v })}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>{['sickness', 'injury', 'medical_appointment', 'bereavement', 'other'].map((r) => <SelectItem key={r} value={r}>{r.replace('_', ' ')}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div><Label>Description</Label><Textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
                        <div><Label>Fit note URL</Label><Input value={form.fit_note_url} onChange={(e) => setForm({ ...form, fit_note_url: e.target.value })} placeholder="Link to uploaded fit note" /></div>
                    </div>
                    <DialogFooter><Button variant="outline" onClick={() => setDialog(false)}>Cancel</Button><Button onClick={submit} data-testid="create-absence-btn">Save</Button></DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={!!rtwDialog} onOpenChange={(o) => !o && setRtwDialog(null)}>
                <DialogContent>
                    <DialogHeader><DialogTitle>Return-to-work interview</DialogTitle></DialogHeader>
                    <div className="space-y-2">
                        <p className="text-sm">For: <strong>{rtwDialog ? empName(rtwDialog.employee_id) : ''}</strong></p>
                        <Textarea rows={4} placeholder="Summary of the conversation, any adjustments, follow-up actions..." value={rtwNotes} onChange={(e) => setRtwNotes(e.target.value)} data-testid="rtw-notes-input" />
                    </div>
                    <DialogFooter><Button variant="outline" onClick={() => setRtwDialog(null)}>Cancel</Button><Button onClick={submitRTW} data-testid="submit-rtw-btn">Log RTW</Button></DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
