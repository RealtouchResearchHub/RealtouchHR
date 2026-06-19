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
    Receipt, Plus, Download, CheckCircle, XCircle, Clock,
    Car, Bike, Loader2, PoundSterling, RefreshCw, Trash2, RotateCcw,
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const CATEGORIES = ["Travel", "Accommodation", "Meals & Entertainment", "Mileage", "Equipment & Supplies", "Training & Development", "Subscriptions", "Client Entertainment", "Postage & Courier", "Other"];

function StatusBadge({ status }) {
    const map = {
        pending: 'bg-amber-100 text-amber-700',
        approved: 'bg-emerald-100 text-emerald-700',
        declined: 'bg-rose-100 text-rose-700',
        paid: 'bg-indigo-100 text-indigo-700',
    };
    return <Badge className={map[status] || 'bg-slate-100 text-slate-700'}>{status}</Badge>;
}

const BLANK_CLAIM = { title: '', category: 'Travel', amount: '', currency: 'GBP', expense_date: new Date().toISOString().slice(0, 10), description: '', receipt_url: '' };
const BLANK_MILEAGE = { journey_date: new Date().toISOString().slice(0, 10), from_location: '', to_location: '', miles: '', vehicle_type: 'car', purpose: '', total_miles_ytd: '0' };

export default function ExpensesPage() {
    const { user, token } = useAuth();
    const auth = () => ({ headers: { Authorization: `Bearer ${token}` }, withCredentials: true });
    const isManager = ['owner', 'admin', 'manager'].includes(user?.role);

    const [claims, setClaims] = useState([]);
    const [mileage, setMileage] = useState([]);
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);

    const [claimDialog, setClaimDialog] = useState(false);
    const [claimForm, setClaimForm] = useState(BLANK_CLAIM);
    const [claimSaving, setClaimSaving] = useState(false);

    const [mileageDialog, setMileageDialog] = useState(false);
    const [mileageForm, setMileageForm] = useState(BLANK_MILEAGE);
    const [mileageSaving, setMileageSaving] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [c, m, s] = await Promise.all([
                axios.get(`${API_URL}/api/expenses/claims`, auth()),
                axios.get(`${API_URL}/api/expenses/mileage`, auth()),
                axios.get(`${API_URL}/api/expenses/summary`, auth()),
            ]);
            setClaims(c.data.claims || []);
            setMileage(m.data.claims || []);
            setSummary(s.data);
        } catch { toast.error('Failed to load expenses'); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const submitClaim = async () => {
        if (!claimForm.title || !claimForm.amount) { toast.error('Title and amount required'); return; }
        setClaimSaving(true);
        try {
            await axios.post(`${API_URL}/api/expenses/claims`, { ...claimForm, amount: Number(claimForm.amount) }, auth());
            toast.success('Expense claim submitted');
            setClaimDialog(false);
            setClaimForm(BLANK_CLAIM);
            load();
        } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
        finally { setClaimSaving(false); }
    };

    const submitMileage = async () => {
        if (!mileageForm.from_location || !mileageForm.to_location || !mileageForm.miles) { toast.error('All mileage fields required'); return; }
        setMileageSaving(true);
        try {
            await axios.post(`${API_URL}/api/expenses/mileage`, { ...mileageForm, miles: Number(mileageForm.miles), total_miles_ytd: Number(mileageForm.total_miles_ytd || 0) }, auth());
            toast.success('Mileage claim submitted');
            setMileageDialog(false);
            setMileageForm(BLANK_MILEAGE);
            load();
        } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
        finally { setMileageSaving(false); }
    };

    const updateStatus = async (claimId, status, type = 'claims') => {
        try {
            if (type === 'claims') {
                await axios.patch(`${API_URL}/api/expenses/claims/${claimId}`, { status }, auth());
            } else {
                await axios.patch(`${API_URL}/api/expenses/mileage/${claimId}`, { status }, auth());
            }
            toast.success(`Marked as ${status}`);
            load();
        } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    };

    const deleteClaim = async (claimId) => {
        if (!window.confirm('Delete this claim?')) return;
        try {
            await axios.delete(`${API_URL}/api/expenses/claims/${claimId}`, auth());
            toast.success('Claim deleted');
            load();
        } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    };

    const exportCSV = () => {
        window.open(`${API_URL}/api/expenses/export/csv`, '_blank');
    };

    const myClaims = claims.filter(c => c.employee_id === user?.user_id || c.employee_id === user?.id);
    const pendingApprovals = claims.filter(c => c.status === 'pending');
    const myMileage = mileage.filter(m => m.employee_id === user?.user_id || m.employee_id === user?.id);

    if (loading) return (
        <div className="flex items-center justify-center min-h-[60vh]">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
        </div>
    );

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2"><Receipt className="w-6 h-6" /> Expenses</h1>
                    <p className="text-muted-foreground text-sm mt-1">Manage expense claims and mileage reimbursements</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={load}><RefreshCw className="w-4 h-4 mr-1" /> Refresh</Button>
                    {isManager && <Button variant="outline" size="sm" onClick={exportCSV}><Download className="w-4 h-4 mr-1" /> Export CSV</Button>}
                    <Button size="sm" onClick={() => setMileageDialog(true)}><Car className="w-4 h-4 mr-1" /> Log Mileage</Button>
                    <Button size="sm" onClick={() => setClaimDialog(true)}><Plus className="w-4 h-4 mr-1" /> New Claim</Button>
                </div>
            </div>

            {/* Summary cards */}
            {summary && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {[
                        ['Pending Claims', `£${summary.expenses?.total_pending ?? 0}`, 'amber'],
                        ['Approved', `£${summary.expenses?.total_approved ?? 0}`, 'emerald'],
                        ['Paid Out', `£${summary.expenses?.total_paid ?? 0}`, 'indigo'],
                        ['Total Miles Logged', `${summary.mileage?.total_miles ?? 0} mi`, 'slate'],
                    ].map(([label, val, color]) => (
                        <Card key={label} className="p-4">
                            <p className="text-xs text-muted-foreground">{label}</p>
                            <p className={`text-xl font-bold text-${color}-600 dark:text-${color}-400`}>{val}</p>
                        </Card>
                    ))}
                </div>
            )}

            <Tabs defaultValue="my-claims">
                <TabsList>
                    <TabsTrigger value="my-claims">My Claims</TabsTrigger>
                    <TabsTrigger value="my-mileage">My Mileage</TabsTrigger>
                    {isManager && <TabsTrigger value="approvals">Approvals {pendingApprovals.length > 0 && <Badge className="ml-1 bg-amber-100 text-amber-700 text-xs">{pendingApprovals.length}</Badge>}</TabsTrigger>}
                    {isManager && <TabsTrigger value="all">All Claims</TabsTrigger>}
                </TabsList>

                {/* My Claims */}
                <TabsContent value="my-claims">
                    <ClaimsTable claims={myClaims} showEmployee={false} onDelete={deleteClaim} />
                </TabsContent>

                {/* My Mileage */}
                <TabsContent value="my-mileage">
                    <MileageTable claims={myMileage} showEmployee={false} />
                </TabsContent>

                {/* Approvals */}
                {isManager && (
                    <TabsContent value="approvals">
                        <ClaimsTable claims={pendingApprovals} showEmployee onUpdate={updateStatus} />
                    </TabsContent>
                )}

                {/* All Claims */}
                {isManager && (
                    <TabsContent value="all">
                        <ClaimsTable claims={claims} showEmployee onUpdate={updateStatus} onDelete={deleteClaim} />
                    </TabsContent>
                )}
            </Tabs>

            {/* New Claim Dialog */}
            <Dialog open={claimDialog} onOpenChange={setClaimDialog}>
                <DialogContent className="max-w-lg">
                    <DialogHeader><DialogTitle><Receipt className="inline w-4 h-4 mr-1" /> New Expense Claim</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                        <div><Label>Title *</Label><Input value={claimForm.title} onChange={e => setClaimForm(f => ({ ...f, title: e.target.value }))} placeholder="e.g. Train to London client meeting" /></div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label>Category</Label>
                                <Select value={claimForm.category} onValueChange={v => setClaimForm(f => ({ ...f, category: v }))}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>{CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                                </Select>
                            </div>
                            <div><Label>Date *</Label><Input type="date" value={claimForm.expense_date} onChange={e => setClaimForm(f => ({ ...f, expense_date: e.target.value }))} /></div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label>Amount (£) *</Label><Input type="number" step="0.01" min="0" value={claimForm.amount} onChange={e => setClaimForm(f => ({ ...f, amount: e.target.value }))} placeholder="0.00" /></div>
                            <div><Label>Receipt URL (optional)</Label><Input value={claimForm.receipt_url} onChange={e => setClaimForm(f => ({ ...f, receipt_url: e.target.value }))} placeholder="https://..." /></div>
                        </div>
                        <div><Label>Description</Label><textarea className="w-full border rounded p-2 text-sm bg-background" rows={2} value={claimForm.description} onChange={e => setClaimForm(f => ({ ...f, description: e.target.value }))} placeholder="Additional details..." /></div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setClaimDialog(false)}>Cancel</Button>
                        <Button onClick={submitClaim} disabled={claimSaving}>{claimSaving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null} Submit Claim</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Mileage Dialog */}
            <Dialog open={mileageDialog} onOpenChange={setMileageDialog}>
                <DialogContent className="max-w-lg">
                    <DialogHeader><DialogTitle><Car className="inline w-4 h-4 mr-1" /> Log Mileage Claim</DialogTitle></DialogHeader>
                    <p className="text-xs text-muted-foreground">HMRC approved rates: Car 45p/mile (first 10,000), 25p thereafter · Bike 20p/mile</p>
                    <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label>Journey Date *</Label><Input type="date" value={mileageForm.journey_date} onChange={e => setMileageForm(f => ({ ...f, journey_date: e.target.value }))} /></div>
                            <div>
                                <Label>Vehicle</Label>
                                <Select value={mileageForm.vehicle_type} onValueChange={v => setMileageForm(f => ({ ...f, vehicle_type: v }))}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="car"><Car className="inline w-3 h-3 mr-1" />Car</SelectItem>
                                        <SelectItem value="bike"><Bike className="inline w-3 h-3 mr-1" />Motorbike</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div><Label>From *</Label><Input value={mileageForm.from_location} onChange={e => setMileageForm(f => ({ ...f, from_location: e.target.value }))} placeholder="Starting location" /></div>
                        <div><Label>To *</Label><Input value={mileageForm.to_location} onChange={e => setMileageForm(f => ({ ...f, to_location: e.target.value }))} placeholder="Destination" /></div>
                        <div className="grid grid-cols-2 gap-3">
                            <div><Label>Miles *</Label><Input type="number" step="0.1" min="0" value={mileageForm.miles} onChange={e => setMileageForm(f => ({ ...f, miles: e.target.value }))} placeholder="0.0" /></div>
                            <div><Label>YTD Miles (for rate calc)</Label><Input type="number" step="1" min="0" value={mileageForm.total_miles_ytd} onChange={e => setMileageForm(f => ({ ...f, total_miles_ytd: e.target.value }))} placeholder="0" /></div>
                        </div>
                        <div><Label>Purpose *</Label><Input value={mileageForm.purpose} onChange={e => setMileageForm(f => ({ ...f, purpose: e.target.value }))} placeholder="e.g. Client visit — Acme Ltd" /></div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setMileageDialog(false)}>Cancel</Button>
                        <Button onClick={submitMileage} disabled={mileageSaving}>{mileageSaving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null} Submit Mileage</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

function ClaimsTable({ claims, showEmployee, onUpdate, onDelete }) {
    if (claims.length === 0) return <p className="text-sm text-muted-foreground text-center py-10">No claims found.</p>;
    return (
        <div className="space-y-2 mt-3">
            {claims.map(c => (
                <Card key={c.claim_id} className="p-4">
                    <div className="flex items-start justify-between gap-3 flex-wrap">
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                                <p className="font-medium text-sm">{c.title}</p>
                                <Badge variant="outline" className="text-xs">{c.category}</Badge>
                                <StatusBadge status={c.status} />
                            </div>
                            {showEmployee && <p className="text-xs text-muted-foreground mt-0.5">{c.employee_name} · {c.employee_email}</p>}
                            <p className="text-xs text-muted-foreground">{c.expense_date}{c.description ? ` · ${c.description}` : ''}</p>
                        </div>
                        <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-sm">£{Number(c.amount).toFixed(2)}</span>
                            {onUpdate && c.status === 'pending' && (
                                <>
                                    <Button size="sm" variant="outline" className="text-emerald-700 border-emerald-300" onClick={() => onUpdate(c.claim_id, 'approved')}><CheckCircle className="w-3 h-3 mr-1" />Approve</Button>
                                    <Button size="sm" variant="outline" className="text-rose-700 border-rose-300" onClick={() => onUpdate(c.claim_id, 'declined')}><XCircle className="w-3 h-3 mr-1" />Decline</Button>
                                </>
                            )}
                            {onUpdate && c.status === 'approved' && (
                                <Button size="sm" variant="outline" className="text-indigo-700 border-indigo-300" onClick={() => onUpdate(c.claim_id, 'paid')}><PoundSterling className="w-3 h-3 mr-1" />Mark Paid</Button>
                            )}
                            {onDelete && c.status === 'pending' && (
                                <Button size="sm" variant="ghost" onClick={() => onDelete(c.claim_id)}><Trash2 className="w-3 h-3 text-rose-500" /></Button>
                            )}
                        </div>
                    </div>
                </Card>
            ))}
        </div>
    );
}

function MileageTable({ claims, showEmployee }) {
    if (claims.length === 0) return <p className="text-sm text-muted-foreground text-center py-10">No mileage claims found.</p>;
    return (
        <div className="space-y-2 mt-3">
            {claims.map(m => (
                <Card key={m.mileage_claim_id} className="p-4">
                    <div className="flex items-start justify-between gap-3 flex-wrap">
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                                <Car className="w-4 h-4 text-muted-foreground" />
                                <p className="font-medium text-sm">{m.from_location} → {m.to_location}</p>
                                <StatusBadge status={m.status} />
                            </div>
                            {showEmployee && <p className="text-xs text-muted-foreground">{m.employee_name}</p>}
                            <p className="text-xs text-muted-foreground">{m.journey_date} · {m.miles} miles · {m.purpose}</p>
                        </div>
                        <div className="text-right">
                            <p className="font-bold text-sm">£{Number(m.amount).toFixed(2)}</p>
                            <p className="text-xs text-muted-foreground">{m.rate_ppm}p/mile</p>
                        </div>
                    </div>
                </Card>
            ))}
        </div>
    );
}
