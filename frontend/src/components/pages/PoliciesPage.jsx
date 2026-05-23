import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../ui/select';
import { Checkbox } from '../ui/checkbox';
import { toast } from 'sonner';
import { FileText, Plus, ScrollText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }, withCredentials: true });

const CATEGORIES = [
    ['general', 'General'],
    ['safeguarding', 'Safeguarding'],
    ['data_protection', 'Data Protection'],
    ['equality', 'Equality & Diversity'],
    ['health_safety', 'Health & Safety'],
    ['disciplinary', 'Disciplinary'],
    ['grievance', 'Grievance'],
    ['absence', 'Absence'],
    ['remote_working', 'Remote Working'],
    ['whistleblowing', 'Whistleblowing'],
    ['rtw', 'Right to Work'],
];

export default function PoliciesPage() {
    const [policies, setPolicies] = useState([]);
    const [pending, setPending] = useState([]);
    const [loading, setLoading] = useState(true);
    const [dialog, setDialog] = useState(false);
    const [form, setForm] = useState({ title: '', category: 'general', content: '', file_url: '', review_date: '', mandatory: true });

    const load = async () => {
        setLoading(true);
        try {
            const [a, b] = await Promise.allSettled([
                axios.get(`${API_URL}/api/policies`, auth()),
                axios.get(`${API_URL}/api/policies/my/pending`, auth()),
            ]);
            if (a.status === 'fulfilled') setPolicies(a.value.data.policies || []);
            if (b.status === 'fulfilled') setPending(b.value.data.pending || []);
        } catch (e) { /* ignore */ }
        finally { setLoading(false); }
    };
    useEffect(() => { load(); }, []);

    const create = async () => {
        if (!form.title) { toast.error('Title is required'); return; }
        try {
            await axios.post(`${API_URL}/api/policies`, form, auth());
            toast.success('Policy created');
            setDialog(false);
            setForm({ title: '', category: 'general', content: '', file_url: '', review_date: '', mandatory: true });
            load();
        } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    };

    const acknowledge = async (policy_id) => {
        try {
            await axios.post(`${API_URL}/api/policies/${policy_id}/acknowledge`, {}, auth());
            toast.success('Acknowledged');
            load();
        } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    };

    return (
        <div className="space-y-6" data-testid="policies-page">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Policies</h1>
                    <p className="text-muted-foreground mt-1">Library of company policies, version-controlled with acknowledgement tracking.</p>
                </div>
                <Button onClick={() => setDialog(true)} className="bg-indigo-600 hover:bg-indigo-700" data-testid="new-policy-btn">
                    <Plus className="w-4 h-4 mr-2" /> New policy
                </Button>
            </div>

            {pending.length > 0 && (
                <Card className="border-amber-200 bg-amber-50/40 dark:bg-amber-950/20">
                    <CardHeader>
                        <CardTitle className="text-amber-700 dark:text-amber-300 text-base flex items-center gap-2"><AlertCircle className="w-4 h-4" /> Pending acknowledgements ({pending.length})</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        {pending.map((p) => (
                            <div key={p.policy_id} className="flex items-center justify-between p-3 rounded-lg bg-white dark:bg-card border">
                                <div>
                                    <p className="font-medium">{p.title}</p>
                                    <p className="text-xs text-muted-foreground">{p.category} · v{p.version}</p>
                                </div>
                                <Button size="sm" onClick={() => acknowledge(p.policy_id)} data-testid={`ack-${p.policy_id}`}>
                                    <CheckCircle2 className="w-4 h-4 mr-1" /> I've read this
                                </Button>
                            </div>
                        ))}
                    </CardContent>
                </Card>
            )}

            <Card>
                <CardHeader><CardTitle>Policy Library</CardTitle></CardHeader>
                <CardContent>
                    {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : policies.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No policies yet. Create your first one.</p>
                    ) : (
                        <div className="space-y-2" data-testid="policy-list">
                            {policies.map((p) => (
                                <div key={p.policy_id} className="p-3 rounded-lg border flex items-start justify-between">
                                    <div className="flex items-start gap-3">
                                        <ScrollText className="w-5 h-5 text-indigo-500 mt-0.5" />
                                        <div>
                                            <p className="font-medium">{p.title}</p>
                                            <div className="flex flex-wrap gap-1 mt-1">
                                                <Badge variant="outline">{p.category}</Badge>
                                                <Badge variant="secondary">v{p.version}</Badge>
                                                {p.mandatory && <Badge className="bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-200">Mandatory</Badge>}
                                                {p.review_date && <Badge variant="outline">Review by {p.review_date}</Badge>}
                                            </div>
                                            {p.content && <p className="text-xs text-muted-foreground mt-2 max-w-2xl">{p.content.slice(0, 160)}{p.content.length > 160 ? '…' : ''}</p>}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            <Dialog open={dialog} onOpenChange={setDialog}>
                <DialogContent className="max-w-lg">
                    <DialogHeader><DialogTitle>New policy</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div><Label>Title</Label><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} data-testid="policy-title-input" /></div>
                        <div><Label>Category</Label>
                            <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>{CATEGORIES.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div><Label>Content (or link to PDF below)</Label><Textarea rows={5} value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} /></div>
                        <div><Label>Or external file URL</Label><Input value={form.file_url} onChange={(e) => setForm({ ...form, file_url: e.target.value })} placeholder="https://..." /></div>
                        <div><Label>Review date</Label><Input type="date" value={form.review_date} onChange={(e) => setForm({ ...form, review_date: e.target.value })} /></div>
                        <div className="flex items-center gap-2">
                            <Checkbox id="mand" checked={form.mandatory} onCheckedChange={(c) => setForm({ ...form, mandatory: c })} />
                            <Label htmlFor="mand">Mandatory (requires acknowledgement)</Label>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDialog(false)}>Cancel</Button>
                        <Button onClick={create} data-testid="create-policy-btn">Create</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
