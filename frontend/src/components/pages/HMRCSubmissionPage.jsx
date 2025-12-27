import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Switch } from '../ui/switch';
import { Label } from '../ui/label';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogFooter,
} from '../ui/dialog';
import { 
    Send,
    CheckCircle2,
    Clock,
    XCircle,
    AlertTriangle,
    FileText,
    Building2,
    RefreshCw
} from 'lucide-react';
import { cn, formatDateTime } from '../../lib/utils';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const statusColors = {
    draft: 'bg-slate-100 text-slate-700 dark:bg-slate-900/30 dark:text-slate-400',
    submitted: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    accepted: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    rejected: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400',
    pending: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
};

export default function HMRCSubmissionPage() {
    const [submissions, setSubmissions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [selectedPayrun, setSelectedPayrun] = useState(null);
    const [payRuns, setPayRuns] = useState([]);
    const [testMode, setTestMode] = useState(true);
    const [submissionType, setSubmissionType] = useState('FPS');

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [submissionsRes, payrunsRes] = await Promise.all([
                axios.get(`${API_URL}/api/hmrc/rti/submissions`, { withCredentials: true }),
                axios.get(`${API_URL}/api/payroll/runs`, { withCredentials: true })
            ]);
            setSubmissions(submissionsRes.data);
            setPayRuns(payrunsRes.data.filter(r => r.status === 'approved' || r.status === 'exported'));
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async () => {
        if (!selectedPayrun) {
            toast.error('Please select a pay run');
            return;
        }

        setSubmitting(true);
        try {
            const response = await axios.post(`${API_URL}/api/hmrc/rti/submit`, {
                payrun_id: selectedPayrun,
                submission_type: submissionType,
                test_mode: testMode
            }, { withCredentials: true });

            toast.success(response.data.message);
            setDialogOpen(false);
            fetchData();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Submission failed');
        } finally {
            setSubmitting(false);
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'accepted': return <CheckCircle2 className="w-4 h-4 text-emerald-600" />;
            case 'rejected': return <XCircle className="w-4 h-4 text-rose-600" />;
            case 'submitted':
            case 'pending': return <Clock className="w-4 h-4 text-amber-600" />;
            default: return <FileText className="w-4 h-4 text-slate-600" />;
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-6" data-testid="hmrc-submission-page">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">HMRC Submissions</h1>
                    <p className="text-muted-foreground mt-1">Submit and track RTI (Real Time Information) to HMRC</p>
                </div>
                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                    <DialogTrigger asChild>
                        <Button className="bg-indigo-600 hover:bg-indigo-700" data-testid="new-submission-btn">
                            <Send className="w-4 h-4 mr-2" />
                            New Submission
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Submit RTI to HMRC</DialogTitle>
                            <DialogDescription>
                                Submit payroll data to HMRC via Real Time Information
                            </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-6 py-4">
                            {/* Test Mode Toggle */}
                            <div className="flex items-center justify-between p-4 rounded-lg bg-amber-50 dark:bg-amber-950/30">
                                <div className="flex items-center gap-3">
                                    <AlertTriangle className="w-5 h-5 text-amber-600" />
                                    <div>
                                        <Label htmlFor="test-mode" className="text-amber-700 dark:text-amber-400">Test Mode</Label>
                                        <p className="text-xs text-amber-600 dark:text-amber-500">Simulate submission without sending to HMRC</p>
                                    </div>
                                </div>
                                <Switch 
                                    id="test-mode"
                                    checked={testMode}
                                    onCheckedChange={setTestMode}
                                    data-testid="test-mode-toggle"
                                />
                            </div>

                            {/* Submission Type */}
                            <div className="space-y-2">
                                <Label>Submission Type</Label>
                                <div className="grid grid-cols-2 gap-3">
                                    <button
                                        className={cn(
                                            "p-4 rounded-lg border-2 text-left transition-all",
                                            submissionType === 'FPS' 
                                                ? "border-indigo-600 bg-indigo-50 dark:bg-indigo-950/30" 
                                                : "border-border hover:border-indigo-300"
                                        )}
                                        onClick={() => setSubmissionType('FPS')}
                                        data-testid="submission-type-fps"
                                    >
                                        <p className="font-semibold">FPS</p>
                                        <p className="text-xs text-muted-foreground">Full Payment Submission</p>
                                    </button>
                                    <button
                                        className={cn(
                                            "p-4 rounded-lg border-2 text-left transition-all",
                                            submissionType === 'EPS' 
                                                ? "border-indigo-600 bg-indigo-50 dark:bg-indigo-950/30" 
                                                : "border-border hover:border-indigo-300"
                                        )}
                                        onClick={() => setSubmissionType('EPS')}
                                        data-testid="submission-type-eps"
                                    >
                                        <p className="font-semibold">EPS</p>
                                        <p className="text-xs text-muted-foreground">Employer Payment Summary</p>
                                    </button>
                                </div>
                            </div>

                            {/* Pay Run Selection */}
                            <div className="space-y-2">
                                <Label>Select Pay Run</Label>
                                {payRuns.length === 0 ? (
                                    <p className="text-sm text-muted-foreground">No approved pay runs available</p>
                                ) : (
                                    <div className="space-y-2 max-h-48 overflow-y-auto">
                                        {payRuns.map(run => (
                                            <button
                                                key={run.payrun_id}
                                                className={cn(
                                                    "w-full p-3 rounded-lg border text-left transition-all",
                                                    selectedPayrun === run.payrun_id 
                                                        ? "border-indigo-600 bg-indigo-50 dark:bg-indigo-950/30" 
                                                        : "border-border hover:border-indigo-300"
                                                )}
                                                onClick={() => setSelectedPayrun(run.payrun_id)}
                                            >
                                                <p className="font-medium">{run.period_start} to {run.period_end}</p>
                                                <p className="text-xs text-muted-foreground">
                                                    {run.employee_count} employees • £{run.total_gross.toLocaleString()} gross
                                                </p>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                            <Button 
                                onClick={handleSubmit}
                                disabled={submitting || !selectedPayrun}
                                className="bg-indigo-600 hover:bg-indigo-700"
                                data-testid="submit-rti-btn"
                            >
                                {submitting ? (
                                    <>
                                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                                        Submitting...
                                    </>
                                ) : (
                                    <>
                                        <Send className="w-4 h-4 mr-2" />
                                        {testMode ? 'Test Submit' : 'Submit to HMRC'}
                                    </>
                                )}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>

            {/* Info Banner */}
            <Alert>
                <Building2 className="w-4 h-4" />
                <AlertTitle>HMRC RTI Integration</AlertTitle>
                <AlertDescription>
                    Real Time Information (RTI) submissions are sent to HMRC each time you pay employees. 
                    This includes FPS (Full Payment Submission) and EPS (Employer Payment Summary).
                    <br /><br />
                    <strong>Note:</strong> Live HMRC submissions require Government Gateway credentials. 
                    Use Test Mode to validate your data before submitting.
                </AlertDescription>
            </Alert>

            {/* Submissions List */}
            <Card data-testid="submissions-list">
                <CardHeader>
                    <CardTitle>Submission History</CardTitle>
                    <CardDescription>Track all RTI submissions to HMRC</CardDescription>
                </CardHeader>
                <CardContent>
                    {submissions.length === 0 ? (
                        <div className="text-center py-12 text-muted-foreground">
                            <Send className="w-12 h-12 mx-auto opacity-50" />
                            <p className="mt-4">No submissions yet</p>
                            <p className="text-sm">Create a new submission to get started</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {submissions.map((submission) => (
                                <div 
                                    key={submission.submission_id}
                                    className="flex items-center justify-between p-4 rounded-lg border hover:bg-accent/50 transition-colors"
                                >
                                    <div className="flex items-center gap-4">
                                        <div className={cn("p-2 rounded-lg", statusColors[submission.status])}>
                                            {getStatusIcon(submission.status)}
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <p className="font-medium">{submission.submission_type}</p>
                                                {submission.test_mode && (
                                                    <Badge variant="outline" className="text-xs">Test</Badge>
                                                )}
                                            </div>
                                            <p className="text-sm text-muted-foreground">
                                                {submission.correlation_id}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <Badge className={statusColors[submission.status]}>
                                            {submission.status}
                                        </Badge>
                                        <p className="text-xs text-muted-foreground mt-1">
                                            {formatDateTime(submission.submitted_at)}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
