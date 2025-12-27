import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { 
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '../ui/dialog';
import { Label } from '../ui/label';
import { 
    Plus, 
    Search, 
    Users, 
    AlertTriangle,
    ArrowRight,
    Mail,
    Briefcase
} from 'lucide-react';
import { cn, getStatusColor, getComplianceColor } from '../../lib/utils';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function EmployeesPage() {
    const navigate = useNavigate();
    const [employees, setEmployees] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [dialogOpen, setDialogOpen] = useState(false);
    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        email: '',
        job_title: '',
        department: '',
        salary: '',
        ni_number: '',
        tax_code: '',
        bank_account: '',
        bank_sort_code: ''
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        fetchEmployees();
    }, []);

    const fetchEmployees = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/employees`, { withCredentials: true });
            setEmployees(response.data);
        } catch (error) {
            toast.error('Failed to load employees');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            const data = {
                ...formData,
                salary: formData.salary ? parseFloat(formData.salary) : null
            };
            await axios.post(`${API_URL}/api/employees`, data, { withCredentials: true });
            toast.success('Employee added successfully');
            setDialogOpen(false);
            setFormData({
                first_name: '',
                last_name: '',
                email: '',
                job_title: '',
                department: '',
                salary: '',
                ni_number: '',
                tax_code: '',
                bank_account: '',
                bank_sort_code: ''
            });
            fetchEmployees();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to add employee');
        } finally {
            setSubmitting(false);
        }
    };

    const filteredEmployees = employees.filter(emp => 
        `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(searchTerm.toLowerCase()) ||
        emp.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        emp.job_title?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-6" data-testid="employees-page">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Employees</h1>
                    <p className="text-muted-foreground mt-1">Manage your team members and their details</p>
                </div>
                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                    <DialogTrigger asChild>
                        <Button className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-employee-btn">
                            <Plus className="w-4 h-4 mr-2" />
                            Add Employee
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
                        <DialogHeader>
                            <DialogTitle>Add New Employee</DialogTitle>
                            <DialogDescription>
                                Enter the employee's details. You can add payroll information later.
                            </DialogDescription>
                        </DialogHeader>
                        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="first_name">First Name *</Label>
                                    <Input
                                        id="first_name"
                                        value={formData.first_name}
                                        onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                                        required
                                        data-testid="input-first-name"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="last_name">Last Name *</Label>
                                    <Input
                                        id="last_name"
                                        value={formData.last_name}
                                        onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                                        required
                                        data-testid="input-last-name"
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="email">Email *</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    required
                                    data-testid="input-email"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="job_title">Job Title</Label>
                                    <Input
                                        id="job_title"
                                        value={formData.job_title}
                                        onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                                        data-testid="input-job-title"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="department">Department</Label>
                                    <Input
                                        id="department"
                                        value={formData.department}
                                        onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                                        data-testid="input-department"
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="salary">Annual Salary (£)</Label>
                                <Input
                                    id="salary"
                                    type="number"
                                    value={formData.salary}
                                    onChange={(e) => setFormData({ ...formData, salary: e.target.value })}
                                    placeholder="e.g. 35000"
                                    data-testid="input-salary"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="ni_number">NI Number</Label>
                                    <Input
                                        id="ni_number"
                                        value={formData.ni_number}
                                        onChange={(e) => setFormData({ ...formData, ni_number: e.target.value })}
                                        placeholder="e.g. AB123456C"
                                        data-testid="input-ni-number"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="tax_code">Tax Code</Label>
                                    <Input
                                        id="tax_code"
                                        value={formData.tax_code}
                                        onChange={(e) => setFormData({ ...formData, tax_code: e.target.value })}
                                        placeholder="e.g. 1257L"
                                        data-testid="input-tax-code"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="bank_account">Bank Account</Label>
                                    <Input
                                        id="bank_account"
                                        value={formData.bank_account}
                                        onChange={(e) => setFormData({ ...formData, bank_account: e.target.value })}
                                        placeholder="8 digit account number"
                                        data-testid="input-bank-account"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="bank_sort_code">Sort Code</Label>
                                    <Input
                                        id="bank_sort_code"
                                        value={formData.bank_sort_code}
                                        onChange={(e) => setFormData({ ...formData, bank_sort_code: e.target.value })}
                                        placeholder="e.g. 12-34-56"
                                        data-testid="input-sort-code"
                                    />
                                </div>
                            </div>
                            <div className="flex justify-end gap-3 mt-6">
                                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                                    Cancel
                                </Button>
                                <Button type="submit" disabled={submitting} data-testid="submit-employee-btn">
                                    {submitting ? 'Adding...' : 'Add Employee'}
                                </Button>
                            </div>
                        </form>
                    </DialogContent>
                </Dialog>
            </div>

            {/* Search */}
            <div className="relative max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                    placeholder="Search employees..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                    data-testid="search-employees"
                />
            </div>

            {/* Employees Grid */}
            {filteredEmployees.length === 0 ? (
                <Card>
                    <CardContent className="py-16 text-center">
                        <Users className="w-16 h-16 mx-auto text-muted-foreground/50" />
                        <h3 className="mt-4 text-lg font-semibold">No employees found</h3>
                        <p className="text-muted-foreground mt-1">
                            {searchTerm ? 'Try adjusting your search' : 'Add your first employee to get started'}
                        </p>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredEmployees.map((emp) => (
                        <Card 
                            key={emp.employee_id} 
                            className="hover:shadow-md transition-all hover-lift cursor-pointer"
                            onClick={() => navigate(`/employees/${emp.employee_id}`)}
                            data-testid={`employee-card-${emp.employee_id}`}
                        >
                            <CardContent className="p-6">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="w-12 h-12 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
                                            <span className="text-lg font-medium text-indigo-700 dark:text-indigo-300">
                                                {emp.first_name[0]}{emp.last_name[0]}
                                            </span>
                                        </div>
                                        <div>
                                            <h3 className="font-semibold">{emp.first_name} {emp.last_name}</h3>
                                            <p className="text-sm text-muted-foreground">{emp.job_title || 'No title'}</p>
                                        </div>
                                    </div>
                                    <Badge className={getStatusColor(emp.status)}>{emp.status}</Badge>
                                </div>
                                
                                <div className="mt-4 space-y-2">
                                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                        <Mail className="w-4 h-4" />
                                        <span className="truncate">{emp.email}</span>
                                    </div>
                                    {emp.department && (
                                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                            <Briefcase className="w-4 h-4" />
                                            <span>{emp.department}</span>
                                        </div>
                                    )}
                                </div>

                                <div className="mt-4 pt-4 border-t border-border flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className={cn("text-sm font-medium", getComplianceColor(emp.compliance_score))}>
                                            {emp.compliance_score}% Compliant
                                        </span>
                                        {emp.compliance_score < 100 && (
                                            <AlertTriangle className="w-4 h-4 text-amber-500" />
                                        )}
                                    </div>
                                    <ArrowRight className="w-4 h-4 text-muted-foreground" />
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
