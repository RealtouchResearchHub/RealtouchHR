import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../ui/select';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
    DropdownMenuLabel,
} from '../ui/dropdown-menu';
import ComplianceScore from '../shared/ComplianceScore';
import OffboardingDialog from '../shared/OffboardingDialog';
import BenefitsInKindDialog from '../shared/BenefitsInKindDialog';
import { 
    ArrowLeft,
    Save,
    Mail,
    Phone,
    Briefcase,
    Calendar,
    CreditCard,
    AlertTriangle,
    CheckCircle2,
    FileText,
    Clock,
    MoreVertical,
    UserMinus,
    FileDown
} from 'lucide-react';
import { cn, formatCurrency, formatDate, getStatusColor, getComplianceColor } from '../../lib/utils';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function EmployeeDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [employee, setEmployee] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [formData, setFormData] = useState({});
    const [leaves, setLeaves] = useState([]);
    const [shifts, setShifts] = useState([]);
    const [showOffboard, setShowOffboard] = useState(false);
    const [showBiK, setShowBiK] = useState(false);

    useEffect(() => {
        fetchEmployee();
        fetchRelatedData();
    }, [id]);

    const fetchEmployee = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/employees/${id}`, { withCredentials: true });
            setEmployee(response.data);
            setFormData(response.data);
        } catch (error) {
            toast.error('Failed to load employee');
            navigate('/employees');
        } finally {
            setLoading(false);
        }
    };

    const downloadTaxDoc = async (docType, extraPath = '') => {
        try {
            const token = localStorage.getItem('token');
            const url = `${API_URL}/api/tax-docs/${docType}/${id}${extraPath}`;
            const res = await axios.get(url, {
                headers: { Authorization: `Bearer ${token}` },
                withCredentials: true,
                responseType: 'blob',
            });
            const blobUrl = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = `${docType.toUpperCase()}_${employee.first_name}_${employee.last_name}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(blobUrl);
            toast.success(`${docType.toUpperCase()} downloaded`);
        } catch (err) {
            toast.error(err.response?.data?.detail || `Failed to download ${docType.toUpperCase()}`);
        }
    };

    const fetchRelatedData = async () => {
        try {
            const [leavesRes, shiftsRes] = await Promise.all([
                axios.get(`${API_URL}/api/leave`, { withCredentials: true }),
                axios.get(`${API_URL}/api/shifts`, { withCredentials: true })
            ]);
            setLeaves(leavesRes.data.filter(l => l.employee_id === id));
            setShifts(shiftsRes.data.filter(s => s.employee_id === id));
        } catch (error) {
            console.error('Failed to fetch related data:', error);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await axios.put(`${API_URL}/api/employees/${id}`, formData, { withCredentials: true });
            toast.success('Employee updated successfully');
            fetchEmployee();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to update employee');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!employee) return null;

    return (
        <div className="space-y-6" data-testid="employee-detail-page">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => navigate('/employees')} data-testid="back-btn">
                    <ArrowLeft className="w-5 h-5" />
                </Button>
                <div className="flex-1">
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">
                        {employee.first_name} {employee.last_name}
                    </h1>
                    <p className="text-muted-foreground">{employee.job_title || 'No job title'}</p>
                </div>
                <Badge className={getStatusColor(employee.status)}>{employee.status}</Badge>
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="icon" data-testid="employee-actions-btn">
                            <MoreVertical className="w-4 h-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                        <DropdownMenuLabel>Tax Documents</DropdownMenuLabel>
                        <DropdownMenuItem
                            onClick={() => downloadTaxDoc('p60', '?tax_year=2024-25')}
                            data-testid="download-p60-item"
                        >
                            <FileDown className="w-4 h-4 mr-2" />
                            Download P60 (2024-25)
                        </DropdownMenuItem>
                        <DropdownMenuItem
                            onClick={() => downloadTaxDoc('p45')}
                            disabled={employee.status !== 'terminated'}
                            data-testid="download-p45-item"
                        >
                            <FileDown className="w-4 h-4 mr-2" />
                            Download P45 {employee.status !== 'terminated' && '(after leave)'}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                            onClick={() => setShowBiK(true)}
                            data-testid="bik-menu-item"
                        >
                            <FileText className="w-4 h-4 mr-2" />
                            Benefits / P11D
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuLabel>Workflow</DropdownMenuLabel>
                        <DropdownMenuItem
                            onClick={() => setShowOffboard(true)}
                            disabled={employee.status === 'terminated'}
                            className="text-rose-600 focus:text-rose-700"
                            data-testid="offboard-menu-item"
                        >
                            <UserMinus className="w-4 h-4 mr-2" />
                            Offboard Employee
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>

            <OffboardingDialog
                open={showOffboard}
                onOpenChange={setShowOffboard}
                employee={employee}
                onComplete={() => fetchEmployee()}
            />

            <BenefitsInKindDialog
                open={showBiK}
                onOpenChange={setShowBiK}
                employee={employee}
            />

            {/* Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="bg-gradient-to-br from-indigo-50 to-white dark:from-indigo-950/30 dark:to-background">
                    <CardContent className="p-6 flex flex-col items-center">
                        <ComplianceScore score={employee.compliance_score} size="md" />
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-6">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/30">
                                <Mail className="w-5 h-5 text-indigo-600" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Email</p>
                                <p className="font-medium truncate">{employee.email}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-6">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/30">
                                <CreditCard className="w-5 h-5 text-emerald-600" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Annual Salary</p>
                                <p className="font-medium">{employee.salary ? formatCurrency(employee.salary) : 'Not set'}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-6">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/30">
                                <Briefcase className="w-5 h-5 text-amber-600" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Department</p>
                                <p className="font-medium">{employee.department || 'Not assigned'}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Compliance Issues */}
            {employee.compliance_issues?.length > 0 && (
                <Card className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                            <AlertTriangle className="w-5 h-5" />
                            Compliance Issues
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ul className="space-y-2">
                            {employee.compliance_issues.map((issue, index) => (
                                <li key={index} className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                                    {issue}
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                </Card>
            )}

            {/* Tabs */}
            <Tabs defaultValue="details" className="space-y-6">
                <TabsList>
                    <TabsTrigger value="details">Personal Details</TabsTrigger>
                    <TabsTrigger value="payroll">Payroll Info</TabsTrigger>
                    <TabsTrigger value="leave">Leave History</TabsTrigger>
                    <TabsTrigger value="shifts">Shifts</TabsTrigger>
                </TabsList>

                {/* Personal Details Tab */}
                <TabsContent value="details">
                    <Card>
                        <CardHeader>
                            <CardTitle>Personal Information</CardTitle>
                            <CardDescription>Update employee's personal details</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <Label htmlFor="first_name">First Name</Label>
                                    <Input
                                        id="first_name"
                                        value={formData.first_name || ''}
                                        onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                                        data-testid="input-first-name"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="last_name">Last Name</Label>
                                    <Input
                                        id="last_name"
                                        value={formData.last_name || ''}
                                        onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                                        data-testid="input-last-name"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="email">Email</Label>
                                    <Input
                                        id="email"
                                        type="email"
                                        value={formData.email || ''}
                                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                        data-testid="input-email"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="job_title">Job Title</Label>
                                    <Input
                                        id="job_title"
                                        value={formData.job_title || ''}
                                        onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                                        data-testid="input-job-title"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="department">Department</Label>
                                    <Input
                                        id="department"
                                        value={formData.department || ''}
                                        onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                                        data-testid="input-department"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="start_date">Start Date</Label>
                                    <Input
                                        id="start_date"
                                        type="date"
                                        value={formData.start_date || ''}
                                        onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                                        data-testid="input-start-date"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="status">Status</Label>
                                    <Select
                                        value={formData.status || 'active'}
                                        onValueChange={(value) => setFormData({ ...formData, status: value })}
                                    >
                                        <SelectTrigger data-testid="select-status">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="active">Active</SelectItem>
                                            <SelectItem value="inactive">Inactive</SelectItem>
                                            <SelectItem value="on_leave">On Leave</SelectItem>
                                            <SelectItem value="terminated">Terminated</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                            <Button onClick={handleSave} disabled={saving} data-testid="save-details-btn">
                                <Save className="w-4 h-4 mr-2" />
                                {saving ? 'Saving...' : 'Save Changes'}
                            </Button>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Payroll Tab */}
                <TabsContent value="payroll">
                    <Card>
                        <CardHeader>
                            <CardTitle>Payroll Information</CardTitle>
                            <CardDescription>Manage payroll and tax details</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <Label htmlFor="salary">Annual Salary (£)</Label>
                                    <Input
                                        id="salary"
                                        type="number"
                                        value={formData.salary || ''}
                                        onChange={(e) => setFormData({ ...formData, salary: parseFloat(e.target.value) || null })}
                                        data-testid="input-salary"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="ni_number">NI Number</Label>
                                    <Input
                                        id="ni_number"
                                        value={formData.ni_number || ''}
                                        onChange={(e) => setFormData({ ...formData, ni_number: e.target.value })}
                                        placeholder="e.g. AB123456C"
                                        data-testid="input-ni-number"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="tax_code">Tax Code</Label>
                                    <Input
                                        id="tax_code"
                                        value={formData.tax_code || ''}
                                        onChange={(e) => setFormData({ ...formData, tax_code: e.target.value })}
                                        placeholder="e.g. 1257L"
                                        data-testid="input-tax-code"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="bank_account">Bank Account Number</Label>
                                    <Input
                                        id="bank_account"
                                        value={formData.bank_account || ''}
                                        onChange={(e) => setFormData({ ...formData, bank_account: e.target.value })}
                                        placeholder="8 digit account number"
                                        data-testid="input-bank-account"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="bank_sort_code">Sort Code</Label>
                                    <Input
                                        id="bank_sort_code"
                                        value={formData.bank_sort_code || ''}
                                        onChange={(e) => setFormData({ ...formData, bank_sort_code: e.target.value })}
                                        placeholder="e.g. 12-34-56"
                                        data-testid="input-sort-code"
                                    />
                                </div>
                            </div>
                            <Button onClick={handleSave} disabled={saving} data-testid="save-payroll-btn">
                                <Save className="w-4 h-4 mr-2" />
                                {saving ? 'Saving...' : 'Save Changes'}
                            </Button>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Leave History Tab */}
                <TabsContent value="leave">
                    <Card>
                        <CardHeader>
                            <CardTitle>Leave History</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {leaves.length === 0 ? (
                                <div className="text-center py-8 text-muted-foreground">
                                    <Calendar className="w-12 h-12 mx-auto opacity-50" />
                                    <p className="mt-4">No leave records</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {leaves.map((leave) => (
                                        <div key={leave.leave_id} className="flex items-center justify-between p-4 rounded-lg border">
                                            <div>
                                                <p className="font-medium capitalize">{leave.leave_type.replace('_', ' ')}</p>
                                                <p className="text-sm text-muted-foreground">
                                                    {formatDate(leave.start_date)} - {formatDate(leave.end_date)} ({leave.days} days)
                                                </p>
                                            </div>
                                            <Badge className={getStatusColor(leave.status)}>{leave.status}</Badge>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Shifts Tab */}
                <TabsContent value="shifts">
                    <Card>
                        <CardHeader>
                            <CardTitle>Recent Shifts</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {shifts.length === 0 ? (
                                <div className="text-center py-8 text-muted-foreground">
                                    <Clock className="w-12 h-12 mx-auto opacity-50" />
                                    <p className="mt-4">No shifts scheduled</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {shifts.slice(0, 10).map((shift) => (
                                        <div key={shift.shift_id} className="flex items-center justify-between p-4 rounded-lg border">
                                            <div>
                                                <p className="font-medium">{formatDate(shift.date)}</p>
                                                <p className="text-sm text-muted-foreground">
                                                    {shift.start_time} - {shift.end_time}
                                                </p>
                                            </div>
                                            <Badge className={getStatusColor(shift.status)}>{shift.status}</Badge>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
