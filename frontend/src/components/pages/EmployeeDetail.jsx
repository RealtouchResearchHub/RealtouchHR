import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem,
    DropdownMenuSeparator, DropdownMenuTrigger, DropdownMenuLabel,
} from '../ui/dropdown-menu';
import { Textarea } from '../ui/textarea';
import ComplianceScore from '../shared/ComplianceScore';
import OffboardingDialog from '../shared/OffboardingDialog';
import BenefitsInKindDialog from '../shared/BenefitsInKindDialog';
import {
    ArrowLeft, Save, Mail, Phone, Briefcase, Calendar, CreditCard,
    AlertTriangle, CheckCircle2, XCircle, FileText, Clock, MoreVertical,
    UserMinus, FileDown, RefreshCw, Shield, Activity, Eye, EyeOff,
    MapPin, User, Building2, Plus, Trash2
} from 'lucide-react';
import { cn, formatCurrency, formatDate, getStatusColor, getComplianceColor } from '../../lib/utils';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

function maskSortCode(sc) {
    if (!sc) return '';
    const clean = sc.replace(/\D/g, '');
    return clean.length >= 6 ? `**-**-${clean.slice(-2)}` : '••••••';
}
function maskAccount(ac) {
    if (!ac) return '';
    return ac.length >= 4 ? `****${ac.slice(-4)}` : '••••••••';
}

export default function EmployeeDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const { user, token } = useAuth();
    const [employee, setEmployee] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [formData, setFormData] = useState({});
    const [leaves, setLeaves] = useState([]);
    const [shifts, setShifts] = useState([]);
    const [showOffboard, setShowOffboard] = useState(false);
    const [showBiK, setShowBiK] = useState(false);
    const [readiness, setReadiness] = useState(null);
    const [statusHistory, setStatusHistory] = useState([]);
    const [auditLog, setAuditLog] = useState([]);
    const [notes, setNotes] = useState([]);
    const [newNote, setNewNote] = useState('');
    const [bankVisible, setBankVisible] = useState(false);
    const [emergencyContacts, setEmergencyContacts] = useState([]);
    const [documents, setDocuments] = useState([]);

    // Roles that can see bank details
    const canSeeBankDetails = user && ['owner', 'admin', 'payroll_admin'].includes(user.role);

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

    const fetchRelatedData = async () => {
        // Core data
        try {
            const [leavesRes, shiftsRes] = await Promise.all([
                axios.get(`${API_URL}/api/leave`, { withCredentials: true }),
                axios.get(`${API_URL}/api/shifts`, { withCredentials: true })
            ]);
            setLeaves(leavesRes.data.filter(l => l.employee_id === id));
            setShifts(shiftsRes.data.filter(s => s.employee_id === id));
        } catch {}

        // Best-effort supplementary data
        const safe = async (fn) => { try { return await fn(); } catch { return null; } };
        const [readinessRes, historyRes, auditRes, docsRes, emgRes] = await Promise.all([
            safe(() => axios.get(`${API_URL}/api/employees/${id}/readiness`, { withCredentials: true })),
            safe(() => axios.get(`${API_URL}/api/employees/${id}/status-history`, { withCredentials: true })),
            safe(() => axios.get(`${API_URL}/api/employees/${id}/audit-log`, { withCredentials: true })),
            safe(() => axios.get(`${API_URL}/api/employees/${id}/documents`, { withCredentials: true })),
            safe(() => axios.get(`${API_URL}/api/employees/${id}/emergency-contacts`, { withCredentials: true })),
        ]);
        if (readinessRes) setReadiness(readinessRes.data);
        if (historyRes) setStatusHistory(historyRes.data || []);
        if (auditRes) setAuditLog(auditRes.data || []);
        if (docsRes) setDocuments(docsRes.data || []);
        if (emgRes) setEmergencyContacts(emgRes.data || []);
    };

    const downloadTaxDoc = async (docType, extraPath = '') => {
        try {
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

    const handleSave = async (extraData = {}) => {
        setSaving(true);
        try {
            await axios.put(`${API_URL}/api/employees/${id}`, { ...formData, ...extraData }, { withCredentials: true });
            toast.success('Employee updated successfully');
            fetchEmployee();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to update employee');
        } finally {
            setSaving(false);
        }
    };

    const addNote = async () => {
        if (!newNote.trim()) return;
        try {
            await axios.post(`${API_URL}/api/employees/${id}/notes`, { content: newNote }, { withCredentials: true });
            toast.success('Note added');
            setNewNote('');
            fetchRelatedData();
        } catch {
            // Optimistically add to local list
            setNotes(prev => [{ note_id: Date.now(), content: newNote, created_at: new Date().toISOString(), author: user?.name || 'You' }, ...prev]);
            setNewNote('');
        }
    };

    const changeLifecycleStatus = async (newStatus) => {
        try {
            await axios.post(`${API_URL}/api/employees/${id}/lifecycle`, { new_status: newStatus }, { withCredentials: true });
            toast.success(`Status changed to ${newStatus.replace(/_/g, ' ')}`);
            fetchEmployee();
            fetchRelatedData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to change status');
        }
    };

    const SaveButton = ({ section }) => (
        <Button onClick={() => handleSave()} disabled={saving} data-testid={`save-${section}-btn`} className="bg-indigo-600 hover:bg-indigo-700">
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Saving...' : 'Save Changes'}
        </Button>
    );

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
                        {employee.preferred_name || employee.first_name} {employee.last_name}
                    </h1>
                    <p className="text-muted-foreground">{employee.job_title || 'No job title'} {employee.department && `· ${employee.department}`}</p>
                </div>
                <Badge className={getStatusColor(employee.status)}>{employee.status || 'active'}</Badge>
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="icon" data-testid="employee-actions-btn">
                            <MoreVertical className="w-4 h-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                        <DropdownMenuLabel>Tax Documents</DropdownMenuLabel>
                        <DropdownMenuItem onClick={() => downloadTaxDoc('p60', '?tax_year=2024-25')} data-testid="download-p60-item">
                            <FileDown className="w-4 h-4 mr-2" /> Download P60 (2024-25)
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => downloadTaxDoc('p45')} disabled={employee.status !== 'terminated'} data-testid="download-p45-item">
                            <FileDown className="w-4 h-4 mr-2" /> Download P45 {employee.status !== 'terminated' && '(after leave)'}
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => setShowBiK(true)} data-testid="bik-menu-item">
                            <FileText className="w-4 h-4 mr-2" /> Benefits / P11D
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuLabel>Workflow</DropdownMenuLabel>
                        <DropdownMenuItem onClick={() => setShowOffboard(true)} disabled={employee.status === 'terminated'} className="text-rose-600 focus:text-rose-700" data-testid="offboard-menu-item">
                            <UserMinus className="w-4 h-4 mr-2" /> Offboard Employee
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>

            <OffboardingDialog open={showOffboard} onOpenChange={setShowOffboard} employee={employee} onComplete={() => fetchEmployee()} />
            <BenefitsInKindDialog open={showBiK} onOpenChange={setShowBiK} employee={employee} />

            {/* Overview cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                                <p className="font-medium truncate text-sm">{employee.email}</p>
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
                                <p className="text-sm text-muted-foreground">Start Date</p>
                                <p className="font-medium">{employee.start_date ? formatDate(employee.start_date) : 'Not set'}</p>
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
                            <AlertTriangle className="w-5 h-5" /> Compliance Issues
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ul className="space-y-2">
                            {employee.compliance_issues.map((issue, i) => (
                                <li key={i} className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />{issue}
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                </Card>
            )}

            {/* Readiness Flags Panel */}
            {readiness && (
                <Card>
                    <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-base flex items-center gap-2">
                                <Shield className="w-4 h-4 text-indigo-600" /> Readiness Status
                            </CardTitle>
                            <Button variant="ghost" size="sm" onClick={fetchRelatedData}>
                                <RefreshCw className="w-3.5 h-3.5 mr-1" /> Refresh
                            </Button>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
                            {[
                                { key: 'hr_profile_ready', label: 'HR Profile' },
                                { key: 'payroll_ready', label: 'Payroll' },
                                { key: 'rti_ready', label: 'RTI' },
                                { key: 'right_to_work_ready', label: 'RTW' },
                                { key: 'ukvi_ready', label: 'UKVI' },
                                { key: 'documents_ready', label: 'Documents' },
                            ].map(({ key, label }) => {
                                const ok = readiness.flags?.[key];
                                const missing = readiness.missing_fields?.[key] || [];
                                return (
                                    <div key={key} className={`p-2 rounded-lg border text-center ${ok ? 'border-emerald-200 bg-emerald-50 dark:bg-emerald-950/20' : 'border-amber-200 bg-amber-50 dark:bg-amber-950/20'}`}>
                                        {ok ? <CheckCircle2 className="w-4 h-4 text-emerald-600 mx-auto mb-1" /> : <XCircle className="w-4 h-4 text-amber-500 mx-auto mb-1" />}
                                        <p className="text-xs font-medium">{label}</p>
                                        {!ok && missing.length > 0 && (
                                            <p className="text-xs text-muted-foreground mt-0.5" title={missing.join(', ')}>{missing.length} missing</p>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Tabs */}
            <Tabs defaultValue="personal" className="space-y-6">
                <TabsList className="flex-wrap h-auto gap-1">
                    <TabsTrigger value="personal">Personal</TabsTrigger>
                    <TabsTrigger value="contact">Contact</TabsTrigger>
                    <TabsTrigger value="employment">Employment</TabsTrigger>
                    <TabsTrigger value="payroll">Payroll</TabsTrigger>
                    <TabsTrigger value="bank">Bank Details</TabsTrigger>
                    <TabsTrigger value="rtw">Right to Work</TabsTrigger>
                    <TabsTrigger value="emergency">Emergency</TabsTrigger>
                    <TabsTrigger value="documents">Documents</TabsTrigger>
                    <TabsTrigger value="leave">Leave</TabsTrigger>
                    <TabsTrigger value="shifts">Shifts</TabsTrigger>
                    <TabsTrigger value="notes">Notes</TabsTrigger>
                    <TabsTrigger value="lifecycle">Lifecycle</TabsTrigger>
                    <TabsTrigger value="audit">Audit Trail</TabsTrigger>
                </TabsList>

                {/* Personal Details */}
                <TabsContent value="personal">
                    <Card>
                        <CardHeader>
                            <CardTitle>Personal Information</CardTitle>
                            <CardDescription>Core personal details. Sensitive changes are audit-logged.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <Label>Title</Label>
                                    <Select value={formData.title || ''} onValueChange={v => setFormData({ ...formData, title: v })}>
                                        <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                                        <SelectContent>
                                            {['Mr', 'Mrs', 'Miss', 'Ms', 'Dr', 'Prof', 'Mx'].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="first_name">First Name</Label>
                                    <Input id="first_name" value={formData.first_name || ''} onChange={e => setFormData({ ...formData, first_name: e.target.value })} data-testid="input-first-name" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Middle Name</Label>
                                    <Input value={formData.middle_name || ''} onChange={e => setFormData({ ...formData, middle_name: e.target.value })} />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="last_name">Last Name</Label>
                                    <Input id="last_name" value={formData.last_name || ''} onChange={e => setFormData({ ...formData, last_name: e.target.value })} data-testid="input-last-name" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Preferred Name</Label>
                                    <Input value={formData.preferred_name || ''} onChange={e => setFormData({ ...formData, preferred_name: e.target.value })} />
                                </div>
                                <div className="space-y-2">
                                    <Label>Date of Birth</Label>
                                    <Input type="date" value={formData.date_of_birth?.slice(0, 10) || ''} onChange={e => setFormData({ ...formData, date_of_birth: e.target.value })} />
                                </div>
                                <div className="space-y-2">
                                    <Label>Gender</Label>
                                    <Select value={formData.gender || ''} onValueChange={v => setFormData({ ...formData, gender: v })}>
                                        <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                                        <SelectContent>
                                            {['Male', 'Female', 'Non-binary', 'Prefer not to say', 'Other'].map(g => <SelectItem key={g} value={g}>{g}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>NI Number</Label>
                                    <Input value={formData.ni_number || ''} onChange={e => setFormData({ ...formData, ni_number: e.target.value })} placeholder="AB123456C" data-testid="input-ni-number" />
                                    <p className="text-xs text-muted-foreground">Visible to payroll/HR admins only</p>
                                </div>
                                <div className="space-y-2">
                                    <Label>Nationality</Label>
                                    <Input value={formData.nationality || ''} onChange={e => setFormData({ ...formData, nationality: e.target.value })} />
                                </div>
                            </div>
                            <SaveButton section="personal" />
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Contact Details */}
                <TabsContent value="contact">
                    <Card>
                        <CardHeader>
                            <CardTitle>Contact Details</CardTitle>
                            <CardDescription>Email addresses, phone numbers and address</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <Label htmlFor="email">Personal Email</Label>
                                    <Input id="email" type="email" value={formData.email || ''} onChange={e => setFormData({ ...formData, email: e.target.value })} data-testid="input-email" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Work Email</Label>
                                    <Input type="email" value={formData.work_email || ''} onChange={e => setFormData({ ...formData, work_email: e.target.value })} />
                                </div>
                                <div className="space-y-2">
                                    <Label>Mobile Number</Label>
                                    <Input value={formData.mobile_phone || ''} onChange={e => setFormData({ ...formData, mobile_phone: e.target.value })} placeholder="+44 7700 000000" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Alternative Phone</Label>
                                    <Input value={formData.alternative_phone || ''} onChange={e => setFormData({ ...formData, alternative_phone: e.target.value })} />
                                </div>
                            </div>
                            <div className="border-t pt-4">
                                <h4 className="font-medium mb-4 text-sm flex items-center gap-2"><MapPin className="w-4 h-4" />Home Address</h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-2 md:col-span-2">
                                        <Label>Address Line 1</Label>
                                        <Input value={formData.address_line1 || ''} onChange={e => setFormData({ ...formData, address_line1: e.target.value })} />
                                    </div>
                                    <div className="space-y-2 md:col-span-2">
                                        <Label>Address Line 2</Label>
                                        <Input value={formData.address_line2 || ''} onChange={e => setFormData({ ...formData, address_line2: e.target.value })} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Town / City</Label>
                                        <Input value={formData.town || ''} onChange={e => setFormData({ ...formData, town: e.target.value })} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>County</Label>
                                        <Input value={formData.county || ''} onChange={e => setFormData({ ...formData, county: e.target.value })} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Postcode</Label>
                                        <Input value={formData.postcode || ''} onChange={e => setFormData({ ...formData, postcode: e.target.value })} placeholder="SW1A 1AA" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Country</Label>
                                        <Input value={formData.country || 'United Kingdom'} onChange={e => setFormData({ ...formData, country: e.target.value })} />
                                    </div>
                                </div>
                            </div>
                            <SaveButton section="contact" />
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Employment Details */}
                <TabsContent value="employment">
                    <Card>
                        <CardHeader>
                            <CardTitle>Employment Details</CardTitle>
                            <CardDescription>Job, contract and working arrangement details</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <Label htmlFor="job_title">Job Title</Label>
                                    <Input id="job_title" value={formData.job_title || ''} onChange={e => setFormData({ ...formData, job_title: e.target.value })} data-testid="input-job-title" />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="department">Department</Label>
                                    <Input id="department" value={formData.department || ''} onChange={e => setFormData({ ...formData, department: e.target.value })} data-testid="input-department" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Work Location</Label>
                                    <Input value={formData.work_location || ''} onChange={e => setFormData({ ...formData, work_location: e.target.value })} />
                                </div>
                                <div className="space-y-2">
                                    <Label>Employment Type</Label>
                                    <Select value={formData.employment_type || ''} onValueChange={v => setFormData({ ...formData, employment_type: v })}>
                                        <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                                        <SelectContent>
                                            {['Full-time', 'Part-time', 'Casual', 'Zero hours', 'Agency'].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Contract Type</Label>
                                    <Select value={formData.contract_type || ''} onValueChange={v => setFormData({ ...formData, contract_type: v })}>
                                        <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                                        <SelectContent>
                                            {['Permanent', 'Fixed-term', 'Temporary', 'Apprenticeship', 'Internship'].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="start_date">Start Date</Label>
                                    <Input id="start_date" type="date" value={formData.start_date?.slice(0, 10) || ''} onChange={e => setFormData({ ...formData, start_date: e.target.value })} data-testid="input-start-date" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Probation Period</Label>
                                    <Select value={formData.probation_period || ''} onValueChange={v => setFormData({ ...formData, probation_period: v })}>
                                        <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                                        <SelectContent>
                                            {['1 month', '2 months', '3 months', '6 months', 'None'].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="probation_end_date">Probation End Date</Label>
                                    <Input id="probation_end_date" type="date" value={formData.probation_end_date?.slice(0, 10) || ''} onChange={e => setFormData({ ...formData, probation_end_date: e.target.value })} data-testid="input-probation-end" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Working Pattern</Label>
                                    <Input value={formData.working_pattern || ''} onChange={e => setFormData({ ...formData, working_pattern: e.target.value })} placeholder="e.g. Mon–Fri 09:00–17:30" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Weekly Contracted Hours</Label>
                                    <Input type="number" value={formData.weekly_hours || ''} onChange={e => setFormData({ ...formData, weekly_hours: parseFloat(e.target.value) || null })} placeholder="e.g. 37.5" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Notice Period</Label>
                                    <Select value={formData.notice_period || ''} onValueChange={v => setFormData({ ...formData, notice_period: v })}>
                                        <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                                        <SelectContent>
                                            {['1 week', '2 weeks', '1 month', '2 months', '3 months', '6 months'].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                            <SaveButton section="employment" />
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Payroll Tab */}
                <TabsContent value="payroll">
                    <Card>
                        <CardHeader>
                            <CardTitle>Payroll & Tax</CardTitle>
                            <CardDescription>Pay, tax code, NI category and pension settings</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <Label>Payroll Status</Label>
                                    <Select value={formData.payroll_status || 'pending'} onValueChange={v => setFormData({ ...formData, payroll_status: v })}>
                                        <SelectTrigger><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {['pending', 'active', 'on_hold', 'excluded'].map(s => <SelectItem key={s} value={s}>{s.replace('_', ' ')}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Pay Frequency</Label>
                                    <Select value={formData.pay_frequency || ''} onValueChange={v => setFormData({ ...formData, pay_frequency: v })}>
                                        <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                                        <SelectContent>
                                            {['weekly', 'fortnightly', 'four_weekly', 'monthly'].map(s => <SelectItem key={s} value={s}>{s.replace('_', ' ')}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Salary Type</Label>
                                    <Select value={formData.salary_type || 'annual'} onValueChange={v => setFormData({ ...formData, salary_type: v })}>
                                        <SelectTrigger><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="annual">Annual Salary</SelectItem>
                                            <SelectItem value="hourly">Hourly Rate</SelectItem>
                                            <SelectItem value="daily">Daily Rate</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="salary">Salary / Rate (£)</Label>
                                    <Input id="salary" type="number" value={formData.salary || ''} onChange={e => setFormData({ ...formData, salary: parseFloat(e.target.value) || null })} data-testid="input-salary" />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="tax_code">Tax Code</Label>
                                    <Input id="tax_code" value={formData.tax_code || ''} onChange={e => setFormData({ ...formData, tax_code: e.target.value })} placeholder="e.g. 1257L" data-testid="input-tax-code" />
                                </div>
                                <div className="space-y-2">
                                    <Label>NI Category</Label>
                                    <Select value={formData.ni_category || 'A'} onValueChange={v => setFormData({ ...formData, ni_category: v })}>
                                        <SelectTrigger><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {['A', 'B', 'C', 'H', 'J', 'M', 'X', 'Z'].map(c => <SelectItem key={c} value={c}>Category {c}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Student Loan Plan</Label>
                                    <Select value={formData.student_loan_plan || ''} onValueChange={v => setFormData({ ...formData, student_loan_plan: v })}>
                                        <SelectTrigger><SelectValue placeholder="None" /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="">None</SelectItem>
                                            {['Plan 1', 'Plan 2', 'Plan 4', 'Plan 5'].map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Starter Declaration</Label>
                                    <Select value={formData.starter_declaration || ''} onValueChange={v => setFormData({ ...formData, starter_declaration: v })}>
                                        <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="A">A — First job since 6 April</SelectItem>
                                            <SelectItem value="B">B — Only job</SelectItem>
                                            <SelectItem value="C">C — Another job / pension</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Auto-Enrolment Status</Label>
                                    <Select value={formData.auto_enrolment_status || ''} onValueChange={v => setFormData({ ...formData, auto_enrolment_status: v })}>
                                        <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                                        <SelectContent>
                                            {['enrolled', 'opted_out', 'postponed', 'not_eligible'].map(s => <SelectItem key={s} value={s}>{s.replace(/_/g, ' ')}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Payroll Start Date</Label>
                                    <Input type="date" value={formData.payroll_start_date?.slice(0, 10) || ''} onChange={e => setFormData({ ...formData, payroll_start_date: e.target.value })} />
                                </div>
                            </div>
                            <SaveButton section="payroll" />
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Bank Details — masked by default, permission-gated */}
                <TabsContent value="bank">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle>Bank Details</CardTitle>
                                    <CardDescription>Encrypted at rest. Masked by default. All views and edits are audit-logged.</CardDescription>
                                </div>
                                {canSeeBankDetails && (
                                    <Button variant="outline" size="sm" onClick={() => setBankVisible(v => !v)}>
                                        {bankVisible ? <><EyeOff className="w-3.5 h-3.5 mr-1.5" />Hide</> : <><Eye className="w-3.5 h-3.5 mr-1.5" />Reveal</>}
                                    </Button>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {!canSeeBankDetails ? (
                                <div className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/20 p-4 text-center">
                                    <Shield className="w-8 h-8 mx-auto text-amber-500 mb-2" />
                                    <p className="text-sm font-medium">Restricted</p>
                                    <p className="text-xs text-muted-foreground mt-1">Bank details are accessible to Owner, Admin, and Payroll Admin roles only.</p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <Label>Account Holder Name</Label>
                                        {bankVisible
                                            ? <Input value={formData.account_holder_name || ''} onChange={e => setFormData({ ...formData, account_holder_name: e.target.value })} />
                                            : <Input value={formData.account_holder_name || ''} disabled />
                                        }
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Bank Name</Label>
                                        {bankVisible
                                            ? <Input value={formData.bank_name || ''} onChange={e => setFormData({ ...formData, bank_name: e.target.value })} />
                                            : <Input value={formData.bank_name || ''} disabled />
                                        }
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Sort Code</Label>
                                        {bankVisible
                                            ? <Input value={formData.bank_sort_code || ''} onChange={e => setFormData({ ...formData, bank_sort_code: e.target.value })} placeholder="00-00-00" data-testid="input-sort-code" />
                                            : <Input value={maskSortCode(formData.bank_sort_code)} readOnly className="font-mono" />
                                        }
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Account Number</Label>
                                        {bankVisible
                                            ? <Input value={formData.bank_account || ''} onChange={e => setFormData({ ...formData, bank_account: e.target.value })} placeholder="8 digits" data-testid="input-bank-account" />
                                            : <Input value={maskAccount(formData.bank_account)} readOnly className="font-mono" />
                                        }
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Building Society Roll No.</Label>
                                        {bankVisible
                                            ? <Input value={formData.building_society_roll || ''} onChange={e => setFormData({ ...formData, building_society_roll: e.target.value })} />
                                            : <Input value={formData.building_society_roll ? '••••' : 'N/A'} disabled />
                                        }
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Payment Method</Label>
                                        <Select value={formData.payment_method || 'bacs'} onValueChange={v => setFormData({ ...formData, payment_method: v })}>
                                            <SelectTrigger><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="bacs">BACS</SelectItem>
                                                <SelectItem value="faster_payments">Faster Payments</SelectItem>
                                                <SelectItem value="cash">Cash</SelectItem>
                                                <SelectItem value="cheque">Cheque</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                            )}
                            {canSeeBankDetails && bankVisible && <SaveButton section="bank" />}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Right to Work / UKVI */}
                <TabsContent value="rtw">
                    <div className="space-y-4">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Shield className="w-5 h-5 text-indigo-600" /> Right to Work
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>RTW Status</Label>
                                        <Select value={formData.right_to_work_status || ''} onValueChange={v => setFormData({ ...formData, right_to_work_status: v })}>
                                            <SelectTrigger><SelectValue placeholder="Select status" /></SelectTrigger>
                                            <SelectContent>
                                                {['valid', 'time_limited', 'pending_check', 'expired', 'not_required'].map(s => (
                                                    <SelectItem key={s} value={s}>{s.replace(/_/g, ' ')}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Document Type</Label>
                                        <Select value={formData.rtw_document_type || ''} onValueChange={v => setFormData({ ...formData, rtw_document_type: v })}>
                                            <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                                            <SelectContent>
                                                {['Passport', 'Birth certificate + NI', 'BRP', 'eVisa share code', 'EEA ID card', 'Other'].map(t => (
                                                    <SelectItem key={t} value={t}>{t}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Check Date</Label>
                                        <Input type="date" value={formData.rtw_check_date?.slice(0, 10) || ''} onChange={e => setFormData({ ...formData, rtw_check_date: e.target.value })} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>RTW Expiry Date</Label>
                                        <Input type="date" value={formData.rtw_expiry_date?.slice(0, 10) || ''} onChange={e => setFormData({ ...formData, rtw_expiry_date: e.target.value })} />
                                    </div>
                                    <div className="space-y-2 md:col-span-2">
                                        <Label>Follow-up Check Date</Label>
                                        <Input type="date" value={formData.rtw_followup_date?.slice(0, 10) || ''} onChange={e => setFormData({ ...formData, rtw_followup_date: e.target.value })} />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader><CardTitle className="text-base">Sponsored Worker / UKVI</CardTitle></CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Sponsored Worker</Label>
                                        <Select value={formData.is_sponsored_worker ? 'yes' : 'no'} onValueChange={v => setFormData({ ...formData, is_sponsored_worker: v === 'yes' })}>
                                            <SelectTrigger><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="no">No</SelectItem>
                                                <SelectItem value="yes">Yes — sponsored</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>CoS Number</Label>
                                        <Input value={formData.cos_number || ''} onChange={e => setFormData({ ...formData, cos_number: e.target.value })} placeholder="Certificate of Sponsorship" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Visa Type</Label>
                                        <Input value={formData.visa_type || ''} onChange={e => setFormData({ ...formData, visa_type: e.target.value })} placeholder="e.g. Skilled Worker" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Visa Expiry Date</Label>
                                        <Input type="date" value={formData.visa_expiry_date?.slice(0, 10) || ''} onChange={e => setFormData({ ...formData, visa_expiry_date: e.target.value })} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>SOC Code</Label>
                                        <Input value={formData.soc_code || ''} onChange={e => setFormData({ ...formData, soc_code: e.target.value })} placeholder="e.g. 2135" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Salary on CoS (£)</Label>
                                        <Input type="number" value={formData.cos_salary || ''} onChange={e => setFormData({ ...formData, cos_salary: parseFloat(e.target.value) || null })} placeholder="e.g. 38700" />
                                    </div>
                                </div>
                                <SaveButton section="rtw" />
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* Emergency Contacts */}
                <TabsContent value="emergency">
                    <Card>
                        <CardHeader>
                            <CardTitle>Emergency Contacts</CardTitle>
                            <CardDescription>People to contact in case of emergency</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {emergencyContacts.length === 0 ? (
                                <div className="text-center py-8 text-muted-foreground">
                                    <User className="w-12 h-12 mx-auto opacity-50" />
                                    <p className="mt-3 text-sm">No emergency contacts added</p>
                                    <p className="text-xs mt-1">Add an emergency contact in the employee profile form</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {emergencyContacts.map((c, i) => (
                                        <div key={i} className="rounded-lg border p-4">
                                            <div className="flex items-start justify-between">
                                                <div>
                                                    <p className="font-medium">{c.name}</p>
                                                    <p className="text-sm text-muted-foreground">{c.relationship}</p>
                                                </div>
                                                {c.is_primary && <Badge className="bg-indigo-100 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300">Primary</Badge>}
                                            </div>
                                            <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-muted-foreground">
                                                {c.phone && <span className="flex items-center gap-1"><Phone className="w-3.5 h-3.5" />{c.phone}</span>}
                                                {c.email && <span className="flex items-center gap-1"><Mail className="w-3.5 h-3.5" />{c.email}</span>}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                            {/* Quick add from form data */}
                            {(formData.emergency_name || formData.emergency_phone) && emergencyContacts.length === 0 && (
                                <div className="mt-4 rounded-lg border p-4 bg-muted/30">
                                    <p className="text-xs text-muted-foreground mb-2">From employee record:</p>
                                    <p className="font-medium">{formData.emergency_name}</p>
                                    <p className="text-sm text-muted-foreground">{formData.emergency_relationship} · {formData.emergency_phone}</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Documents */}
                <TabsContent value="documents">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle>Documents</CardTitle>
                                    <CardDescription>Employee evidence pack, contracts, and compliance documents</CardDescription>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            {documents.length === 0 ? (
                                <div className="text-center py-8 text-muted-foreground">
                                    <FileText className="w-12 h-12 mx-auto opacity-50" />
                                    <p className="mt-3 text-sm">No documents uploaded</p>
                                    <p className="text-xs mt-1">Upload documents from the Documents module</p>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {documents.map((doc) => (
                                        <div key={doc.document_id} className="flex items-center justify-between p-3 rounded-lg border">
                                            <div className="flex items-center gap-3">
                                                <FileText className="w-4 h-4 text-muted-foreground" />
                                                <div>
                                                    <p className="font-medium text-sm">{doc.title || doc.name}</p>
                                                    <p className="text-xs text-muted-foreground">{doc.category} {doc.expiry_date && `· Expires ${formatDate(doc.expiry_date)}`}</p>
                                                </div>
                                            </div>
                                            <Badge className={doc.expiry_date && new Date(doc.expiry_date) < new Date() ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-700'}>
                                                {doc.expiry_date && new Date(doc.expiry_date) < new Date() ? 'Expired' : doc.status || 'Active'}
                                            </Badge>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Leave History Tab */}
                <TabsContent value="leave">
                    <Card>
                        <CardHeader><CardTitle>Leave History</CardTitle></CardHeader>
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
                                                <p className="font-medium capitalize">{leave.leave_type?.replace('_', ' ')}</p>
                                                <p className="text-sm text-muted-foreground">
                                                    {formatDate(leave.start_date)} – {formatDate(leave.end_date)} ({leave.days} days)
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
                        <CardHeader><CardTitle>Recent Shifts</CardTitle></CardHeader>
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
                                                <p className="text-sm text-muted-foreground">{shift.start_time} – {shift.end_time}</p>
                                            </div>
                                            <Badge className={getStatusColor(shift.status)}>{shift.status}</Badge>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Notes Tab */}
                <TabsContent value="notes">
                    <Card>
                        <CardHeader>
                            <CardTitle>Notes</CardTitle>
                            <CardDescription>Internal HR notes — not visible to the employee</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex gap-3">
                                <Textarea
                                    value={newNote}
                                    onChange={e => setNewNote(e.target.value)}
                                    placeholder="Add an internal note…"
                                    rows={3}
                                    className="flex-1"
                                />
                                <Button onClick={addNote} disabled={!newNote.trim()} className="self-start bg-indigo-600 hover:bg-indigo-700">
                                    <Plus className="w-4 h-4 mr-1" /> Add
                                </Button>
                            </div>
                            {notes.length === 0 ? (
                                <p className="text-sm text-muted-foreground text-center py-4">No notes yet.</p>
                            ) : (
                                <div className="space-y-3">
                                    {notes.map((note, i) => (
                                        <div key={note.note_id || i} className="rounded-lg border p-3 text-sm">
                                            <p>{note.content}</p>
                                            <p className="text-xs text-muted-foreground mt-1">{note.author} · {new Date(note.created_at).toLocaleString()}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Lifecycle / Status History */}
                <TabsContent value="lifecycle">
                    <div className="space-y-4">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-base">
                                    <Activity className="w-4 h-4 text-indigo-600" /> Change Lifecycle Status
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                <p className="text-sm text-muted-foreground">Current status: <strong>{(employee.status || 'active').replace(/_/g, ' ')}</strong></p>
                                <div className="flex flex-wrap gap-2">
                                    {['onboarding', 'active', 'on_leave', 'suspended', 'notice_period', 'leaver', 'archived'].map(s => (
                                        <Button
                                            key={s}
                                            variant={employee.status === s ? 'default' : 'outline'}
                                            size="sm"
                                            disabled={employee.status === s}
                                            onClick={() => changeLifecycleStatus(s)}
                                        >
                                            {s.replace(/_/g, ' ')}
                                        </Button>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader><CardTitle className="text-base">Status History</CardTitle></CardHeader>
                            <CardContent>
                                {statusHistory.length === 0 ? (
                                    <p className="text-sm text-muted-foreground text-center py-4">No status changes recorded yet.</p>
                                ) : (
                                    <div className="space-y-2">
                                        {statusHistory.map((h, i) => (
                                            <div key={h.history_id || i} className="flex items-start justify-between p-3 rounded-lg border text-sm">
                                                <div>
                                                    <span className="font-medium">{h.previous_status}</span>
                                                    <span className="text-muted-foreground mx-2">→</span>
                                                    <span className="font-medium">{h.new_status}</span>
                                                    {h.reason && <p className="text-xs text-muted-foreground mt-0.5">{h.reason}</p>}
                                                </div>
                                                <span className="text-xs text-muted-foreground whitespace-nowrap">{new Date(h.changed_at).toLocaleString()}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* Audit Trail */}
                <TabsContent value="audit">
                    <Card>
                        <CardHeader>
                            <CardTitle>Audit Trail</CardTitle>
                            <CardDescription>Immutable record of all changes to this employee's record</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {auditLog.length === 0 ? (
                                <div className="text-center py-8 text-muted-foreground">
                                    <Building2 className="w-12 h-12 mx-auto opacity-50" />
                                    <p className="mt-3 text-sm">No audit entries yet</p>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {auditLog.slice(0, 50).map((entry, i) => (
                                        <div key={entry.audit_id || i} className="flex items-start justify-between p-3 rounded-lg border text-sm">
                                            <div>
                                                <p className="font-medium">{entry.action?.replace(/_/g, ' ')}</p>
                                                <p className="text-xs text-muted-foreground">
                                                    {entry.user_name || entry.user_email} · {entry.field && `Field: ${entry.field}`}
                                                </p>
                                                {entry.before && <p className="text-xs text-muted-foreground mt-0.5">Before: {JSON.stringify(entry.before)}</p>}
                                                {entry.after && <p className="text-xs text-muted-foreground">After: {JSON.stringify(entry.after)}</p>}
                                            </div>
                                            <span className="text-xs text-muted-foreground whitespace-nowrap ml-4">{new Date(entry.timestamp || entry.created_at).toLocaleString()}</span>
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
