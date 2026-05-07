import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Progress } from '../ui/progress';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../ui/select';
import { 
    Building2,
    Users,
    CreditCard,
    CheckCircle2,
    ArrowRight,
    ArrowLeft,
    Sparkles,
    Rocket
} from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const steps = [
    { id: 'company', title: 'Company Setup', icon: Building2, description: 'Tell us about your business' },
    { id: 'employee', title: 'First Employee', icon: Users, description: 'Add your first team member' },
    { id: 'payroll', title: 'Payroll Preview', icon: CreditCard, description: 'See your first payslip' },
    { id: 'complete', title: 'All Done!', icon: CheckCircle2, description: 'Ready to go' }
];

export default function OnboardingWizard() {
    const navigate = useNavigate();
    const { company, refreshCompany } = useAuth();
    const [currentStep, setCurrentStep] = useState(0);
    const [loading, setLoading] = useState(false);
    const [progress, setProgress] = useState(null);
    
    const [companyData, setCompanyData] = useState({
        name: '',
        industry: '',
        size: '',
        payroll_frequency: 'monthly'
    });
    
    const [employeeData, setEmployeeData] = useState({
        first_name: '',
        last_name: '',
        email: '',
        job_title: '',
        salary: ''
    });
    
    const [payRun, setPayRun] = useState(null);

    useEffect(() => {
        fetchProgress();
    }, []);

    const fetchProgress = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/onboarding/progress`, { withCredentials: true });
            setProgress(response.data);
            
            // Set initial step based on progress
            if (response.data.completed) {
                setCurrentStep(3);
            } else if (response.data.first_payrun_created) {
                setCurrentStep(3);
            } else if (response.data.first_employee_added) {
                setCurrentStep(2);
            } else if (response.data.completed_steps.includes('company_setup')) {
                setCurrentStep(1);
            }
            
            // Pre-fill company data if exists
            if (company) {
                setCompanyData({
                    name: company.name || '',
                    industry: company.industry || '',
                    size: company.size || '',
                    payroll_frequency: company.payroll_frequency || 'monthly'
                });
            }
        } catch (error) {
            console.error('Failed to fetch progress:', error);
        }
    };

    const handleCompanySubmit = async () => {
        if (!companyData.name) {
            toast.error('Please enter your company name');
            return;
        }
        
        setLoading(true);
        try {
            await axios.put(`${API_URL}/api/company`, companyData, { withCredentials: true });
            await refreshCompany();
            toast.success('Company details saved!');
            setCurrentStep(1);
        } catch (error) {
            toast.error('Failed to save company details');
        } finally {
            setLoading(false);
        }
    };

    const handleEmployeeSubmit = async () => {
        if (!employeeData.first_name || !employeeData.last_name || !employeeData.email) {
            toast.error('Please fill in all required fields');
            return;
        }
        
        setLoading(true);
        try {
            const data = {
                ...employeeData,
                salary: employeeData.salary ? parseFloat(employeeData.salary) : null
            };
            
            const response = await axios.post(`${API_URL}/api/onboarding/quick-employee`, data, { withCredentials: true });
            toast.success('Employee added!');
            setCurrentStep(2);
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to add employee');
        } finally {
            setLoading(false);
        }
    };

    const handlePayrollPreview = async () => {
        setLoading(true);
        try {
            const response = await axios.post(`${API_URL}/api/onboarding/quick-payrun`, {}, { withCredentials: true });
            setPayRun(response.data.pay_run);
            toast.success('Payroll preview created!');
            setCurrentStep(3);
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to create payroll preview');
        } finally {
            setLoading(false);
        }
    };

    const handleFinish = () => {
        navigate('/dashboard');
    };

    const progressPercentage = ((currentStep + 1) / steps.length) * 100;

    return (
        <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-background dark:to-background flex items-center justify-center p-6" data-testid="onboarding-wizard">
            <div className="w-full max-w-2xl">
                {/* Progress */}
                <div className="mb-8">
                    <div className="flex items-center justify-between mb-4">
                        {steps.map((step, index) => (
                            <div key={step.id} className="flex flex-col items-center flex-1">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                                    index <= currentStep 
                                        ? 'bg-indigo-600 text-white' 
                                        : 'bg-muted text-muted-foreground'
                                }`}>
                                    {index < currentStep ? (
                                        <CheckCircle2 className="w-5 h-5" />
                                    ) : (
                                        <step.icon className="w-5 h-5" />
                                    )}
                                </div>
                                <span className={`text-xs mt-2 text-center ${index <= currentStep ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
                                    {step.title}
                                </span>
                            </div>
                        ))}
                    </div>
                    <Progress value={progressPercentage} className="h-2" />
                </div>

                {/* Step Content */}
                <Card className="shadow-xl">
                    {/* Step 1: Company Setup */}
                    {currentStep === 0 && (
                        <>
                            <CardHeader className="text-center">
                                <div className="w-16 h-16 rounded-2xl bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center mx-auto mb-4">
                                    <Building2 className="w-8 h-8 text-indigo-600" />
                                </div>
                                <CardTitle className="text-2xl font-['Plus_Jakarta_Sans']">Let's set up your company</CardTitle>
                                <CardDescription>This will only take a minute</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                <div className="space-y-2">
                                    <Label htmlFor="company_name">Company Name *</Label>
                                    <Input
                                        id="company_name"
                                        value={companyData.name}
                                        onChange={(e) => setCompanyData({ ...companyData, name: e.target.value })}
                                        placeholder="e.g. Acme Ltd"
                                        data-testid="input-company-name"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="industry">Industry</Label>
                                        <Input
                                            id="industry"
                                            value={companyData.industry}
                                            onChange={(e) => setCompanyData({ ...companyData, industry: e.target.value })}
                                            placeholder="e.g. Technology"
                                            data-testid="input-industry"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Company Size</Label>
                                        <Select
                                            value={companyData.size}
                                            onValueChange={(value) => setCompanyData({ ...companyData, size: value })}
                                        >
                                            <SelectTrigger data-testid="select-size">
                                                <SelectValue placeholder="Select size" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="1-10">1-10 employees</SelectItem>
                                                <SelectItem value="11-50">11-50 employees</SelectItem>
                                                <SelectItem value="51-200">51-200 employees</SelectItem>
                                                <SelectItem value="200+">200+ employees</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <Label>Payroll Frequency</Label>
                                    <Select
                                        value={companyData.payroll_frequency}
                                        onValueChange={(value) => setCompanyData({ ...companyData, payroll_frequency: value })}
                                    >
                                        <SelectTrigger data-testid="select-frequency">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="weekly">Weekly</SelectItem>
                                            <SelectItem value="bi-weekly">Bi-weekly</SelectItem>
                                            <SelectItem value="monthly">Monthly</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <Button 
                                    className="w-full bg-indigo-600 hover:bg-indigo-700" 
                                    onClick={handleCompanySubmit}
                                    disabled={loading}
                                    data-testid="continue-btn"
                                >
                                    {loading ? 'Saving...' : 'Continue'}
                                    <ArrowRight className="w-4 h-4 ml-2" />
                                </Button>
                            </CardContent>
                        </>
                    )}

                    {/* Step 2: First Employee */}
                    {currentStep === 1 && (
                        <>
                            <CardHeader className="text-center">
                                <div className="w-16 h-16 rounded-2xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-4">
                                    <Users className="w-8 h-8 text-emerald-600" />
                                </div>
                                <CardTitle className="text-2xl font-['Plus_Jakarta_Sans']">Add your first employee</CardTitle>
                                <CardDescription>This can be yourself or a team member</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="first_name">First Name *</Label>
                                        <Input
                                            id="first_name"
                                            value={employeeData.first_name}
                                            onChange={(e) => setEmployeeData({ ...employeeData, first_name: e.target.value })}
                                            data-testid="input-first-name"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="last_name">Last Name *</Label>
                                        <Input
                                            id="last_name"
                                            value={employeeData.last_name}
                                            onChange={(e) => setEmployeeData({ ...employeeData, last_name: e.target.value })}
                                            data-testid="input-last-name"
                                        />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="email">Email *</Label>
                                    <Input
                                        id="email"
                                        type="email"
                                        value={employeeData.email}
                                        onChange={(e) => setEmployeeData({ ...employeeData, email: e.target.value })}
                                        data-testid="input-email"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="job_title">Job Title</Label>
                                        <Input
                                            id="job_title"
                                            value={employeeData.job_title}
                                            onChange={(e) => setEmployeeData({ ...employeeData, job_title: e.target.value })}
                                            data-testid="input-job-title"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="salary">Annual Salary (£)</Label>
                                        <Input
                                            id="salary"
                                            type="number"
                                            value={employeeData.salary}
                                            onChange={(e) => setEmployeeData({ ...employeeData, salary: e.target.value })}
                                            placeholder="e.g. 35000"
                                            data-testid="input-salary"
                                        />
                                    </div>
                                </div>
                                <div className="flex gap-3">
                                    <Button variant="outline" onClick={() => setCurrentStep(0)} data-testid="back-btn">
                                        <ArrowLeft className="w-4 h-4 mr-2" />
                                        Back
                                    </Button>
                                    <Button 
                                        className="flex-1 bg-indigo-600 hover:bg-indigo-700" 
                                        onClick={handleEmployeeSubmit}
                                        disabled={loading}
                                        data-testid="continue-btn"
                                    >
                                        {loading ? 'Adding...' : 'Continue'}
                                        <ArrowRight className="w-4 h-4 ml-2" />
                                    </Button>
                                </div>
                            </CardContent>
                        </>
                    )}

                    {/* Step 3: Payroll Preview */}
                    {currentStep === 2 && (
                        <>
                            <CardHeader className="text-center">
                                <div className="w-16 h-16 rounded-2xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center mx-auto mb-4">
                                    <CreditCard className="w-8 h-8 text-purple-600" />
                                </div>
                                <CardTitle className="text-2xl font-['Plus_Jakarta_Sans']">Generate payroll preview</CardTitle>
                                <CardDescription>See how your first payslip looks</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                <div className="bg-muted/50 rounded-xl p-6 text-center">
                                    <Sparkles className="w-12 h-12 mx-auto text-purple-500 mb-4" />
                                    <p className="text-muted-foreground">
                                        Click below to generate a payroll preview for this month. 
                                        We'll calculate PAYE, NI, and pension contributions automatically.
                                    </p>
                                </div>
                                <div className="flex gap-3">
                                    <Button variant="outline" onClick={() => setCurrentStep(1)} data-testid="back-btn">
                                        <ArrowLeft className="w-4 h-4 mr-2" />
                                        Back
                                    </Button>
                                    <Button 
                                        className="flex-1 bg-indigo-600 hover:bg-indigo-700" 
                                        onClick={handlePayrollPreview}
                                        disabled={loading}
                                        data-testid="generate-payroll-btn"
                                    >
                                        {loading ? 'Generating...' : 'Generate Preview'}
                                        <Sparkles className="w-4 h-4 ml-2" />
                                    </Button>
                                </div>
                            </CardContent>
                        </>
                    )}

                    {/* Step 4: Complete */}
                    {currentStep === 3 && (
                        <>
                            <CardHeader className="text-center">
                                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-emerald-500/30">
                                    <Rocket className="w-10 h-10 text-white" />
                                </div>
                                <CardTitle className="text-2xl font-['Plus_Jakarta_Sans']">You're all set!</CardTitle>
                                <CardDescription>Your HR &amp; payroll system is ready to use</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                <div className="bg-emerald-50 dark:bg-emerald-950/30 rounded-xl p-6">
                                    <h3 className="font-semibold text-emerald-700 dark:text-emerald-400 mb-3">What you've accomplished:</h3>
                                    <ul className="space-y-2">
                                        <li className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                                            <CheckCircle2 className="w-4 h-4" />
                                            Company profile configured
                                        </li>
                                        <li className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                                            <CheckCircle2 className="w-4 h-4" />
                                            First employee added
                                        </li>
                                        <li className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                                            <CheckCircle2 className="w-4 h-4" />
                                            Payroll preview generated
                                        </li>
                                    </ul>
                                </div>

                                {/* Module tour — what's next */}
                                <div>
                                    <h3 className="font-semibold mb-3">Explore what's next:</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {[
                                            { label: 'HMRC RTI submissions', desc: 'Submit FPS/EPS to HMRC', href: '/hmrc' },
                                            { label: 'UKVI compliance', desc: 'Track visas + sponsor licence', href: '/ukvi' },
                                            { label: 'Statutory Pay', desc: 'SSP/SMP/SPP/ShPP/SAP calculators', href: '/statutory' },
                                            { label: 'Time & Scheduling', desc: 'Clock-ins, shifts, timesheets', href: '/time-tracking' },
                                            { label: 'Year-End Close', desc: 'Generate P60s + EPS finalise', href: '/year-end' },
                                            { label: 'Invite your team', desc: 'Assign roles: admin, HR, payroll', href: '/admin' },
                                            { label: 'Billing', desc: 'Upgrade plan, manage payment methods', href: '/billing' },
                                            { label: 'Settings — HMRC refs', desc: 'PAYE / AOR / sponsor licence', href: '/settings' },
                                        ].map((m) => (
                                            <button
                                                key={m.href}
                                                onClick={() => navigate(m.href)}
                                                className="text-left p-3 border rounded-lg hover:border-indigo-400 hover:bg-indigo-50/40 dark:hover:bg-indigo-950/20 transition"
                                                data-testid={`wizard-module-${m.href.replace('/', '')}`}
                                            >
                                                <p className="text-sm font-medium">{m.label}</p>
                                                <p className="text-xs text-muted-foreground mt-0.5">{m.desc}</p>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <Button 
                                    className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700" 
                                    onClick={handleFinish}
                                    data-testid="go-to-dashboard-btn"
                                >
                                    Go to Dashboard
                                    <ArrowRight className="w-4 h-4 ml-2" />
                                </Button>
                            </CardContent>
                        </>
                    )}
                </Card>

                {/* Skip Link */}
                {currentStep < 3 && (
                    <p className="text-center mt-4">
                        <button 
                            className="text-sm text-muted-foreground hover:text-foreground underline"
                            onClick={() => navigate('/dashboard')}
                            data-testid="skip-wizard-btn"
                        >
                            Skip for now, I'll set up later
                        </button>
                    </p>
                )}
            </div>
        </div>
    );
}
