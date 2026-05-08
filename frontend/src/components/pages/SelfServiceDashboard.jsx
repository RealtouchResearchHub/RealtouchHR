import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Progress } from '../ui/progress';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '../ui/dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../ui/select';
import { Textarea } from '../ui/textarea';
import { 
    User,
    CreditCard,
    Calendar,
    Download,
    FileText,
    Plus,
    CheckCircle2,
    Clock,
    XCircle
} from 'lucide-react';
import { cn, formatCurrency, formatDate, getStatusColor } from '../../lib/utils';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const leaveTypes = [
    { value: 'annual', label: 'Annual Leave' },
    { value: 'sick', label: 'Sick Leave' },
    { value: 'personal', label: 'Personal Leave' },
    { value: 'other', label: 'Other' }
];

export default function SelfServiceDashboard() {
    const { user } = useAuth();
    const [profile, setProfile] = useState(null);
    const [payslips, setPayslips] = useState([]);
    const [leaveData, setLeaveData] = useState({ requests: [], balance: { annual: 25, used: 0, remaining: 25 } });
    const [loading, setLoading] = useState(true);
    const [leaveDialogOpen, setLeaveDialogOpen] = useState(false);
    const [leaveForm, setLeaveForm] = useState({
        leave_type: '',
        start_date: '',
        end_date: '',
        reason: ''
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [profileRes, payslipsRes, leaveRes] = await Promise.all([
                axios.get(`${API_URL}/api/self-service/profile`, { withCredentials: true }),
                axios.get(`${API_URL}/api/self-service/payslips`, { withCredentials: true }),
                axios.get(`${API_URL}/api/self-service/leave`, { withCredentials: true })
            ]);
            setProfile(profileRes.data);
            setPayslips(payslipsRes.data);
            setLeaveData(leaveRes.data);
        } catch (error) {
            console.error('Failed to load self-service data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadPayslip = async (payrunId) => {
        try {
            const response = await axios.get(
                `${API_URL}/api/self-service/payslips/${payrunId}/pdf`,
                { withCredentials: true, responseType: 'blob' }
            );
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `payslip_${payrunId}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            toast.success('Payslip downloaded');
        } catch (error) {
            const status = error.response?.status;
            let detail = '';
            if (error.response?.data instanceof Blob) {
                try { detail = JSON.parse(await error.response.data.text()).detail; }
                catch { detail = 'Download failed'; }
            } else {
                detail = error.response?.data?.detail || 'Download failed';
            }
            if (status === 402) {
                if (window.confirm(`${detail}\n\nProceed to Stripe to pay £5.00 for this payslip?`)) {
                    try {
                        const co = await axios.post(
                            `${API_URL}/api/payments/checkout/payslip`,
                            { payslip_id: payrunId, origin_url: window.location.origin },
                            { withCredentials: true }
                        );
                        if (co.data?.checkout_url) {
                            sessionStorage.setItem('pending_payslip_download', JSON.stringify({
                                payrunId, employeeId: 'self', filename: `payslip_${payrunId}.pdf`,
                                session_id: co.data.session_id, isSelfService: true,
                            }));
                            window.location.href = co.data.checkout_url;
                        }
                    } catch (e) {
                        toast.error(e.response?.data?.detail || 'Could not start checkout');
                    }
                }
            } else if (status === 403) {
                toast.error(detail || 'Downloads disabled during trial');
            } else {
                toast.error(detail);
            }
        }
    };

    const handleSubmitLeave = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await axios.post(`${API_URL}/api/self-service/leave`, leaveForm, { withCredentials: true });
            toast.success('Leave request submitted');
            setLeaveDialogOpen(false);
            setLeaveForm({ leave_type: '', start_date: '', end_date: '', reason: '' });
            fetchData();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to submit leave request');
        } finally {
            setSubmitting(false);
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
        <div className="space-y-6" data-testid="self-service-dashboard">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">My Dashboard</h1>
                <p className="text-muted-foreground mt-1">View your payslips, request leave, and manage your profile</p>
            </div>

            {/* Profile Card */}
            <Card className="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30">
                <CardContent className="p-6">
                    <div className="flex items-center gap-6">
                        <div className="w-20 h-20 rounded-full bg-indigo-600 flex items-center justify-center">
                            <span className="text-2xl font-bold text-white">
                                {profile?.first_name?.[0]}{profile?.last_name?.[0]}
                            </span>
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold">{profile?.first_name} {profile?.last_name}</h2>
                            <p className="text-muted-foreground">{profile?.job_title || 'Team Member'}</p>
                            <p className="text-sm text-muted-foreground">{profile?.department}</p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Quick Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                    <CardContent className="p-6">
                        <div className="flex items-center gap-4">
                            <div className="p-3 rounded-xl bg-emerald-100 dark:bg-emerald-900/30">
                                <Calendar className="w-6 h-6 text-emerald-600" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Leave Balance</p>
                                <p className="text-2xl font-bold">{leaveData.balance.remaining} days</p>
                            </div>
                        </div>
                        <Progress 
                            value={(leaveData.balance.used / leaveData.balance.annual) * 100} 
                            className="mt-4 h-2"
                        />
                        <p className="text-xs text-muted-foreground mt-2">
                            {leaveData.balance.used} of {leaveData.balance.annual} days used
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="p-6">
                        <div className="flex items-center gap-4">
                            <div className="p-3 rounded-xl bg-indigo-100 dark:bg-indigo-900/30">
                                <CreditCard className="w-6 h-6 text-indigo-600" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Latest Payslip</p>
                                <p className="text-2xl font-bold">
                                    {payslips.length > 0 ? formatCurrency(payslips[0].net_pay) : 'N/A'}
                                </p>
                            </div>
                        </div>
                        {payslips.length > 0 && (
                            <p className="text-xs text-muted-foreground mt-4">
                                Pay date: {formatDate(payslips[0].pay_date)}
                            </p>
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="p-6">
                        <div className="flex items-center gap-4">
                            <div className="p-3 rounded-xl bg-amber-100 dark:bg-amber-900/30">
                                <Clock className="w-6 h-6 text-amber-600" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Pending Requests</p>
                                <p className="text-2xl font-bold">
                                    {leaveData.requests.filter(r => r.status === 'pending').length}
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="payslips" className="space-y-6">
                <TabsList>
                    <TabsTrigger value="payslips">
                        <CreditCard className="w-4 h-4 mr-2" />
                        Payslips
                    </TabsTrigger>
                    <TabsTrigger value="leave">
                        <Calendar className="w-4 h-4 mr-2" />
                        Leave
                    </TabsTrigger>
                    <TabsTrigger value="profile">
                        <User className="w-4 h-4 mr-2" />
                        Profile
                    </TabsTrigger>
                </TabsList>

                {/* Payslips Tab */}
                <TabsContent value="payslips">
                    <Card>
                        <CardHeader>
                            <CardTitle>My Payslips</CardTitle>
                            <CardDescription>View and download your payslips</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {payslips.length === 0 ? (
                                <div className="text-center py-12 text-muted-foreground">
                                    <FileText className="w-12 h-12 mx-auto opacity-50" />
                                    <p className="mt-4">No payslips available yet</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {payslips.map((payslip) => (
                                        <div 
                                            key={payslip.payrun_id}
                                            className="flex items-center justify-between p-4 rounded-lg border hover:bg-accent/50 transition-colors"
                                        >
                                            <div className="flex items-center gap-4">
                                                <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/30">
                                                    <FileText className="w-5 h-5 text-indigo-600" />
                                                </div>
                                                <div>
                                                    <p className="font-medium">
                                                        {formatDate(payslip.period_start)} - {formatDate(payslip.period_end)}
                                                    </p>
                                                    <p className="text-sm text-muted-foreground">
                                                        Pay date: {formatDate(payslip.pay_date)}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4">
                                                <div className="text-right">
                                                    <p className="font-semibold">{formatCurrency(payslip.net_pay)}</p>
                                                    <p className="text-xs text-muted-foreground">Net Pay</p>
                                                </div>
                                                <Button 
                                                    variant="outline" 
                                                    size="sm"
                                                    onClick={() => handleDownloadPayslip(payslip.payrun_id)}
                                                    data-testid={`download-payslip-${payslip.payrun_id}`}
                                                >
                                                    <Download className="w-4 h-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Leave Tab */}
                <TabsContent value="leave">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle>Leave Requests</CardTitle>
                                <CardDescription>Request and track your leave</CardDescription>
                            </div>
                            <Dialog open={leaveDialogOpen} onOpenChange={setLeaveDialogOpen}>
                                <DialogTrigger asChild>
                                    <Button data-testid="request-leave-btn">
                                        <Plus className="w-4 h-4 mr-2" />
                                        Request Leave
                                    </Button>
                                </DialogTrigger>
                                <DialogContent>
                                    <DialogHeader>
                                        <DialogTitle>Request Leave</DialogTitle>
                                        <DialogDescription>Submit a new leave request</DialogDescription>
                                    </DialogHeader>
                                    <form onSubmit={handleSubmitLeave} className="space-y-4 mt-4">
                                        <div className="space-y-2">
                                            <Label>Leave Type</Label>
                                            <Select
                                                value={leaveForm.leave_type}
                                                onValueChange={(value) => setLeaveForm({ ...leaveForm, leave_type: value })}
                                            >
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select type" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {leaveTypes.map(type => (
                                                        <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="space-y-2">
                                                <Label>Start Date</Label>
                                                <Input
                                                    type="date"
                                                    value={leaveForm.start_date}
                                                    onChange={(e) => setLeaveForm({ ...leaveForm, start_date: e.target.value })}
                                                    required
                                                />
                                            </div>
                                            <div className="space-y-2">
                                                <Label>End Date</Label>
                                                <Input
                                                    type="date"
                                                    value={leaveForm.end_date}
                                                    onChange={(e) => setLeaveForm({ ...leaveForm, end_date: e.target.value })}
                                                    required
                                                />
                                            </div>
                                        </div>
                                        <div className="space-y-2">
                                            <Label>Reason (optional)</Label>
                                            <Textarea
                                                value={leaveForm.reason}
                                                onChange={(e) => setLeaveForm({ ...leaveForm, reason: e.target.value })}
                                                placeholder="Add any notes..."
                                            />
                                        </div>
                                        <div className="flex justify-end gap-3">
                                            <Button type="button" variant="outline" onClick={() => setLeaveDialogOpen(false)}>
                                                Cancel
                                            </Button>
                                            <Button type="submit" disabled={submitting}>
                                                {submitting ? 'Submitting...' : 'Submit Request'}
                                            </Button>
                                        </div>
                                    </form>
                                </DialogContent>
                            </Dialog>
                        </CardHeader>
                        <CardContent>
                            {leaveData.requests.length === 0 ? (
                                <div className="text-center py-12 text-muted-foreground">
                                    <Calendar className="w-12 h-12 mx-auto opacity-50" />
                                    <p className="mt-4">No leave requests</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {leaveData.requests.map((request) => (
                                        <div 
                                            key={request.leave_id}
                                            className="flex items-center justify-between p-4 rounded-lg border"
                                        >
                                            <div className="flex items-center gap-4">
                                                <div className={cn(
                                                    "p-2 rounded-lg",
                                                    request.status === 'approved' ? 'bg-emerald-100 dark:bg-emerald-900/30' :
                                                    request.status === 'rejected' ? 'bg-rose-100 dark:bg-rose-900/30' :
                                                    'bg-amber-100 dark:bg-amber-900/30'
                                                )}>
                                                    {request.status === 'approved' ? (
                                                        <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                                                    ) : request.status === 'rejected' ? (
                                                        <XCircle className="w-5 h-5 text-rose-600" />
                                                    ) : (
                                                        <Clock className="w-5 h-5 text-amber-600" />
                                                    )}
                                                </div>
                                                <div>
                                                    <p className="font-medium capitalize">{request.leave_type} Leave</p>
                                                    <p className="text-sm text-muted-foreground">
                                                        {formatDate(request.start_date)} - {formatDate(request.end_date)} ({request.days} days)
                                                    </p>
                                                </div>
                                            </div>
                                            <Badge className={getStatusColor(request.status)}>{request.status}</Badge>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Profile Tab */}
                <TabsContent value="profile">
                    <Card>
                        <CardHeader>
                            <CardTitle>My Profile</CardTitle>
                            <CardDescription>View your employment details</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <p className="text-sm text-muted-foreground">Full Name</p>
                                    <p className="font-medium">{profile?.first_name} {profile?.last_name}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-muted-foreground">Email</p>
                                    <p className="font-medium">{profile?.email}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-muted-foreground">Job Title</p>
                                    <p className="font-medium">{profile?.job_title || 'Not specified'}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-muted-foreground">Department</p>
                                    <p className="font-medium">{profile?.department || 'Not specified'}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-muted-foreground">Start Date</p>
                                    <p className="font-medium">{profile?.start_date ? formatDate(profile.start_date) : 'Not specified'}</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
