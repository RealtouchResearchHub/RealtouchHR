import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { 
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '../ui/dialog';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { 
    Plus, 
    CreditCard,
    ArrowRight,
    CheckCircle2,
    AlertTriangle,
    FileText,
    Download,
    Eye
} from 'lucide-react';
import { cn, formatCurrency, formatDate, getStatusColor, getComplianceColor } from '../../lib/utils';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const payrollSteps = [
    { id: 'prepare', label: 'Prepare', description: 'Review employee data' },
    { id: 'validate', label: 'Validate', description: 'Check compliance' },
    { id: 'preview', label: 'Preview', description: 'Review payslips' },
    { id: 'approve', label: 'Approve', description: 'Final approval' },
    { id: 'export', label: 'Export', description: 'Download reports' }
];

export default function PayrollPage() {
    const navigate = useNavigate();
    const [payRuns, setPayRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [formData, setFormData] = useState({
        period_start: '',
        period_end: '',
        pay_date: ''
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        fetchPayRuns();
    }, []);

    const fetchPayRuns = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/payroll/runs`, { withCredentials: true });
            setPayRuns(response.data);
        } catch (error) {
            toast.error('Failed to load pay runs');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            const response = await axios.post(`${API_URL}/api/payroll/runs`, formData, { withCredentials: true });
            toast.success('Pay run created successfully');
            setDialogOpen(false);
            setFormData({ period_start: '', period_end: '', pay_date: '' });
            navigate(`/payroll/${response.data.payrun_id}`);
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to create pay run');
        } finally {
            setSubmitting(false);
        }
    };

    const getStepIndex = (status) => {
        switch (status) {
            case 'draft': return 0;
            case 'validated': return 1;
            case 'previewed': return 2;
            case 'approved': return 3;
            case 'exported': return 4;
            default: return 0;
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
        <div className="space-y-6" data-testid="payroll-page">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Payroll</h1>
                    <p className="text-muted-foreground mt-1">Manage pay runs and generate payslips</p>
                </div>
                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                    <DialogTrigger asChild>
                        <Button className="bg-indigo-600 hover:bg-indigo-700" data-testid="create-payrun-btn">
                            <Plus className="w-4 h-4 mr-2" />
                            New Pay Run
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Create New Pay Run</DialogTitle>
                            <DialogDescription>
                                Start a new payroll run for your employees
                            </DialogDescription>
                        </DialogHeader>
                        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="period_start">Period Start</Label>
                                    <Input
                                        id="period_start"
                                        type="date"
                                        value={formData.period_start}
                                        onChange={(e) => setFormData({ ...formData, period_start: e.target.value })}
                                        required
                                        data-testid="input-period-start"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="period_end">Period End</Label>
                                    <Input
                                        id="period_end"
                                        type="date"
                                        value={formData.period_end}
                                        onChange={(e) => setFormData({ ...formData, period_end: e.target.value })}
                                        required
                                        data-testid="input-period-end"
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="pay_date">Pay Date</Label>
                                <Input
                                    id="pay_date"
                                    type="date"
                                    value={formData.pay_date}
                                    onChange={(e) => setFormData({ ...formData, pay_date: e.target.value })}
                                    required
                                    data-testid="input-pay-date"
                                />
                            </div>
                            <div className="flex justify-end gap-3 mt-6">
                                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                                    Cancel
                                </Button>
                                <Button type="submit" disabled={submitting} data-testid="submit-payrun-btn">
                                    {submitting ? 'Creating...' : 'Create Pay Run'}
                                </Button>
                            </div>
                        </form>
                    </DialogContent>
                </Dialog>
            </div>

            {/* Guided Flow Info */}
            <Card className="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30 border-indigo-100 dark:border-indigo-900/50">
                <CardContent className="p-6">
                    <h3 className="font-semibold text-lg mb-4">Guided Payroll Flow</h3>
                    <div className="flex items-center justify-between">
                        {payrollSteps.map((step, index) => (
                            <React.Fragment key={step.id}>
                                <div className="flex flex-col items-center">
                                    <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center text-indigo-600 font-medium">
                                        {index + 1}
                                    </div>
                                    <span className="text-sm font-medium mt-2">{step.label}</span>
                                    <span className="text-xs text-muted-foreground">{step.description}</span>
                                </div>
                                {index < payrollSteps.length - 1 && (
                                    <ArrowRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                                )}
                            </React.Fragment>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Pay Runs List */}
            {payRuns.length === 0 ? (
                <Card>
                    <CardContent className="py-16 text-center">
                        <CreditCard className="w-16 h-16 mx-auto text-muted-foreground/50" />
                        <h3 className="mt-4 text-lg font-semibold">No pay runs yet</h3>
                        <p className="text-muted-foreground mt-1">
                            Create your first pay run to start processing payroll
                        </p>
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-4">
                    {payRuns.map((run) => {
                        const stepIndex = getStepIndex(run.status);
                        const progress = ((stepIndex + 1) / payrollSteps.length) * 100;
                        
                        return (
                            <Card 
                                key={run.payrun_id}
                                className="hover:shadow-md transition-all cursor-pointer"
                                onClick={() => navigate(`/payroll/${run.payrun_id}`)}
                                data-testid={`payrun-card-${run.payrun_id}`}
                            >
                                <CardContent className="p-6">
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <div className="flex items-center gap-3">
                                                <h3 className="font-semibold text-lg">
                                                    Pay Period: {formatDate(run.period_start)} - {formatDate(run.period_end)}
                                                </h3>
                                                <Badge className={getStatusColor(run.status)}>{run.status}</Badge>
                                            </div>
                                            <p className="text-sm text-muted-foreground mt-1">
                                                Pay Date: {formatDate(run.pay_date)} • {run.employee_count} employees
                                            </p>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-2xl font-bold font-['Plus_Jakarta_Sans']">
                                                {formatCurrency(run.total_net)}
                                            </p>
                                            <p className="text-sm text-muted-foreground">Net Pay</p>
                                        </div>
                                    </div>

                                    <div className="mt-4 grid grid-cols-4 gap-4 text-sm">
                                        <div>
                                            <p className="text-muted-foreground">Gross</p>
                                            <p className="font-medium">{formatCurrency(run.total_gross)}</p>
                                        </div>
                                        <div>
                                            <p className="text-muted-foreground">Tax (PAYE)</p>
                                            <p className="font-medium">{formatCurrency(run.total_tax)}</p>
                                        </div>
                                        <div>
                                            <p className="text-muted-foreground">NI</p>
                                            <p className="font-medium">{formatCurrency(run.total_ni)}</p>
                                        </div>
                                        <div>
                                            <p className="text-muted-foreground">Compliance</p>
                                            <p className={cn("font-medium", getComplianceColor(run.compliance_score))}>
                                                {run.compliance_score}%
                                            </p>
                                        </div>
                                    </div>

                                    <div className="mt-4">
                                        <div className="flex items-center justify-between text-sm mb-2">
                                            <span className="text-muted-foreground">Progress</span>
                                            <span className="font-medium">{payrollSteps[stepIndex].label}</span>
                                        </div>
                                        <Progress value={progress} className="h-2" />
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
