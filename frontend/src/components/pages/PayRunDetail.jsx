import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '../ui/table';
import { 
    ArrowLeft,
    ArrowRight,
    CheckCircle2,
    AlertTriangle,
    Download,
    FileText
} from 'lucide-react';
import { cn, formatCurrency, formatDate, getStatusColor, getComplianceColor } from '../../lib/utils';
import { toast } from 'sonner';
import PaywallModal from '../shared/PaywallModal';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const payrollSteps = [
    { id: 'draft', label: 'Prepare', nextStatus: 'validated' },
    { id: 'validated', label: 'Validate', nextStatus: 'previewed' },
    { id: 'previewed', label: 'Preview', nextStatus: 'approved' },
    { id: 'approved', label: 'Approve', nextStatus: 'exported' },
    { id: 'exported', label: 'Export', nextStatus: null }
];

export default function PayRunDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [payRun, setPayRun] = useState(null);
    const [payslips, setPayslips] = useState([]);
    const [loading, setLoading] = useState(true);
    const [processing, setProcessing] = useState(false);
    const [paywallOpen, setPaywallOpen] = useState(false);
    const [paywallMessage, setPaywallMessage] = useState('');
    const [paywallResolver, setPaywallResolver] = useState(null);

    const handlePaywallChoice = (choice) => {
        setPaywallOpen(false);
        if (paywallResolver) {
            paywallResolver(choice);
            setPaywallResolver(null);
        }
    };

    useEffect(() => {
        fetchData();
    }, [id]);

    // Resume a pending payslip download after returning from Stripe
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const sessionId = params.get('session_id');
        const status = params.get('status');
        if (sessionId && status === 'success') {
            (async () => {
                const { resumePendingPayslipDownload } = await import('../../lib/payslipDownload');
                await resumePendingPayslipDownload(sessionId);
                // Clean up URL
                window.history.replaceState({}, '', window.location.pathname);
            })();
        }
    }, []);

    const fetchData = async () => {
        try {
            const [runRes, slipsRes] = await Promise.all([
                axios.get(`${API_URL}/api/payroll/runs/${id}`, { withCredentials: true }),
                axios.get(`${API_URL}/api/payroll/runs/${id}/payslips`, { withCredentials: true })
            ]);
            setPayRun(runRes.data);
            setPayslips(slipsRes.data);
        } catch (error) {
            toast.error('Failed to load pay run details');
            navigate('/payroll');
        } finally {
            setLoading(false);
        }
    };

    const handleAdvanceStep = async () => {
        const currentStep = payrollSteps.find(s => s.id === payRun.status);
        if (!currentStep?.nextStatus) return;

        setProcessing(true);
        try {
            await axios.put(`${API_URL}/api/payroll/runs/${id}`, 
                { status: currentStep.nextStatus, reason: `Advanced to ${currentStep.nextStatus}` },
                { withCredentials: true }
            );
            toast.success(`Pay run ${currentStep.nextStatus}`);
            fetchData();
        } catch (error) {
            toast.error('Failed to update pay run');
        } finally {
            setProcessing(false);
        }
    };

    const handleDownloadPayslip = async (employeeId) => {
        const { downloadPayslipWithPaywall } = await import('../../lib/payslipDownload');
        await downloadPayslipWithPaywall({
            payrunId: id,
            employeeId,
            filename: `payslip_${employeeId}.pdf`,
            onPaywall: (message) => new Promise((resolve) => {
                setPaywallMessage(message);
                setPaywallResolver(() => resolve);
                setPaywallOpen(true);
            }),
        });
    };

    const handleExportFPS = async () => {
        try {
            const response = await axios.get(
                `${API_URL}/api/payroll/runs/${id}/export/fps`,
                { withCredentials: true, responseType: 'blob' }
            );
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `fps_export_${payRun.period_end}.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
            toast.success('FPS export downloaded');
        } catch (error) {
            toast.error('Failed to export FPS');
        }
    };

    const handleExportEPS = async () => {
        try {
            const response = await axios.get(
                `${API_URL}/api/payroll/runs/${id}/export/eps`,
                { withCredentials: true, responseType: 'blob' }
            );
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `eps_export_${payRun.period_end}.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
            toast.success('EPS export downloaded');
        } catch (error) {
            toast.error('Failed to export EPS');
        }
    };

    const handleExportP32 = async () => {
        try {
            const response = await axios.get(
                `${API_URL}/api/payroll/runs/${id}/export/p32`,
                { withCredentials: true, responseType: 'blob' }
            );
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `p32_report_${payRun.period_end}.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
            toast.success('P32 report downloaded');
        } catch (error) {
            toast.error('Failed to export P32');
        }
    };

    const getStepIndex = (status) => {
        return payrollSteps.findIndex(s => s.id === status);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!payRun) return null;

    const stepIndex = getStepIndex(payRun.status);
    const currentStep = payrollSteps[stepIndex];
    const progress = ((stepIndex + 1) / payrollSteps.length) * 100;

    return (
        <div className="space-y-6" data-testid="payrun-detail-page">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => navigate('/payroll')} data-testid="back-btn">
                    <ArrowLeft className="w-5 h-5" />
                </Button>
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Pay Run Details</h1>
                    <p className="text-muted-foreground">
                        {formatDate(payRun.period_start)} - {formatDate(payRun.period_end)}
                    </p>
                </div>
            </div>

            {/* Progress Steps */}
            <Card>
                <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-6">
                        {payrollSteps.map((step, index) => (
                            <React.Fragment key={step.id}>
                                <div className="flex flex-col items-center">
                                    <div className={cn(
                                        "w-10 h-10 rounded-full flex items-center justify-center font-medium transition-all",
                                        index <= stepIndex 
                                            ? "bg-indigo-600 text-white" 
                                            : "bg-muted text-muted-foreground"
                                    )}>
                                        {index < stepIndex ? (
                                            <CheckCircle2 className="w-5 h-5" />
                                        ) : (
                                            index + 1
                                        )}
                                    </div>
                                    <span className={cn(
                                        "text-sm font-medium mt-2",
                                        index <= stepIndex ? "text-foreground" : "text-muted-foreground"
                                    )}>
                                        {step.label}
                                    </span>
                                </div>
                                {index < payrollSteps.length - 1 && (
                                    <div className={cn(
                                        "flex-1 h-1 mx-2 rounded",
                                        index < stepIndex ? "bg-indigo-600" : "bg-muted"
                                    )} />
                                )}
                            </React.Fragment>
                        ))}
                    </div>
                    
                    {currentStep?.nextStatus && (
                        <div className="flex justify-center">
                            <Button 
                                onClick={handleAdvanceStep}
                                disabled={processing}
                                className="bg-indigo-600 hover:bg-indigo-700"
                                data-testid="advance-step-btn"
                            >
                                {processing ? 'Processing...' : `Proceed to ${payrollSteps[stepIndex + 1]?.label}`}
                                <ArrowRight className="w-4 h-4 ml-2" />
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <Card>
                    <CardContent className="p-4">
                        <p className="text-sm text-muted-foreground">Employees</p>
                        <p className="text-2xl font-bold">{payRun.employee_count}</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4">
                        <p className="text-sm text-muted-foreground">Gross Pay</p>
                        <p className="text-2xl font-bold">{formatCurrency(payRun.total_gross)}</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4">
                        <p className="text-sm text-muted-foreground">Tax (PAYE)</p>
                        <p className="text-2xl font-bold">{formatCurrency(payRun.total_tax)}</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4">
                        <p className="text-sm text-muted-foreground">NI</p>
                        <p className="text-2xl font-bold">{formatCurrency(payRun.total_ni)}</p>
                    </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-emerald-50 to-white dark:from-emerald-950/30 dark:to-background">
                    <CardContent className="p-4">
                        <p className="text-sm text-muted-foreground">Net Pay</p>
                        <p className="text-2xl font-bold text-emerald-600">{formatCurrency(payRun.total_net)}</p>
                    </CardContent>
                </Card>
            </div>

            {/* Compliance Status */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        {payRun.compliance_score >= 100 ? (
                            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                        ) : (
                            <AlertTriangle className="w-5 h-5 text-amber-600" />
                        )}
                        Compliance Status
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center gap-4">
                        <div className={cn("text-4xl font-bold", getComplianceColor(payRun.compliance_score))}>
                            {payRun.compliance_score}%
                        </div>
                        <div className="flex-1">
                            <Progress value={payRun.compliance_score} className="h-3" />
                        </div>
                    </div>
                    {payRun.compliance_score < 100 && (
                        <p className="mt-4 text-muted-foreground">
                            Some employees have missing payroll data. Review and complete their profiles before finalising.
                        </p>
                    )}
                </CardContent>
            </Card>

            {/* HMRC Exports */}
            <Card data-testid="hmrc-exports">
                <CardHeader>
                    <CardTitle>HMRC Export Pack</CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground mb-4">
                        Download HMRC-ready reports. Note: These are CSV exports for review. RTI submission integration coming in Stage 2.
                    </p>
                    <div className="flex flex-wrap gap-3">
                        <Button variant="outline" onClick={handleExportFPS} data-testid="export-fps-btn">
                            <Download className="w-4 h-4 mr-2" />
                            FPS (Full Payment Submission)
                        </Button>
                        <Button variant="outline" onClick={handleExportEPS} data-testid="export-eps-btn">
                            <Download className="w-4 h-4 mr-2" />
                            EPS (Employer Payment Summary)
                        </Button>
                        <Button variant="outline" onClick={handleExportP32} data-testid="export-p32-btn">
                            <Download className="w-4 h-4 mr-2" />
                            P32 Report
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Payslips Table */}
            <Card data-testid="payslips-table">
                <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle>Payslips Preview</CardTitle>
                </CardHeader>
                <CardContent>
                    {payslips.length === 0 ? (
                        <p className="text-center py-8 text-muted-foreground">No payslips generated</p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Employee</TableHead>
                                    <TableHead className="text-right">Gross</TableHead>
                                    <TableHead className="text-right">Tax</TableHead>
                                    <TableHead className="text-right">NI</TableHead>
                                    <TableHead className="text-right">Pension</TableHead>
                                    <TableHead className="text-right">Net</TableHead>
                                    <TableHead></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {payslips.map((slip) => (
                                    <TableRow key={slip.employee_id}>
                                        <TableCell className="font-medium">{slip.employee_name}</TableCell>
                                        <TableCell className="text-right">{formatCurrency(slip.gross_pay)}</TableCell>
                                        <TableCell className="text-right">{formatCurrency(slip.tax_deduction)}</TableCell>
                                        <TableCell className="text-right">{formatCurrency(slip.ni_deduction)}</TableCell>
                                        <TableCell className="text-right">{formatCurrency(slip.pension_deduction)}</TableCell>
                                        <TableCell className="text-right font-semibold">{formatCurrency(slip.net_pay)}</TableCell>
                                        <TableCell>
                                            <Button 
                                                variant="ghost" 
                                                size="icon"
                                                onClick={() => handleDownloadPayslip(slip.employee_id)}
                                                data-testid={`download-payslip-${slip.employee_id}`}
                                            >
                                                <Download className="w-4 h-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            <PaywallModal
                open={paywallOpen}
                message={paywallMessage}
                onChoice={handlePaywallChoice}
            />
        </div>
    );
}
