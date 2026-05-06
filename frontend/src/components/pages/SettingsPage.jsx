import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { Badge } from '../ui/badge';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import ComplianceScore from '../shared/ComplianceScore';
import { 
    Building2,
    User,
    Shield,
    Bell,
    Palette,
    Sun,
    Moon,
    CheckCircle2,
    AlertTriangle
} from 'lucide-react';
import { cn, getStatusColor } from '../../lib/utils';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function SettingsPage() {
    const { user, company, updatePreferences, refreshCompany } = useAuth();
    const { theme, setTheme } = useTheme();
    const [companyData, setCompanyData] = useState({
        name: '',
        industry: '',
        size: '',
        address: '',
        payroll_frequency: 'monthly',
        paye_reference: '',
        accounts_office_reference: '',
        sponsor_licence_number: '',
        sponsor_licence_expiry: '',
        sponsor_licence_rating: '',
        small_employer_relief: false,
    });
    const [complianceScore, setComplianceScore] = useState(null);
    const [complianceTasks, setComplianceTasks] = useState([]);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (company) {
            setCompanyData({
                name: company.name || '',
                industry: company.industry || '',
                size: company.size || '',
                address: company.address || '',
                payroll_frequency: company.payroll_frequency || 'monthly',
                paye_reference: company.paye_reference || '',
                accounts_office_reference: company.accounts_office_reference || '',
                sponsor_licence_number: company.sponsor_licence_number || '',
                sponsor_licence_expiry: company.sponsor_licence_expiry || '',
                sponsor_licence_rating: company.sponsor_licence_rating || '',
                small_employer_relief: company.small_employer_relief || false,
            });
        }
        fetchCompliance();
    }, [company]);

    const fetchCompliance = async () => {
        try {
            const [scoreRes, tasksRes] = await Promise.all([
                axios.get(`${API_URL}/api/compliance/score`, { withCredentials: true }),
                axios.get(`${API_URL}/api/compliance/tasks`, { withCredentials: true })
            ]);
            setComplianceScore(scoreRes.data);
            setComplianceTasks(tasksRes.data);
        } catch (error) {
            console.error('Failed to fetch compliance:', error);
        }
    };

    const handleSaveCompany = async () => {
        setSaving(true);
        try {
            await axios.put(`${API_URL}/api/company`, companyData, { withCredentials: true });
            toast.success('Company settings saved');
            refreshCompany();
        } catch (error) {
            toast.error('Failed to save settings');
        } finally {
            setSaving(false);
        }
    };

    const handleCompleteSetup = async () => {
        setSaving(true);
        try {
            await axios.put(`${API_URL}/api/company`, { ...companyData, setup_completed: true }, { withCredentials: true });
            toast.success('Company setup completed!');
            refreshCompany();
        } catch (error) {
            toast.error('Failed to complete setup');
        } finally {
            setSaving(false);
        }
    };

    const handleThemeChange = async (newTheme) => {
        setTheme(newTheme);
        try {
            await updatePreferences({ theme_preference: newTheme });
        } catch (error) {
            console.error('Failed to save theme preference:', error);
        }
    };

    return (
        <div className="space-y-6" data-testid="settings-page">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Settings</h1>
                <p className="text-muted-foreground mt-1">Manage your company and account settings</p>
            </div>

            <Tabs defaultValue="company" className="space-y-6">
                <TabsList>
                    <TabsTrigger value="company" data-testid="tab-company">
                        <Building2 className="w-4 h-4 mr-2" />
                        Company
                    </TabsTrigger>
                    <TabsTrigger value="compliance" data-testid="tab-compliance">
                        <Shield className="w-4 h-4 mr-2" />
                        Compliance
                    </TabsTrigger>
                    <TabsTrigger value="appearance" data-testid="tab-appearance">
                        <Palette className="w-4 h-4 mr-2" />
                        Appearance
                    </TabsTrigger>
                </TabsList>

                {/* Company Tab */}
                <TabsContent value="company">
                    <Card>
                        <CardHeader>
                            <CardTitle>Company Information</CardTitle>
                            <CardDescription>Update your company details</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <Label htmlFor="company_name">Company Name</Label>
                                    <Input
                                        id="company_name"
                                        value={companyData.name}
                                        onChange={(e) => setCompanyData({ ...companyData, name: e.target.value })}
                                        data-testid="input-company-name"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="industry">Industry</Label>
                                    <Input
                                        id="industry"
                                        value={companyData.industry}
                                        onChange={(e) => setCompanyData({ ...companyData, industry: e.target.value })}
                                        placeholder="e.g. Technology, Retail, Healthcare"
                                        data-testid="input-industry"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="size">Company Size</Label>
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
                                            <SelectItem value="201-500">201-500 employees</SelectItem>
                                            <SelectItem value="500+">500+ employees</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="payroll_frequency">Payroll Frequency</Label>
                                    <Select
                                        value={companyData.payroll_frequency}
                                        onValueChange={(value) => setCompanyData({ ...companyData, payroll_frequency: value })}
                                    >
                                        <SelectTrigger data-testid="select-payroll-frequency">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="weekly">Weekly</SelectItem>
                                            <SelectItem value="bi-weekly">Bi-weekly</SelectItem>
                                            <SelectItem value="monthly">Monthly</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="address">Business Address</Label>
                                <Input
                                    id="address"
                                    value={companyData.address}
                                    onChange={(e) => setCompanyData({ ...companyData, address: e.target.value })}
                                    placeholder="Enter your business address"
                                    data-testid="input-address"
                                />
                            </div>

                            {/* HMRC References */}
                            <div className="pt-4 border-t">
                                <h4 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">HMRC references</h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <Label>PAYE reference</Label>
                                        <Input
                                            placeholder="e.g. 120/AB1234"
                                            value={companyData.paye_reference}
                                            onChange={(e) => setCompanyData({ ...companyData, paye_reference: e.target.value })}
                                            data-testid="input-paye-ref"
                                        />
                                        <p className="text-xs text-muted-foreground">Format: NNN/AANNNNNNN</p>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Accounts Office reference</Label>
                                        <Input
                                            placeholder="e.g. 120PA00012345"
                                            value={companyData.accounts_office_reference}
                                            onChange={(e) => setCompanyData({ ...companyData, accounts_office_reference: e.target.value })}
                                            data-testid="input-aor"
                                        />
                                        <p className="text-xs text-muted-foreground">Format: NNNPAANNNNNNNN</p>
                                    </div>
                                </div>
                                <div className="mt-4 flex items-center gap-2">
                                    <Switch
                                        checked={!!companyData.small_employer_relief}
                                        onCheckedChange={(v) => setCompanyData({ ...companyData, small_employer_relief: v })}
                                        data-testid="small-employer-toggle"
                                    />
                                    <Label className="cursor-pointer">Small employer relief (claim 103% recovery on statutory pay)</Label>
                                </div>
                            </div>

                            {/* Sponsor Licence */}
                            <div className="pt-4 border-t">
                                <h4 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">UKVI Sponsor Licence</h4>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    <div className="space-y-2">
                                        <Label>Licence number</Label>
                                        <Input
                                            placeholder="e.g. 1234567890"
                                            value={companyData.sponsor_licence_number}
                                            onChange={(e) => setCompanyData({ ...companyData, sponsor_licence_number: e.target.value })}
                                            data-testid="input-sponsor-licence"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Expiry date</Label>
                                        <Input
                                            type="date"
                                            value={companyData.sponsor_licence_expiry?.split('T')[0] || ''}
                                            onChange={(e) => setCompanyData({ ...companyData, sponsor_licence_expiry: e.target.value })}
                                            data-testid="input-sponsor-expiry"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Rating</Label>
                                        <Select
                                            value={companyData.sponsor_licence_rating || ''}
                                            onValueChange={(v) => setCompanyData({ ...companyData, sponsor_licence_rating: v })}
                                        >
                                            <SelectTrigger data-testid="select-sponsor-rating"><SelectValue placeholder="Select rating" /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="A">A-rated (full)</SelectItem>
                                                <SelectItem value="B">B-rated (action plan)</SelectItem>
                                                <SelectItem value="suspended">Suspended</SelectItem>
                                                <SelectItem value="none">None</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                            </div>

                            <div className="flex gap-3">
                                <Button onClick={handleSaveCompany} disabled={saving} data-testid="save-company-btn">
                                    {saving ? 'Saving...' : 'Save Changes'}
                                </Button>
                                {company && !company.setup_completed && (
                                    <Button 
                                        variant="outline" 
                                        onClick={handleCompleteSetup}
                                        disabled={saving}
                                        data-testid="complete-setup-btn"
                                    >
                                        Mark Setup Complete
                                    </Button>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Compliance Tab */}
                <TabsContent value="compliance">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Score Card */}
                        <Card className="lg:col-span-1 bg-gradient-to-br from-emerald-50 to-white dark:from-emerald-950/30 dark:to-background">
                            <CardHeader>
                                <CardTitle>Compliance Score</CardTitle>
                            </CardHeader>
                            <CardContent className="flex flex-col items-center py-8">
                                <ComplianceScore score={complianceScore?.score || 100} size="lg" />
                                <p className="mt-4 text-center text-muted-foreground">
                                    {complianceScore?.issues?.length || 0} issues to address
                                </p>
                            </CardContent>
                        </Card>

                        {/* Tasks Card */}
                        <Card className="lg:col-span-2">
                            <CardHeader>
                                <CardTitle>Compliance Tasks</CardTitle>
                                <CardDescription>Outstanding items that need attention</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {complianceTasks.length === 0 && (!complianceScore?.issues || complianceScore.issues.length === 0) ? (
                                    <div className="text-center py-8">
                                        <CheckCircle2 className="w-12 h-12 mx-auto text-emerald-500" />
                                        <p className="mt-4 font-medium">All caught up!</p>
                                        <p className="text-muted-foreground">No compliance issues to address</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {complianceTasks.map((task) => (
                                            <div 
                                                key={task.task_id}
                                                className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <AlertTriangle className="w-5 h-5 text-amber-500" />
                                                    <div>
                                                        <p className="font-medium">{task.title}</p>
                                                        <p className="text-sm text-muted-foreground">{task.description}</p>
                                                    </div>
                                                </div>
                                                <Badge className={getStatusColor(task.priority)}>{task.priority}</Badge>
                                            </div>
                                        ))}
                                        {complianceScore?.issues?.map((issue, index) => (
                                            <div 
                                                key={index}
                                                className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <AlertTriangle className="w-5 h-5 text-amber-500" />
                                                    <div>
                                                        <p className="font-medium">{issue.issue}</p>
                                                        <p className="text-sm text-muted-foreground">
                                                            Employee: {issue.employee_name}
                                                        </p>
                                                    </div>
                                                </div>
                                                <Badge className="bg-amber-100 text-amber-700">High</Badge>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* Appearance Tab */}
                <TabsContent value="appearance">
                    <Card>
                        <CardHeader>
                            <CardTitle>Appearance</CardTitle>
                            <CardDescription>Customize how RealtouchHR looks</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="space-y-4">
                                <Label>Theme</Label>
                                <div className="grid grid-cols-3 gap-4">
                                    <button
                                        onClick={() => handleThemeChange('light')}
                                        className={cn(
                                            "flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
                                            theme === 'light' 
                                                ? "border-indigo-600 bg-indigo-50 dark:bg-indigo-950/30" 
                                                : "border-border hover:border-indigo-300"
                                        )}
                                        data-testid="theme-light-btn"
                                    >
                                        <Sun className="w-8 h-8 text-amber-500" />
                                        <span className="font-medium">Light</span>
                                    </button>
                                    <button
                                        onClick={() => handleThemeChange('dark')}
                                        className={cn(
                                            "flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
                                            theme === 'dark' 
                                                ? "border-indigo-600 bg-indigo-50 dark:bg-indigo-950/30" 
                                                : "border-border hover:border-indigo-300"
                                        )}
                                        data-testid="theme-dark-btn"
                                    >
                                        <Moon className="w-8 h-8 text-indigo-500" />
                                        <span className="font-medium">Dark</span>
                                    </button>
                                    <button
                                        onClick={() => {
                                            const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                                            handleThemeChange(systemTheme);
                                        }}
                                        className={cn(
                                            "flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
                                            "border-border hover:border-indigo-300"
                                        )}
                                        data-testid="theme-system-btn"
                                    >
                                        <div className="flex">
                                            <Sun className="w-6 h-6 text-amber-500" />
                                            <Moon className="w-6 h-6 text-indigo-500 -ml-2" />
                                        </div>
                                        <span className="font-medium">System</span>
                                    </button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
