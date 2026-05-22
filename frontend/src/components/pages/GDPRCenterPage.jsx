import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Alert, AlertDescription } from '../ui/alert';
import { toast } from 'sonner';
import { Download, Shield, AlertTriangle, FileLock2, Trash2, CheckCircle2, XCircle, ScanLine, Loader2 } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }, withCredentials: true });

export default function GDPRCenterPage() {
    const [tab, setTab] = useState('mydata');
    const [overview, setOverview] = useState(null);
    const [erasures, setErasures] = useState([]);
    const [exportPreview, setExportPreview] = useState(null);
    const [loading, setLoading] = useState(false);
    const [erasureReason, setErasureReason] = useState('');
    const [erasureDialog, setErasureDialog] = useState(false);
    const [processDialog, setProcessDialog] = useState(null); // {request_id, ...}
    const [processNotes, setProcessNotes] = useState('');

    const load = async () => {
        try {
            const [ovr, er] = await Promise.allSettled([
                axios.get(`${API_URL}/api/gdpr/overview`, auth()),
                axios.get(`${API_URL}/api/gdpr/erasure`, auth()),
            ]);
            if (ovr.status === 'fulfilled') setOverview(ovr.value.data);
            if (er.status === 'fulfilled') setErasures(er.value.data || []);
        } catch (e) { /* ignore */ }
    };

    useEffect(() => { load(); }, []);

    const previewMyData = async () => {
        setLoading(true);
        try {
            const res = await axios.get(`${API_URL}/api/gdpr/my-data`, auth());
            setExportPreview(res.data);
        } catch (e) {
            toast.error(e.response?.data?.detail || 'Failed to fetch data');
        } finally { setLoading(false); }
    };

    const downloadMyData = async () => {
        setLoading(true);
        try {
            const res = await axios.get(`${API_URL}/api/gdpr/my-data/download`, { ...auth(), responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const a = document.createElement('a');
            a.href = url;
            a.download = `realtouchhr_data_export_${new Date().toISOString().slice(0,10)}.json`;
            a.click();
            window.URL.revokeObjectURL(url);
            toast.success('Export downloaded');
        } catch (e) {
            toast.error('Download failed');
        } finally { setLoading(false); }
    };

    const submitErasure = async () => {
        try {
            await axios.post(`${API_URL}/api/gdpr/erasure`, { reason: erasureReason }, auth());
            toast.success('Erasure request submitted. HR/Admin will review.');
            setErasureDialog(false);
            setErasureReason('');
            load();
        } catch (e) {
            toast.error(e.response?.data?.detail || 'Failed to submit');
        }
    };

    const processErasure = async (action) => {
        if (!processDialog) return;
        try {
            await axios.post(
                `${API_URL}/api/gdpr/erasure/${processDialog.request_id}/process`,
                { action, notes: processNotes || null },
                auth()
            );
            toast.success(`Request ${action.replace('approve_', '')}`);
            setProcessDialog(null);
            setProcessNotes('');
            load();
        } catch (e) {
            toast.error(e.response?.data?.detail || 'Failed');
        }
    };

    return (
        <div className="space-y-6" data-testid="gdpr-center-page">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">GDPR / Data Protection Centre</h1>
                    <p className="text-muted-foreground mt-1">UK Data Protection Act 2018 — your rights under Articles 15 (access) & 17 (erasure)</p>
                </div>
                <Badge variant="outline" className="text-indigo-600 border-indigo-300"><Shield className="w-3 h-3 mr-1" />Compliance Centre</Badge>
            </div>

            <Tabs value={tab} onValueChange={setTab}>
                <TabsList>
                    <TabsTrigger value="mydata" data-testid="tab-mydata"><FileLock2 className="w-4 h-4 mr-2" />My Data</TabsTrigger>
                    <TabsTrigger value="erasure" data-testid="tab-erasure"><Trash2 className="w-4 h-4 mr-2" />Right to be Forgotten</TabsTrigger>
                    <TabsTrigger value="overview" data-testid="tab-overview"><ScanLine className="w-4 h-4 mr-2" />Company Overview</TabsTrigger>
                </TabsList>

                <TabsContent value="mydata" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Download your personal data</CardTitle>
                            <CardDescription>Get a complete JSON export of every piece of personal data we hold about you.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <Alert>
                                <Shield className="h-4 w-4" />
                                <AlertDescription>
                                    Under UK GDPR Article 15, you have the right to receive a copy of your personal data. Sensitive credentials (password hashes, 2FA secrets) are excluded for security.
                                </AlertDescription>
                            </Alert>
                            <div className="flex flex-wrap gap-3">
                                <Button onClick={previewMyData} variant="outline" disabled={loading} data-testid="preview-data-btn">
                                    {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <ScanLine className="w-4 h-4 mr-2" />}
                                    Preview
                                </Button>
                                <Button onClick={downloadMyData} disabled={loading} data-testid="download-data-btn">
                                    <Download className="w-4 h-4 mr-2" />
                                    Download JSON
                                </Button>
                            </div>
                            {exportPreview && (
                                <div className="mt-4 p-4 rounded-lg bg-muted">
                                    <p className="text-sm font-medium mb-2">Export Summary</p>
                                    <p className="text-xs text-muted-foreground">Export ID: {exportPreview.export_id}</p>
                                    <p className="text-xs text-muted-foreground mb-2">Generated: {new Date(exportPreview.generated_at).toLocaleString('en-GB')}</p>
                                    <p className="text-sm font-medium">Data Categories ({exportPreview.summary?.total_categories || 0}):</p>
                                    <div className="flex flex-wrap gap-2 mt-1">
                                        {(exportPreview.summary?.categories || []).map(c => (
                                            <Badge key={c} variant="secondary" className="text-xs">{c.replace('_', ' ')}</Badge>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="erasure" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Right to erasure (Article 17)</CardTitle>
                            <CardDescription>Request that we delete or anonymise your personal data. Records required by HMRC will be retained (6 years).</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Alert variant="destructive" className="mb-4">
                                <AlertTriangle className="h-4 w-4" />
                                <AlertDescription>
                                    This action is reviewed by HR/Admin. Anonymisation is irreversible. Payroll history will be retained per HMRC PAYE rules (6 years).
                                </AlertDescription>
                            </Alert>
                            <Button onClick={() => setErasureDialog(true)} variant="destructive" data-testid="submit-erasure-btn">
                                <Trash2 className="w-4 h-4 mr-2" />
                                Submit Erasure Request
                            </Button>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Pending requests (HR/Admin)</CardTitle>
                            <CardDescription>Review and process incoming erasure requests.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {erasures.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No erasure requests.</p>
                            ) : (
                                <div className="space-y-2">
                                    {erasures.map(r => (
                                        <div key={r.request_id} className="p-4 border rounded-lg flex items-start justify-between" data-testid={`erasure-row-${r.request_id}`}>
                                            <div>
                                                <p className="font-medium">{r.requester_email}</p>
                                                <p className="text-xs text-muted-foreground">{new Date(r.created_at).toLocaleString('en-GB')}</p>
                                                {r.reason && <p className="text-sm mt-1">{r.reason}</p>}
                                                <Badge variant={r.status === 'pending' ? 'default' : r.status.startsWith('completed') ? 'secondary' : 'outline'} className="mt-2">
                                                    {r.status}
                                                </Badge>
                                            </div>
                                            {r.status === 'pending' && (
                                                <Button size="sm" variant="outline" onClick={() => setProcessDialog(r)} data-testid={`process-erasure-${r.request_id}`}>
                                                    Review
                                                </Button>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="overview" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Personal data held by your company</CardTitle>
                            <CardDescription>Counts per data category for record-keeping and DPIA purposes.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {overview ? (
                                <>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="gdpr-counts-grid">
                                        {Object.entries(overview.counts || {}).map(([k, v]) => (
                                            <div key={k} className="p-3 rounded-lg border bg-card">
                                                <p className="text-xs text-muted-foreground capitalize">{k.replace('_', ' ')}</p>
                                                <p className="text-2xl font-semibold">{v}</p>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="mt-6">
                                        <h4 className="font-semibold mb-2">Retention Policy</h4>
                                        <ul className="text-sm space-y-1 text-muted-foreground">
                                            {Object.entries(overview.retention_policy || {}).map(([k, v]) => (
                                                <li key={k}>• <strong>{k.replace('_', ' ')}</strong>: {v}</li>
                                            ))}
                                        </ul>
                                    </div>
                                </>
                            ) : (
                                <p className="text-sm text-muted-foreground">HR/Admin only.</p>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            <Dialog open={erasureDialog} onOpenChange={setErasureDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Submit Erasure Request</DialogTitle>
                    </DialogHeader>
                    <Textarea
                        placeholder="Reason (optional)"
                        value={erasureReason}
                        onChange={(e) => setErasureReason(e.target.value)}
                        data-testid="erasure-reason-input"
                    />
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setErasureDialog(false)}>Cancel</Button>
                        <Button variant="destructive" onClick={submitErasure} data-testid="submit-erasure-confirm-btn">Submit Request</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={!!processDialog} onOpenChange={(o) => !o && setProcessDialog(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Process Erasure Request</DialogTitle>
                    </DialogHeader>
                    {processDialog && (
                        <div className="space-y-3">
                            <p className="text-sm"><strong>Requester:</strong> {processDialog.requester_email}</p>
                            <p className="text-sm"><strong>Reason:</strong> {processDialog.reason || 'Not provided'}</p>
                            <Textarea
                                placeholder="Notes (optional)"
                                value={processNotes}
                                onChange={(e) => setProcessNotes(e.target.value)}
                                data-testid="process-notes-input"
                            />
                        </div>
                    )}
                    <DialogFooter className="flex-col sm:flex-row gap-2">
                        <Button variant="outline" onClick={() => processErasure('reject')} data-testid="erasure-reject-btn">
                            <XCircle className="w-4 h-4 mr-2" />Reject
                        </Button>
                        <Button variant="secondary" onClick={() => processErasure('approve_anonymize')} data-testid="erasure-anonymize-btn">
                            <Shield className="w-4 h-4 mr-2" />Anonymise (recommended)
                        </Button>
                        <Button variant="destructive" onClick={() => processErasure('approve_delete')} data-testid="erasure-delete-btn">
                            <Trash2 className="w-4 h-4 mr-2" />Full Delete
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
