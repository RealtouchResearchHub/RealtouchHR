import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import {
    Briefcase, Plus, Users, Star, ChevronRight, Loader2,
    FileText, BookOpen, ClipboardList, RefreshCw, Trash2,
    CheckCircle, XCircle, ArrowRight, MapPin, Calendar,
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const STAGES = ["applied", "screening", "interview", "assessment", "offer", "hired", "rejected", "withdrawn"];
const CONTRACT_TYPES = ["full_time", "part_time", "fixed_term", "zero_hours", "casual", "freelance", "apprenticeship"];
const SOURCES = ["direct", "linkedin", "indeed", "referral", "agency", "other"];

const STAGE_COLORS = {
    applied: 'bg-slate-100 text-slate-700',
    screening: 'bg-blue-100 text-blue-700',
    interview: 'bg-indigo-100 text-indigo-700',
    assessment: 'bg-purple-100 text-purple-700',
    offer: 'bg-amber-100 text-amber-700',
    hired: 'bg-emerald-100 text-emerald-700',
    rejected: 'bg-rose-100 text-rose-700',
    withdrawn: 'bg-slate-100 text-slate-500',
};

const BLANK_JOB = { title: '', department: '', location: '', contract_type: 'full_time', salary_min: '', salary_max: '', description: '', requirements: '', closing_date: '' };
const BLANK_APPLICANT = { job_id: '', first_name: '', last_name: '', email: '', phone: '', cover_letter: '', source: 'direct' };

export default function RecruitmentPage() {
    const { user, token } = useAuth();
    const auth = () => ({ headers: { Authorization: `Bearer ${token}` }, withCredentials: true });
    const isManager = ['owner', 'admin', 'manager'].includes(user?.role);

    const [jobs, setJobs] = useState([]);
    const [applicants, setApplicants] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    const [jobDialog, setJobDialog] = useState(false);
    const [jobForm, setJobForm] = useState(BLANK_JOB);
    const [jobSaving, setJobSaving] = useState(false);
    const [editingJob, setEditingJob] = useState(null);

    const [appDialog, setAppDialog] = useState(false);
    const [appForm, setAppForm] = useState(BLANK_APPLICANT);
    const [appSaving, setAppSaving] = useState(false);

    const [selectedJob, setSelectedJob] = useState(null);
    const [templateDialog, setTemplateDialog] = useState(null);
    const [templateContent, setTemplateContent] = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [j, a, s] = await Promise.all([
                axios.get(`${API_URL}/api/recruitment/jobs`, auth()),
                axios.get(`${API_URL}/api/recruitment/applicants`, auth()),
                axios.get(`${API_URL}/api/recruitment/jobs/stats`, auth()),
            ]);
            setJobs(j.data.jobs || []);
            setApplicants(a.data.applicants || []);
            setStats(s.data);
        } catch { toast.error('Failed to load recruitment data'); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const saveJob = async () => {
        if (!jobForm.title) { toast.error('Job title required'); return; }
        setJobSaving(true);
        try {
            const payload = { ...jobForm, salary_min: jobForm.salary_min ? Number(jobForm.salary_min) : null, salary_max: jobForm.salary_max ? Number(jobForm.salary_max) : null };
            if (editingJob) {
                await axios.patch(`${API_URL}/api/recruitment/jobs/${editingJob}`, payload, auth());
                toast.success('Job updated');
            } else {
                await axios.post(`${API_URL}/api/recruitment/jobs`, payload, auth());
                toast.success('Job posted');
            }
            setJobDialog(false); setJobForm(BLANK_JOB); setEditingJob(null); load();
        } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
        finally { setJobSaving(false); }
    };

    const deleteJob = async (jobId) => {
        if (!window.confirm('Delete this job and all applicants?')) return;
        try { await axios.delete(`${API_URL}/api/recruitment/jobs/${jobId}`, auth()); toast.success('Job deleted'); load(); }
        catch { toast.error('Failed'); }
    };

    const updateJobStatus = async (jobId, status) => {
        try { await axios.patch(`${API_URL}/api/recruitment/jobs/${jobId}`, { status }, auth()); load(); }
        catch { toast.error('Failed'); }
    };

    const addApplicant = async () => {
        if (!appForm.job_id || !appForm.first_name || !appForm.last_name || !appForm.email) { toast.error('Required: job, name, email'); return; }
        setAppSaving(true);
        try {
            await axios.post(`${API_URL}/api/recruitment/applicants`, appForm, auth());
            toast.success('Applicant added');
            setAppDialog(false); setAppForm(BLANK_APPLICANT); load();
        } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
        finally { setAppSaving(false); }
    };

    const moveStage = async (applicantId, stage) => {
        try {
            await axios.patch(`${API_URL}/api/recruitment/applicants/${applicantId}`, { stage }, auth());
            if (stage === 'hired') toast.success('Applicant hired! Job marked as filled.');
            else toast.success(`Moved to ${stage}`);
            load();
        } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    };

    const deleteApplicant = async (id) => {
        if (!window.confirm('Remove this applicant?')) return;
        try { await axios.delete(`${API_URL}/api/recruitment/applicants/${id}`, auth()); load(); }
        catch { toast.error('Failed'); }
    };

    const loadTemplate = async (type) => {
        try {
            const res = await axios.get(`${API_URL}/api/recruitment/templates/${type}`, auth());
            setTemplateContent(res.data.template || res.data.handbook || '');
            setTemplateDialog(type);
        } catch { toast.error('Failed to load template'); }
    };

    const filteredApplicants = selectedJob ? applicants.filter(a => a.job_id === selectedJob) : applicants;

    if (loading) return <div className="flex items-center justify-center min-h-[60vh]"><Loader2 className="w-8 h-8 animate-spin text-indigo-600" /></div>;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2"><Briefcase className="w-6 h-6" /> Recruitment</h1>
                    <p className="text-muted-foreground text-sm mt-1">Manage job postings, applicants, and hiring pipeline</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={load}><RefreshCw className="w-4 h-4 mr-1" />Refresh</Button>
                    {isManager && <Button size="sm" onClick={() => { setJobForm(BLANK_JOB); setEditingJob(null); setJobDialog(true); }}><Plus className="w-4 h-4 mr-1" />Post Job</Button>}
                    {isManager && <Button size="sm" variant="outline" onClick={() => setAppDialog(true)}><Users className="w-4 h-4 mr-1" />Add Applicant</Button>}
                </div>
            </div>

            {/* Stats */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    {[
                        ['Total Jobs', stats.total_jobs],
                        ['Open', stats.open_jobs],
                        ['Filled', stats.filled_jobs],
                        ['Applicants', stats.total_applicants],
                        ['Hired', stats.hired],
                    ].map(([label, val]) => (
                        <Card key={label} className="p-3">
                            <p className="text-xs text-muted-foreground">{label}</p>
                            <p className="text-2xl font-bold">{val}</p>
                        </Card>
                    ))}
                </div>
            )}

            <Tabs defaultValue="jobs">
                <TabsList>
                    <TabsTrigger value="jobs"><Briefcase className="w-4 h-4 mr-1" />Jobs ({jobs.length})</TabsTrigger>
                    <TabsTrigger value="pipeline"><Users className="w-4 h-4 mr-1" />Pipeline ({applicants.length})</TabsTrigger>
                    <TabsTrigger value="templates"><FileText className="w-4 h-4 mr-1" />Resources</TabsTrigger>
                </TabsList>

                {/* Jobs tab */}
                <TabsContent value="jobs">
                    {jobs.length === 0 ? (
                        <div className="text-center py-16 text-muted-foreground">
                            <Briefcase className="w-12 h-12 mx-auto mb-3 opacity-30" />
                            <p className="font-medium">No jobs posted yet</p>
                            {isManager && <Button className="mt-4" onClick={() => setJobDialog(true)}><Plus className="w-4 h-4 mr-1" />Post your first job</Button>}
                        </div>
                    ) : (
                        <div className="space-y-3 mt-3">
                            {jobs.map(job => (
                                <Card key={job.job_id} className="p-4">
                                    <div className="flex items-start justify-between gap-3 flex-wrap">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <p className="font-semibold">{job.title}</p>
                                                <Badge className={job.status === 'open' ? 'bg-emerald-100 text-emerald-700' : job.status === 'filled' ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-700'}>
                                                    {job.status}
                                                </Badge>
                                                <Badge variant="outline" className="text-xs">{job.contract_type?.replace('_', ' ')}</Badge>
                                            </div>
                                            <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground flex-wrap">
                                                {job.department && <span>{job.department}</span>}
                                                {job.location && <span><MapPin className="inline w-3 h-3 mr-0.5" />{job.location}</span>}
                                                {(job.salary_min || job.salary_max) && <span>£{job.salary_min?.toLocaleString()}{job.salary_max ? `–${job.salary_max?.toLocaleString()}` : '+'}</span>}
                                                {job.closing_date && <span><Calendar className="inline w-3 h-3 mr-0.5" />Closes {job.closing_date}</span>}
                                                <span><Users className="inline w-3 h-3 mr-0.5" />{job.applicant_count || 0} applicants</span>
                                            </div>
                                        </div>
                                        {isManager && (
                                            <div className="flex items-center gap-2">
                                                <Select value={job.status} onValueChange={s => updateJobStatus(job.job_id, s)}>
                                                    <SelectTrigger className="h-8 w-28 text-xs"><SelectValue /></SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="open">Open</SelectItem>
                                                        <SelectItem value="filled">Filled</SelectItem>
                                                        <SelectItem value="closed">Closed</SelectItem>
                                                        <SelectItem value="draft">Draft</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                                <Button size="sm" variant="outline" onClick={() => { setJobForm({ title: job.title, department: job.department || '', location: job.location || '', contract_type: job.contract_type, salary_min: job.salary_min || '', salary_max: job.salary_max || '', description: job.description || '', requirements: job.requirements || '', closing_date: job.closing_date || '' }); setEditingJob(job.job_id); setJobDialog(true); }}>Edit</Button>
                                                <Button size="sm" variant="ghost" onClick={() => deleteJob(job.job_id)}><Trash2 className="w-3.5 h-3.5 text-rose-500" /></Button>
                                            </div>
                                        )}
                                    </div>
                                </Card>
                            ))}
                        </div>
                    )}
                </TabsContent>

                {/* Pipeline tab */}
                <TabsContent value="pipeline">
                    <div className="flex gap-3 flex-wrap mt-3 mb-4">
                        <Button size="sm" variant={selectedJob === null ? 'default' : 'outline'} onClick={() => setSelectedJob(null)}>All Jobs</Button>
                        {jobs.map(j => (
                            <Button key={j.job_id} size="sm" variant={selectedJob === j.job_id ? 'default' : 'outline'} onClick={() => setSelectedJob(j.job_id)}>
                                {j.title} ({applicants.filter(a => a.job_id === j.job_id).length})
                            </Button>
                        ))}
                    </div>

                    {/* Pipeline kanban-style by stage */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                        {STAGES.slice(0, 8).map(stage => {
                            const stageApps = filteredApplicants.filter(a => a.stage === stage);
                            return (
                                <div key={stage} className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <Badge className={`${STAGE_COLORS[stage]} text-xs capitalize`}>{stage}</Badge>
                                        <span className="text-xs text-muted-foreground">{stageApps.length}</span>
                                    </div>
                                    {stageApps.map(app => (
                                        <Card key={app.applicant_id} className="p-3">
                                            <p className="font-medium text-sm">{app.full_name}</p>
                                            <p className="text-xs text-muted-foreground truncate">{app.email}</p>
                                            <p className="text-xs text-muted-foreground">{app.job_title}</p>
                                            {isManager && (
                                                <div className="mt-2 flex gap-1 flex-wrap">
                                                    {STAGES.filter(s => s !== stage).slice(0, 3).map(s => (
                                                        <button key={s} onClick={() => moveStage(app.applicant_id, s)} className="text-xs px-1.5 py-0.5 rounded border hover:bg-muted capitalize">{s}</button>
                                                    ))}
                                                    <button onClick={() => deleteApplicant(app.applicant_id)} className="text-xs px-1 py-0.5 rounded border border-rose-200 text-rose-600 hover:bg-rose-50"><Trash2 className="w-3 h-3" /></button>
                                                </div>
                                            )}
                                        </Card>
                                    ))}
                                    {stageApps.length === 0 && <p className="text-xs text-muted-foreground/50 text-center py-4 border border-dashed rounded-lg">Empty</p>}
                                </div>
                            );
                        })}
                    </div>
                </TabsContent>

                {/* Resources / Templates */}
                <TabsContent value="templates">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
                        {[
                            { key: 'job-description', icon: FileText, title: 'Job Description Template', desc: 'Structured template for writing job descriptions' },
                            { key: 'offer-letter', icon: ClipboardList, title: 'Offer Letter Template', desc: 'Professional offer letter with key terms' },
                            { key: 'interview-handbook', icon: BookOpen, title: 'Interview Handbook', desc: 'Legal guidelines, scoring, STAR questions' },
                        ].map(t => (
                            <Card key={t.key} className="p-5 cursor-pointer hover:shadow-md transition-shadow" onClick={() => loadTemplate(t.key)}>
                                <t.icon className="w-8 h-8 text-indigo-600 mb-3" />
                                <p className="font-semibold text-sm">{t.title}</p>
                                <p className="text-xs text-muted-foreground mt-1">{t.desc}</p>
                                <Button size="sm" variant="outline" className="mt-3">View Template <ChevronRight className="w-3.5 h-3.5 ml-1" /></Button>
                            </Card>
                        ))}
                    </div>
                </TabsContent>
            </Tabs>

            {/* Post/Edit Job Dialog */}
            <Dialog open={jobDialog} onOpenChange={o => { setJobDialog(o); if (!o) { setEditingJob(null); setJobForm(BLANK_JOB); } }}>
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader><DialogTitle>{editingJob ? 'Edit Job' : 'Post New Job'}</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div><Label>Job Title *</Label><Input value={jobForm.title} onChange={e => setJobForm(f => ({ ...f, title: e.target.value }))} placeholder="e.g. Senior HR Advisor" /></div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label>Department</Label><Input value={jobForm.department} onChange={e => setJobForm(f => ({ ...f, department: e.target.value }))} placeholder="HR, Finance..." /></div>
                            <div><Label>Location</Label><Input value={jobForm.location} onChange={e => setJobForm(f => ({ ...f, location: e.target.value }))} placeholder="London / Remote" /></div>
                        </div>
                        <div className="grid grid-cols-3 gap-3">
                            <div>
                                <Label>Contract Type</Label>
                                <Select value={jobForm.contract_type} onValueChange={v => setJobForm(f => ({ ...f, contract_type: v }))}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>{CONTRACT_TYPES.map(c => <SelectItem key={c} value={c}>{c.replace('_', ' ')}</SelectItem>)}</SelectContent>
                                </Select>
                            </div>
                            <div><Label>Salary Min (£)</Label><Input type="number" value={jobForm.salary_min} onChange={e => setJobForm(f => ({ ...f, salary_min: e.target.value }))} placeholder="25000" /></div>
                            <div><Label>Salary Max (£)</Label><Input type="number" value={jobForm.salary_max} onChange={e => setJobForm(f => ({ ...f, salary_max: e.target.value }))} placeholder="35000" /></div>
                        </div>
                        <div><Label>Closing Date</Label><Input type="date" value={jobForm.closing_date} onChange={e => setJobForm(f => ({ ...f, closing_date: e.target.value }))} /></div>
                        <div><Label>Job Description</Label><textarea className="w-full border rounded p-2 text-sm bg-background" rows={5} value={jobForm.description} onChange={e => setJobForm(f => ({ ...f, description: e.target.value }))} placeholder="Describe the role..." /></div>
                        <div><Label>Requirements</Label><textarea className="w-full border rounded p-2 text-sm bg-background" rows={3} value={jobForm.requirements} onChange={e => setJobForm(f => ({ ...f, requirements: e.target.value }))} placeholder="Essential skills and qualifications..." /></div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setJobDialog(false)}>Cancel</Button>
                        <Button onClick={saveJob} disabled={jobSaving}>{jobSaving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null}{editingJob ? 'Save Changes' : 'Post Job'}</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Add Applicant Dialog */}
            <Dialog open={appDialog} onOpenChange={setAppDialog}>
                <DialogContent className="max-w-lg">
                    <DialogHeader><DialogTitle><Users className="inline w-4 h-4 mr-1" />Add Applicant</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div>
                            <Label>Job *</Label>
                            <Select value={appForm.job_id} onValueChange={v => setAppForm(f => ({ ...f, job_id: v }))}>
                                <SelectTrigger><SelectValue placeholder="Select job..." /></SelectTrigger>
                                <SelectContent>{jobs.filter(j => j.status === 'open').map(j => <SelectItem key={j.job_id} value={j.job_id}>{j.title}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label>First Name *</Label><Input value={appForm.first_name} onChange={e => setAppForm(f => ({ ...f, first_name: e.target.value }))} /></div>
                            <div><Label>Last Name *</Label><Input value={appForm.last_name} onChange={e => setAppForm(f => ({ ...f, last_name: e.target.value }))} /></div>
                        </div>
                        <div><Label>Email *</Label><Input type="email" value={appForm.email} onChange={e => setAppForm(f => ({ ...f, email: e.target.value }))} /></div>
                        <div><Label>Phone</Label><Input value={appForm.phone} onChange={e => setAppForm(f => ({ ...f, phone: e.target.value }))} /></div>
                        <div>
                            <Label>Source</Label>
                            <Select value={appForm.source} onValueChange={v => setAppForm(f => ({ ...f, source: v }))}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>{SOURCES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div><Label>Cover Letter / Notes</Label><textarea className="w-full border rounded p-2 text-sm bg-background" rows={3} value={appForm.cover_letter} onChange={e => setAppForm(f => ({ ...f, cover_letter: e.target.value }))} /></div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setAppDialog(false)}>Cancel</Button>
                        <Button onClick={addApplicant} disabled={appSaving}>{appSaving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null}Add Applicant</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Template viewer */}
            <Dialog open={!!templateDialog} onOpenChange={o => !o && setTemplateDialog(null)}>
                <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader><DialogTitle className="capitalize">{templateDialog?.replace(/-/g, ' ')}</DialogTitle></DialogHeader>
                    <pre className="text-sm bg-muted/40 rounded p-4 whitespace-pre-wrap font-mono leading-relaxed">{templateContent}</pre>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => { navigator.clipboard.writeText(templateContent); toast.success('Copied to clipboard'); }}>Copy</Button>
                        <Button onClick={() => setTemplateDialog(null)}>Close</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
