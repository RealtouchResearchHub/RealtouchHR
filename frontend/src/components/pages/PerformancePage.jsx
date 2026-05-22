import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../ui/dialog';
import { toast } from 'sonner';
import { Target, ClipboardCheck, MessageSquare, Plus, Loader2, Scale } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }, withCredentials: true });

const RATINGS = [
    { id: 'exceeds', label: 'Exceeds expectations' },
    { id: 'meets', label: 'Meets expectations' },
    { id: 'partial', label: 'Partially meets' },
    { id: 'below', label: 'Below expectations' },
];

export default function PerformancePage() {
    const [employees, setEmployees] = useState([]);
    const [appraisals, setAppraisals] = useState([]);
    const [objectives, setObjectives] = useState([]);
    const [notes, setNotes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [objDialog, setObjDialog] = useState(false);
    const [apprDialog, setApprDialog] = useState(false);
    const [noteDialog, setNoteDialog] = useState(false);
    const [objForm, setObjForm] = useState({ employee_id: '', title: '', description: '', target_date: '', weight: 100 });
    const [apprForm, setApprForm] = useState({ employee_id: '', cycle: '2025-Annual', period_start: '', period_end: '', overall_rating: '', manager_assessment: '' });
    const [noteForm, setNoteForm] = useState({ employee_id: '', note_type: 'one_on_one', title: '', content: '', private: false });
    const [biasScan, setBiasScan] = useState(null);
    const [scanLoading, setScanLoading] = useState(false);

    const runBiasScan = async () => {
        setScanLoading(true);
        try {
            const res = await axios.get(`${API_URL}/api/fairness/appraisals/bias-scan`, auth());
            setBiasScan(res.data);
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Bias scan failed');
        } finally { setScanLoading(false); }
    };

    const load = async () => {
        try {
            const [eRes, aRes, oRes, nRes] = await Promise.all([
                axios.get(`${API_URL}/api/employees`, auth()),
                axios.get(`${API_URL}/api/performance/appraisals`, auth()),
                axios.get(`${API_URL}/api/performance/objectives`, auth()),
                axios.get(`${API_URL}/api/performance/notes`, auth()),
            ]);
            setEmployees(eRes.data || []);
            setAppraisals(aRes.data.appraisals || []);
            setObjectives(oRes.data.objectives || []);
            setNotes(nRes.data.notes || []);
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to load performance data');
        } finally {
            setLoading(false);
        }
    };
    useEffect(() => { load(); }, []);

    const createObjective = async (e) => {
        e.preventDefault();
        try {
            await axios.post(`${API_URL}/api/performance/objectives`, objForm, auth());
            toast.success('Objective created');
            setObjDialog(false);
            setObjForm({ employee_id: '', title: '', description: '', target_date: '', weight: 100 });
            load();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed');
        }
    };

    const createAppraisal = async (e) => {
        e.preventDefault();
        try {
            await axios.post(`${API_URL}/api/performance/appraisals`, apprForm, auth());
            toast.success('Appraisal created');
            setApprDialog(false);
            load();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed');
        }
    };

    const createNote = async (e) => {
        e.preventDefault();
        try {
            await axios.post(`${API_URL}/api/performance/notes`, noteForm, auth());
            toast.success('Note added');
            setNoteDialog(false);
            setNoteForm({ employee_id: '', note_type: 'one_on_one', title: '', content: '', private: false });
            load();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed');
        }
    };

    const updateObjectiveProgress = async (id, progress) => {
        try {
            await axios.put(`${API_URL}/api/performance/objectives/${id}`, { progress }, auth());
            load();
        } catch (err) { /* ignore */ }
    };

    if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-indigo-600" /></div>;

    const empName = (id) => {
        const e = employees.find(x => x.employee_id === id);
        return e ? `${e.first_name} ${e.last_name}` : id;
    };

    return (
        <div className="space-y-6" data-testid="performance-page">
            <div>
                <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Performance Management</h1>
                <p className="text-muted-foreground mt-1">Appraisals, SMART objectives, and 1-on-1 review notes.</p>
            </div>

            <Tabs defaultValue="objectives">
                <TabsList>
                    <TabsTrigger value="objectives" data-testid="tab-objectives"><Target className="w-4 h-4 mr-2" /> Objectives ({objectives.length})</TabsTrigger>
                    <TabsTrigger value="appraisals" data-testid="tab-appraisals"><ClipboardCheck className="w-4 h-4 mr-2" /> Appraisals ({appraisals.length})</TabsTrigger>
                    <TabsTrigger value="notes" data-testid="tab-notes"><MessageSquare className="w-4 h-4 mr-2" /> Notes ({notes.length})</TabsTrigger>
                    <TabsTrigger value="fairness" data-testid="tab-fairness"><Scale className="w-4 h-4 mr-2" /> Fairness</TabsTrigger>
                </TabsList>

                <TabsContent value="objectives">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle>SMART Objectives</CardTitle>
                            <Button onClick={() => setObjDialog(true)} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="add-objective-btn">
                                <Plus className="w-4 h-4 mr-2" /> Add objective
                            </Button>
                        </CardHeader>
                        <CardContent>
                            {!objectives.length ? <p className="text-center py-8 text-muted-foreground">No objectives yet.</p> : (
                                <div className="space-y-2">
                                    {objectives.map((o) => (
                                        <div key={o.objective_id} className="p-3 border rounded-lg" data-testid={`obj-${o.objective_id}`}>
                                            <div className="flex items-start justify-between gap-3">
                                                <div className="flex-1">
                                                    <p className="font-medium">{o.title}</p>
                                                    <p className="text-xs text-muted-foreground mt-0.5">
                                                        {empName(o.employee_id)} · weight {o.weight}% · target {o.target_date || 'no date'}
                                                    </p>
                                                    {o.description && <p className="text-sm mt-1">{o.description}</p>}
                                                </div>
                                                <Badge className={
                                                    o.status === 'completed' ? 'bg-emerald-100 text-emerald-700'
                                                    : o.status === 'cancelled' ? 'bg-slate-100 text-slate-700'
                                                    : 'bg-indigo-100 text-indigo-700'
                                                }>{o.status.toUpperCase()}</Badge>
                                            </div>
                                            <div className="mt-2">
                                                <div className="flex justify-between text-xs mb-1">
                                                    <span>Progress</span><span>{o.progress}%</span>
                                                </div>
                                                <input type="range" min="0" max="100" value={o.progress}
                                                    onChange={(e) => updateObjectiveProgress(o.objective_id, parseInt(e.target.value))}
                                                    className="w-full" data-testid={`progress-${o.objective_id}`} />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="appraisals">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle>Appraisals</CardTitle>
                            <Button onClick={() => setApprDialog(true)} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="add-appraisal-btn">
                                <Plus className="w-4 h-4 mr-2" /> New appraisal
                            </Button>
                        </CardHeader>
                        <CardContent>
                            {!appraisals.length ? <p className="text-center py-8 text-muted-foreground">No appraisals yet.</p> : (
                                <div className="space-y-2">
                                    {appraisals.map((a) => (
                                        <div key={a.appraisal_id} className="p-3 border rounded-lg" data-testid={`appr-${a.appraisal_id}`}>
                                            <div className="flex justify-between items-start gap-3">
                                                <div className="flex-1">
                                                    <p className="font-medium">{empName(a.employee_id)} — {a.cycle}</p>
                                                    <p className="text-xs text-muted-foreground mt-0.5">{a.period_start} → {a.period_end}</p>
                                                    {a.manager_assessment && <p className="text-sm mt-1 line-clamp-2">{a.manager_assessment}</p>}
                                                </div>
                                                <div className="flex flex-col items-end gap-1">
                                                    {a.overall_rating && (
                                                        <Badge className={
                                                            a.overall_rating === 'exceeds' ? 'bg-emerald-100 text-emerald-700'
                                                            : a.overall_rating === 'meets' ? 'bg-blue-100 text-blue-700'
                                                            : a.overall_rating === 'partial' ? 'bg-amber-100 text-amber-700'
                                                            : 'bg-rose-100 text-rose-700'
                                                        }>{a.overall_rating.toUpperCase()}</Badge>
                                                    )}
                                                    <Badge variant="outline">{a.status.toUpperCase()}</Badge>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="notes">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle>Review notes</CardTitle>
                            <Button onClick={() => setNoteDialog(true)} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="add-note-btn">
                                <Plus className="w-4 h-4 mr-2" /> Add note
                            </Button>
                        </CardHeader>
                        <CardContent>
                            {!notes.length ? <p className="text-center py-8 text-muted-foreground">No notes yet.</p> : (
                                <div className="space-y-2">
                                    {notes.map((n) => (
                                        <div key={n.note_id} className="p-3 border rounded-lg" data-testid={`note-${n.note_id}`}>
                                            <div className="flex items-start justify-between gap-3">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2">
                                                        <p className="font-medium">{n.title}</p>
                                                        {n.private && <Badge variant="outline" className="text-xs">PRIVATE</Badge>}
                                                    </div>
                                                    <p className="text-xs text-muted-foreground mt-0.5">
                                                        {empName(n.employee_id)} · by {n.author_name} · {n.note_type}
                                                    </p>
                                                    <p className="text-sm mt-2">{n.content}</p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="fairness">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle>Equality Act 2010 — Bias Scan</CardTitle>
                                <p className="text-xs text-muted-foreground mt-1">Detects rating distribution bias across protected characteristics using the 80% rule.</p>
                            </div>
                            <Button onClick={runBiasScan} disabled={scanLoading} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="run-bias-scan-btn">
                                {scanLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Scale className="w-4 h-4 mr-2" />}
                                Run scan
                            </Button>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {!biasScan ? (
                                <p className="text-center py-6 text-muted-foreground">Click "Run scan" to analyse current appraisal data for potential bias.</p>
                            ) : (
                                <>
                                    <div className="flex items-center gap-2 text-sm">
                                        <span>Total appraisals scanned: <strong>{biasScan.total_appraisals}</strong></span>
                                        <span className="text-muted-foreground">·</span>
                                        <span className="text-muted-foreground">{biasScan.method}</span>
                                    </div>
                                    <div>
                                        <p className="font-medium mb-2">Alerts</p>
                                        <div className="space-y-1" data-testid="bias-alerts">
                                            {biasScan.alerts.map((a, i) => (
                                                <div key={i} className={`p-2 rounded text-sm ${a.level === 'info' ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300' : 'bg-amber-50 text-amber-800 dark:bg-amber-950/30 dark:text-amber-200'}`}>
                                                    <span className="font-medium">[{a.category}]</span> {a.issue}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    {Object.keys(biasScan.groups || {}).map((cat) => (
                                        <div key={cat}>
                                            <p className="font-medium capitalize mt-2 mb-1">{cat}</p>
                                            <div className="overflow-x-auto border rounded">
                                                <table className="w-full text-sm">
                                                    <thead className="bg-muted">
                                                        <tr>
                                                            <th className="text-left p-2">Group</th>
                                                            <th className="text-right p-2">Total</th>
                                                            <th className="text-right p-2">Favourable</th>
                                                            <th className="text-right p-2">Rate</th>
                                                            <th className="text-right p-2">Avg weight</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {Object.entries(biasScan.groups[cat]).map(([g, b]) => (
                                                            <tr key={g} className="border-t">
                                                                <td className="p-2">{g}</td>
                                                                <td className="p-2 text-right">{b.total}</td>
                                                                <td className="p-2 text-right">{b.favourable}</td>
                                                                <td className="p-2 text-right">{(b.favourable_rate * 100).toFixed(0)}%</td>
                                                                <td className="p-2 text-right">{b.average_weight ?? '—'}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    ))}
                                </>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* Objective dialog */}
            <Dialog open={objDialog} onOpenChange={setObjDialog}>
                <DialogContent data-testid="obj-dialog">
                    <DialogHeader><DialogTitle>New objective</DialogTitle></DialogHeader>
                    <form onSubmit={createObjective} className="space-y-3">
                        <div><Label>Employee</Label>
                            <Select value={objForm.employee_id} onValueChange={(v) => setObjForm({ ...objForm, employee_id: v })}>
                                <SelectTrigger data-testid="obj-employee"><SelectValue placeholder="Choose…" /></SelectTrigger>
                                <SelectContent>{employees.map(e => <SelectItem key={e.employee_id} value={e.employee_id}>{e.first_name} {e.last_name}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div><Label>Title</Label><Input required value={objForm.title} onChange={(e) => setObjForm({ ...objForm, title: e.target.value })} data-testid="obj-title" /></div>
                        <div><Label>Description</Label><Textarea rows={2} value={objForm.description} onChange={(e) => setObjForm({ ...objForm, description: e.target.value })} /></div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label>Target date</Label><Input type="date" value={objForm.target_date} onChange={(e) => setObjForm({ ...objForm, target_date: e.target.value })} /></div>
                            <div><Label>Weight %</Label><Input type="number" min="1" max="100" value={objForm.weight} onChange={(e) => setObjForm({ ...objForm, weight: parseInt(e.target.value) })} /></div>
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setObjDialog(false)}>Cancel</Button>
                            <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="save-obj-btn">Create</Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* Appraisal dialog */}
            <Dialog open={apprDialog} onOpenChange={setApprDialog}>
                <DialogContent data-testid="appr-dialog">
                    <DialogHeader><DialogTitle>New appraisal</DialogTitle></DialogHeader>
                    <form onSubmit={createAppraisal} className="space-y-3">
                        <div><Label>Employee</Label>
                            <Select value={apprForm.employee_id} onValueChange={(v) => setApprForm({ ...apprForm, employee_id: v })}>
                                <SelectTrigger data-testid="appr-employee"><SelectValue placeholder="Choose…" /></SelectTrigger>
                                <SelectContent>{employees.map(e => <SelectItem key={e.employee_id} value={e.employee_id}>{e.first_name} {e.last_name}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label>Cycle</Label><Input required value={apprForm.cycle} onChange={(e) => setApprForm({ ...apprForm, cycle: e.target.value })} placeholder="2025-Annual" /></div>
                            <div><Label>Rating</Label>
                                <Select value={apprForm.overall_rating} onValueChange={(v) => setApprForm({ ...apprForm, overall_rating: v })}>
                                    <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                                    <SelectContent>{RATINGS.map(r => <SelectItem key={r.id} value={r.id}>{r.label}</SelectItem>)}</SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label>Period start</Label><Input type="date" required value={apprForm.period_start} onChange={(e) => setApprForm({ ...apprForm, period_start: e.target.value })} /></div>
                            <div><Label>Period end</Label><Input type="date" required value={apprForm.period_end} onChange={(e) => setApprForm({ ...apprForm, period_end: e.target.value })} /></div>
                        </div>
                        <div><Label>Manager assessment</Label><Textarea rows={3} value={apprForm.manager_assessment} onChange={(e) => setApprForm({ ...apprForm, manager_assessment: e.target.value })} /></div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setApprDialog(false)}>Cancel</Button>
                            <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="save-appr-btn">Create</Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* Note dialog */}
            <Dialog open={noteDialog} onOpenChange={setNoteDialog}>
                <DialogContent data-testid="note-dialog">
                    <DialogHeader><DialogTitle>Add review note</DialogTitle></DialogHeader>
                    <form onSubmit={createNote} className="space-y-3">
                        <div><Label>Employee</Label>
                            <Select value={noteForm.employee_id} onValueChange={(v) => setNoteForm({ ...noteForm, employee_id: v })}>
                                <SelectTrigger data-testid="note-employee"><SelectValue placeholder="Choose…" /></SelectTrigger>
                                <SelectContent>{employees.map(e => <SelectItem key={e.employee_id} value={e.employee_id}>{e.first_name} {e.last_name}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label>Type</Label>
                                <Select value={noteForm.note_type} onValueChange={(v) => setNoteForm({ ...noteForm, note_type: v })}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="one_on_one">1-on-1</SelectItem>
                                        <SelectItem value="feedback">Feedback</SelectItem>
                                        <SelectItem value="praise">Praise</SelectItem>
                                        <SelectItem value="concern">Concern</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="flex items-end gap-2">
                                <input type="checkbox" id="note-private" checked={noteForm.private} onChange={(e) => setNoteForm({ ...noteForm, private: e.target.checked })} />
                                <label htmlFor="note-private" className="text-sm">Private (HR/manager only)</label>
                            </div>
                        </div>
                        <div><Label>Title</Label><Input required value={noteForm.title} onChange={(e) => setNoteForm({ ...noteForm, title: e.target.value })} data-testid="note-title" /></div>
                        <div><Label>Content</Label><Textarea required rows={3} value={noteForm.content} onChange={(e) => setNoteForm({ ...noteForm, content: e.target.value })} /></div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setNoteDialog(false)}>Cancel</Button>
                            <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="save-note-btn">Add note</Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
}
