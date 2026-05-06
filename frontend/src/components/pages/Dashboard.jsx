import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import ComplianceScore from '../shared/ComplianceScore';
import NextActionBanner from '../shared/NextActionBanner';
import { DemoLauncherCard } from '../shared/DemoTour';
import { 
    Users, 
    Calendar, 
    CreditCard, 
    Clock,
    ArrowRight,
    TrendingUp,
    AlertTriangle,
    CheckCircle2,
    Plus
} from 'lucide-react';
import { cn, formatCurrency, getStatusColor } from '../../lib/utils';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Dashboard() {
    const { user, company } = useAuth();
    const [stats, setStats] = useState(null);
    const [employees, setEmployees] = useState([]);
    const [recentLeaves, setRecentLeaves] = useState([]);
    const [loading, setLoading] = useState(true);
    const [demoStatus, setDemoStatus] = useState({ demo_mode: false });

    const fetchData = async () => {
        try {
            const token = localStorage.getItem('token');
            const headers = { Authorization: `Bearer ${token}` };
            const [statsRes, empRes, leaveRes, demoRes] = await Promise.all([
                axios.get(`${API_URL}/api/dashboard/stats`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/employees`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/leave`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/demo/status`, { headers, withCredentials: true }).catch(() => ({ data: { demo_mode: false } })),
            ]);
            setStats(statsRes.data);
            setEmployees(empRes.data.slice(0, 5));
            setRecentLeaves(leaveRes.data.slice(0, 5));
            setDemoStatus(demoRes.data || { demo_mode: false });
        } catch (error) {
            console.error('Error fetching dashboard data:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleStartTour = (steps) => {
        // Persist steps in localStorage so MainLayout DemoTour can pick them up
        localStorage.setItem('demo_tour_steps', JSON.stringify(steps));
        localStorage.setItem('demo_tour_active', 'true');
        // Force MainLayout to re-render via storage event (synthetic)
        window.dispatchEvent(new Event('demo-tour-start'));
        fetchData();
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    const statCards = [
        {
            title: 'Total Employees',
            value: stats?.total_employees || 0,
            icon: Users,
            color: 'text-indigo-600 bg-indigo-100 dark:bg-indigo-900/30',
            link: '/employees'
        },
        {
            title: 'On Leave Today',
            value: stats?.on_leave_today || 0,
            icon: Calendar,
            color: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30',
            link: '/leave'
        },
        {
            title: 'Pending Approvals',
            value: stats?.pending_approvals || 0,
            icon: Clock,
            color: 'text-rose-600 bg-rose-100 dark:bg-rose-900/30',
            link: '/leave'
        }
    ];

    return (
        <div className="space-y-8" data-testid="dashboard-page">
            {/* Welcome Header */}
            <div>
                <h1 className="text-3xl lg:text-4xl font-bold font-['Plus_Jakarta_Sans'] text-foreground">
                    Welcome back, {user?.name?.split(' ')[0]}
                </h1>
                <p className="mt-2 text-lg text-muted-foreground">
                    Here's what's happening with your HR today.
                </p>
            </div>

            {/* Next Best Action - Hero */}
            <NextActionBanner action={stats?.next_action} />

            {/* Demo launcher - prominent if no demo seeded yet */}
            <DemoLauncherCard
                isSeeded={demoStatus.demo_mode}
                onStart={handleStartTour}
                onReset={fetchData}
            />

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {statCards.map((stat, index) => (
                    <Link key={index} to={stat.link}>
                        <Card className="hover:shadow-md transition-all hover-lift cursor-pointer" data-testid={`stat-card-${stat.title.toLowerCase().replace(/\s+/g, '-')}`}>
                            <CardContent className="p-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm font-medium text-muted-foreground">{stat.title}</p>
                                        <p className="text-3xl font-bold font-['Plus_Jakarta_Sans'] mt-1">{stat.value}</p>
                                    </div>
                                    <div className={cn("p-3 rounded-xl", stat.color)}>
                                        <stat.icon className="w-6 h-6" />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                ))}
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Compliance Score - Larger Card */}
                <Card className="lg:col-span-4 relative overflow-hidden bg-gradient-to-br from-emerald-50 to-white dark:from-emerald-950/30 dark:to-background border-emerald-100 dark:border-emerald-900/50" data-testid="compliance-score-card">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                            Compliance Status
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="flex flex-col items-center py-8">
                        <ComplianceScore score={stats?.compliance_score || 100} size="lg" />
                        <p className="mt-4 text-center text-muted-foreground">
                            {stats?.compliance_score >= 90 
                                ? 'Excellent! Your compliance is in great shape.'
                                : stats?.compliance_score >= 70
                                    ? 'Good, but there are some items to address.'
                                    : 'Attention needed. Please review compliance tasks.'
                            }
                        </p>
                        <Link to="/settings" className="mt-4">
                            <Button variant="outline" size="sm">
                                View Details
                                <ArrowRight className="w-4 h-4 ml-2" />
                            </Button>
                        </Link>
                    </CardContent>
                </Card>

                {/* Employee Directory Preview */}
                <Card className="lg:col-span-8" data-testid="employees-preview-card">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle>Employee Directory</CardTitle>
                        <Link to="/employees">
                            <Button variant="ghost" size="sm">
                                View All
                                <ArrowRight className="w-4 h-4 ml-1" />
                            </Button>
                        </Link>
                    </CardHeader>
                    <CardContent>
                        {employees.length === 0 ? (
                            <div className="text-center py-8">
                                <Users className="w-12 h-12 mx-auto text-muted-foreground/50" />
                                <p className="mt-4 text-muted-foreground">No employees yet</p>
                                <Link to="/employees/new">
                                    <Button className="mt-4" data-testid="add-first-employee-btn">
                                        <Plus className="w-4 h-4 mr-2" />
                                        Add Your First Employee
                                    </Button>
                                </Link>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {employees.map((emp) => (
                                    <Link 
                                        key={emp.employee_id} 
                                        to={`/employees/${emp.employee_id}`}
                                        className="flex items-center justify-between p-3 rounded-lg hover:bg-accent transition-colors"
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
                                                <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300">
                                                    {emp.first_name[0]}{emp.last_name[0]}
                                                </span>
                                            </div>
                                            <div>
                                                <p className="font-medium">{emp.first_name} {emp.last_name}</p>
                                                <p className="text-sm text-muted-foreground">{emp.job_title || 'No title'}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <Badge className={getStatusColor(emp.status)}>{emp.status}</Badge>
                                            {emp.compliance_score < 100 && (
                                                <AlertTriangle className="w-4 h-4 text-amber-500" />
                                            )}
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Link to="/employees/new">
                    <Card className="hover:shadow-md transition-all hover-lift cursor-pointer h-full" data-testid="quick-add-employee">
                        <CardContent className="p-6 flex flex-col items-center text-center">
                            <div className="p-3 rounded-xl bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 mb-3">
                                <Users className="w-6 h-6" />
                            </div>
                            <p className="font-medium">Add Employee</p>
                        </CardContent>
                    </Card>
                </Link>
                <Link to="/payroll/new">
                    <Card className="hover:shadow-md transition-all hover-lift cursor-pointer h-full" data-testid="quick-run-payroll">
                        <CardContent className="p-6 flex flex-col items-center text-center">
                            <div className="p-3 rounded-xl bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 mb-3">
                                <CreditCard className="w-6 h-6" />
                            </div>
                            <p className="font-medium">Run Payroll</p>
                        </CardContent>
                    </Card>
                </Link>
                <Link to="/scheduling">
                    <Card className="hover:shadow-md transition-all hover-lift cursor-pointer h-full" data-testid="quick-scheduling">
                        <CardContent className="p-6 flex flex-col items-center text-center">
                            <div className="p-3 rounded-xl bg-amber-100 dark:bg-amber-900/30 text-amber-600 mb-3">
                                <Clock className="w-6 h-6" />
                            </div>
                            <p className="font-medium">Scheduling</p>
                        </CardContent>
                    </Card>
                </Link>
                <Link to="/documents">
                    <Card className="hover:shadow-md transition-all hover-lift cursor-pointer h-full" data-testid="quick-documents">
                        <CardContent className="p-6 flex flex-col items-center text-center">
                            <div className="p-3 rounded-xl bg-purple-100 dark:bg-purple-900/30 text-purple-600 mb-3">
                                <TrendingUp className="w-6 h-6" />
                            </div>
                            <p className="font-medium">Documents</p>
                        </CardContent>
                    </Card>
                </Link>
            </div>
        </div>
    );
}
