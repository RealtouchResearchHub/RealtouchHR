import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../ui/select';
import { Checkbox } from '../ui/checkbox';
import { toast } from 'sonner';
import { GraduationCap, Plus, Award, Loader2, ArrowUpRight } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }, withCredentials: true });

export default function TrainingPage() {
    const [tab, setTab] = useState('courses');
    const [courses, setCourses] = useState([]);
    const [records, setRecords] = useState([]);
    const [matrix, setMatrix] = useState({ courses: [], matrix: [] });
    const [employees, setEmployees] = useState([]);
    const [loading, setLoading] = useState(true);
    const [courseDialog, setCourseDialog] = useState(false);
    const [recordDialog, setRecordDialog] = useState(false);
    const [courseForm, setCourseForm] = useState({ title: '', provider: '', description: '', mandatory: false, renewal_months: '' });
    const [recordForm, setRecordForm] = useState({ course_id: '', employee_id: '', completion_date: '', certificate_url: '', status: 'completed', notes: '' });

    const load = async () => {
        setLoading(true);
        try {
            const [c, r, m, e] = await Promise.allSettled([
                axios.get(`${API_URL}/api/training/courses`, auth()),
                axios.get(`${API_URL}/api/training/records`, auth()),
                axios.get(`${API_URL}/api/training/matrix`, auth()),
                axios.get(`${API_URL}/api/employees`, auth()),
            ]);
            if (c.status === 'fulfilled') setCourses(c.value.data.courses || []);
            if (r.status === 'fulfilled') setRecords(r.value.data.records || []);
            if (m.status === 'fulfilled') setMatrix(m.value.data || { courses: [], matrix: [] });
            if (e.status === 'fulfilled') setEmployees(e.value.data?.employees || e.value.data || []);
        } catch (e) { /* ignore */ } finally { setLoading(false); }
    };
    useEffect(() => { load(); }, []);

    const createCourse = async () => {
        if (!courseForm.title) { toast.error('Title required'); return; }
        try {
            const payload = { ...courseForm, renewal_months: courseForm.renewal_months ? Number(courseForm.renewal_months) : null };
            await axios.post(`${API_URL}/api/training/courses`, payload, auth());
            toast.success('Course created');
            setCourseDialog(false);
            setCourseForm({ title: '', provider: '', description: '', mandatory: false, renewal_months: '' });
            load();
        } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    };

    const createRecord = async () => {
        if (!recordForm.course_id || !recordForm.employee_id) { toast.error('Course & employee required'); return; }
        try {
            await axios.post(`${API_URL}/api/training/records`, recordForm, auth());
            toast.success('Record added');
            setRecordDialog(false);
            setRecordForm({ course_id: '', employee_id: '', completion_date: '', certificate_url: '', status: 'completed', notes: '' });
            load();
        } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    };

    const statusColor = (s) => ({
        completed: 'bg-emerald-100 text-emerald-700',
        in_progress: 'bg-amber-100 text-amber-700',
        assigned: 'bg-slate-100 text-slate-700',
        expired: 'bg-red-100 text-red-700',
        expiring_soon: 'bg-amber-100 text-amber-700',
        not_started: 'bg-slate-100 text-slate-500',
    }[s] || 'bg-slate-100 text-slate-700');

    const empName = (id) => {
        const e = employees.find((x) => x.employee_id === id);
        return e ? `${e.first_name} ${e.last_name}` : id;
    };

    return (
        <div className="space-y-6" data-testid="training-page">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Training Records</h1>
                    <p className="text-muted-foreground mt-1">Manage courses, completions, certificates and renewal reminders.</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => setCourseDialog(true)} data-testid="new-course-btn"><Plus className="w-4 h-4 mr-1" /> Course</Button>
                    <Button onClick={() => setRecordDialog(true)} className="bg-indigo-600 hover:bg-indigo-700" data-testid="new-training-record-btn"><Plus className="w-4 h-4 mr-1" /> Record</Button>
                </div>
            </div>

            <Tabs value={tab} onValueChange={setTab}>
                <TabsList>
                    <TabsTrigger value="courses">Courses ({courses.length})</TabsTrigger>
                    <TabsTrigger value="records">Records ({records.length})</TabsTrigger>
                    <TabsTrigger value="matrix">Matrix</TabsTrigger>
                </TabsList>

                <TabsContent value="courses">
                    <Card>
                        <CardContent className="pt-6">
                            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : courses.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No courses yet.</p>
                            ) : (
                                <div className="space-y-2">
                                    {courses.map((c) => (
                                        <div key={c.course_id} className="p-3 border rounded-lg flex items-start gap-3">
                                            <GraduationCap className="w-5 h-5 text-indigo-500 mt-0.5" />
                                            <div className="flex-1">
                                                <p className="font-medium">{c.title}</p>
                                                <p className="text-xs text-muted-foreground">{c.provider || '—'} · {c.duration_hours ? `${c.duration_hours}h` : 'duration n/a'} · renewal: {c.renewal_months ? `${c.renewal_months} months` : 'none'}</p>
                                                {c.mandatory && <Badge className="mt-1 bg-red-100 text-red-700">Mandatory</Badge>}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="records">
                    <Card>
                        <CardContent className="pt-6">
                            {records.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No records yet.</p>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead className="bg-muted text-left">
                                            <tr>
                                                <th className="p-2">Employee</th>
                                                <th className="p-2">Course</th>
                                                <th className="p-2">Completion</th>
                                                <th className="p-2">Expiry</th>
                                                <th className="p-2">Status</th>
                                                <th className="p-2">Certificate</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {records.map((r) => (
                                                <tr key={r.record_id} className="border-t">
                                                    <td className="p-2">{empName(r.employee_id)}</td>
                                                    <td className="p-2">{r.course_title}</td>
                                                    <td className="p-2">{r.completion_date || '—'}</td>
                                                    <td className="p-2">{r.expiry_date || '—'}</td>
                                                    <td className="p-2"><Badge className={statusColor(r.status)}>{r.status}</Badge></td>
                                                    <td className="p-2">{r.certificate_url ? <a href={r.certificate_url} target="_blank" rel="noopener noreferrer" className="text-indigo-600"><ArrowUpRight className="w-3 h-3 inline" /></a> : '—'}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="matrix">
                    <Card>
                        <CardHeader><CardTitle>Training Matrix</CardTitle></CardHeader>
                        <CardContent>
                            {matrix.matrix.length === 0 ? (
                                <p className="text-sm text-muted-foreground">Add employees and courses to see the matrix.</p>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="text-sm">
                                        <thead className="bg-muted text-left">
                                            <tr>
                                                <th className="p-2 sticky left-0 bg-muted">Employee</th>
                                                {matrix.courses.map((c) => (
                                                    <th key={c.course_id} className="p-2 whitespace-nowrap">{c.title}</th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {matrix.matrix.map((row) => (
                                                <tr key={row.employee_id} className="border-t">
                                                    <td className="p-2 font-medium whitespace-nowrap sticky left-0 bg-card">{row.name}</td>
                                                    {matrix.courses.map((c) => {
                                                        const cell = row.courses[c.course_id];
                                                        return <td key={c.course_id} className="p-2 text-center"><Badge className={statusColor(cell.status)}>{cell.status.replace('_', ' ')}</Badge></td>;
                                                    })}
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            <Dialog open={courseDialog} onOpenChange={setCourseDialog}>
                <DialogContent>
                    <DialogHeader><DialogTitle>New course</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div><Label>Title</Label><Input value={courseForm.title} onChange={(e) => setCourseForm({ ...courseForm, title: e.target.value })} data-testid="course-title-input" /></div>
                        <div><Label>Provider</Label><Input value={courseForm.provider} onChange={(e) => setCourseForm({ ...courseForm, provider: e.target.value })} /></div>
                        <div><Label>Description</Label><Textarea rows={2} value={courseForm.description} onChange={(e) => setCourseForm({ ...courseForm, description: e.target.value })} /></div>
                        <div><Label>Renewal (months)</Label><Input type="number" value={courseForm.renewal_months} onChange={(e) => setCourseForm({ ...courseForm, renewal_months: e.target.value })} placeholder="12 = annual renewal" /></div>
                        <div className="flex items-center gap-2"><Checkbox id="cm" checked={courseForm.mandatory} onCheckedChange={(c) => setCourseForm({ ...courseForm, mandatory: c })} /><Label htmlFor="cm">Mandatory</Label></div>
                    </div>
                    <DialogFooter><Button variant="outline" onClick={() => setCourseDialog(false)}>Cancel</Button><Button onClick={createCourse} data-testid="create-course-btn">Create</Button></DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={recordDialog} onOpenChange={setRecordDialog}>
                <DialogContent>
                    <DialogHeader><DialogTitle>New training record</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div><Label>Course</Label>
                            <Select value={recordForm.course_id} onValueChange={(v) => setRecordForm({ ...recordForm, course_id: v })}>
                                <SelectTrigger><SelectValue placeholder="Pick a course" /></SelectTrigger>
                                <SelectContent>{courses.map((c) => <SelectItem key={c.course_id} value={c.course_id}>{c.title}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div><Label>Employee</Label>
                            <Select value={recordForm.employee_id} onValueChange={(v) => setRecordForm({ ...recordForm, employee_id: v })}>
                                <SelectTrigger><SelectValue placeholder="Pick employee" /></SelectTrigger>
                                <SelectContent>{employees.map((e) => <SelectItem key={e.employee_id} value={e.employee_id}>{e.first_name} {e.last_name}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div><Label>Completion date</Label><Input type="date" value={recordForm.completion_date} onChange={(e) => setRecordForm({ ...recordForm, completion_date: e.target.value })} /></div>
                        <div><Label>Certificate URL</Label><Input value={recordForm.certificate_url} onChange={(e) => setRecordForm({ ...recordForm, certificate_url: e.target.value })} /></div>
                        <div><Label>Status</Label>
                            <Select value={recordForm.status} onValueChange={(v) => setRecordForm({ ...recordForm, status: v })}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="assigned">Assigned</SelectItem>
                                    <SelectItem value="in_progress">In Progress</SelectItem>
                                    <SelectItem value="completed">Completed</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <DialogFooter><Button variant="outline" onClick={() => setRecordDialog(false)}>Cancel</Button><Button onClick={createRecord} data-testid="create-record-btn">Save</Button></DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
