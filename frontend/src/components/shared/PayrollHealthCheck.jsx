import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { 
    AlertTriangle,
    CheckCircle2,
    XCircle,
    RefreshCw,
    ArrowRight,
    AlertCircle,
    User,
    Building2,
    CreditCard
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const severityColors = {
    critical: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400 border-rose-200 dark:border-rose-800',
    warning: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border-amber-200 dark:border-amber-800',
    info: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 border-blue-200 dark:border-blue-800'
};

const severityIcons = {
    critical: XCircle,
    warning: AlertTriangle,
    info: AlertCircle
};

const categoryIcons = {
    missing_data: User,
    anomaly: AlertCircle,
    compliance: Building2,
    banking: CreditCard
};

export default function PayrollHealthCheck({ payrunId, onHealthCheckComplete }) {
    const [healthCheck, setHealthCheck] = useState(null);
    const [loading, setLoading] = useState(false);
    const [hasRun, setHasRun] = useState(false);

    const runHealthCheck = async () => {
        setLoading(true);
        try {
            const response = await axios.get(
                `${API_URL}/api/payroll/health-check/${payrunId}`,
                { withCredentials: true }
            );
            setHealthCheck(response.data);
            setHasRun(true);
            
            if (onHealthCheckComplete) {
                onHealthCheckComplete(response.data);
            }
            
            if (response.data.overall_status === 'pass') {
                toast.success('Health check passed! Ready to proceed.');
            } else if (response.data.overall_status === 'warning') {
                toast.warning('Health check completed with warnings.');
            } else {
                toast.error('Health check failed. Please resolve critical issues.');
            }
        } catch (error) {
            toast.error('Failed to run health check');
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'pass': return 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30';
            case 'warning': return 'text-amber-600 bg-amber-100 dark:bg-amber-900/30';
            case 'fail': return 'text-rose-600 bg-rose-100 dark:bg-rose-900/30';
            default: return 'text-slate-600 bg-slate-100 dark:bg-slate-900/30';
        }
    };

    const getScoreColor = (score) => {
        if (score >= 90) return 'text-emerald-600';
        if (score >= 70) return 'text-amber-600';
        return 'text-rose-600';
    };

    if (!hasRun) {
        return (
            <Card className="border-2 border-dashed" data-testid="health-check-prompt">
                <CardContent className="py-12 text-center">
                    <div className="w-16 h-16 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center mx-auto mb-4">
                        <CheckCircle2 className="w-8 h-8 text-indigo-600" />
                    </div>
                    <h3 className="text-lg font-semibold mb-2">Payroll Health Check</h3>
                    <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                        Run a comprehensive health check to identify missing data, anomalies, and compliance issues before processing payroll.
                    </p>
                    <Button 
                        onClick={runHealthCheck} 
                        disabled={loading}
                        className="bg-indigo-600 hover:bg-indigo-700"
                        data-testid="run-health-check-btn"
                    >
                        {loading ? (
                            <>
                                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                                Running Check...
                            </>
                        ) : (
                            <>
                                <CheckCircle2 className="w-4 h-4 mr-2" />
                                Run Health Check
                            </>
                        )}
                    </Button>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card data-testid="health-check-results">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            {healthCheck?.overall_status === 'pass' ? (
                                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                            ) : healthCheck?.overall_status === 'warning' ? (
                                <AlertTriangle className="w-5 h-5 text-amber-600" />
                            ) : (
                                <XCircle className="w-5 h-5 text-rose-600" />
                            )}
                            Payroll Health Check
                        </CardTitle>
                        <CardDescription>
                            Checked on {new Date(healthCheck?.check_date).toLocaleString()}
                        </CardDescription>
                    </div>
                    <Button variant="outline" size="sm" onClick={runHealthCheck} disabled={loading}>
                        <RefreshCw className={cn("w-4 h-4 mr-2", loading && "animate-spin")} />
                        Re-run
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Score Overview */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className={cn("p-4 rounded-xl text-center", getStatusColor(healthCheck?.overall_status))}>
                        <p className="text-sm font-medium mb-1">Status</p>
                        <p className="text-2xl font-bold capitalize">{healthCheck?.overall_status}</p>
                    </div>
                    <div className="p-4 rounded-xl bg-muted text-center">
                        <p className="text-sm font-medium text-muted-foreground mb-1">Score</p>
                        <p className={cn("text-4xl font-bold", getScoreColor(healthCheck?.score))}>
                            {healthCheck?.score}%
                        </p>
                    </div>
                    <div className="p-4 rounded-xl bg-muted text-center">
                        <p className="text-sm font-medium text-muted-foreground mb-1">Issues Found</p>
                        <p className="text-2xl font-bold">{healthCheck?.issues?.length || 0}</p>
                    </div>
                </div>

                {/* Can Proceed Alert */}
                {healthCheck?.can_proceed ? (
                    <Alert className="border-emerald-200 bg-emerald-50 dark:bg-emerald-950/30">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        <AlertTitle className="text-emerald-700 dark:text-emerald-400">Ready to Proceed</AlertTitle>
                        <AlertDescription className="text-emerald-600 dark:text-emerald-400">
                            {healthCheck?.issues?.length > 0 
                                ? 'You can proceed with payroll, but consider resolving the warnings below.'
                                : 'All checks passed. You can proceed with payroll processing.'
                            }
                        </AlertDescription>
                    </Alert>
                ) : (
                    <Alert className="border-rose-200 bg-rose-50 dark:bg-rose-950/30">
                        <XCircle className="w-4 h-4 text-rose-600" />
                        <AlertTitle className="text-rose-700 dark:text-rose-400">Cannot Proceed</AlertTitle>
                        <AlertDescription className="text-rose-600 dark:text-rose-400">
                            Critical issues must be resolved before processing payroll.
                        </AlertDescription>
                    </Alert>
                )}

                {/* Issues List */}
                {healthCheck?.issues?.length > 0 && (
                    <div className="space-y-3">
                        <h4 className="font-semibold">Issues to Address</h4>
                        {healthCheck.issues.map((issue, index) => {
                            const SeverityIcon = severityIcons[issue.severity] || AlertCircle;
                            const CategoryIcon = categoryIcons[issue.category] || AlertCircle;
                            
                            return (
                                <div 
                                    key={index}
                                    className={cn("p-4 rounded-lg border", severityColors[issue.severity])}
                                >
                                    <div className="flex items-start gap-3">
                                        <SeverityIcon className="w-5 h-5 mt-0.5 flex-shrink-0" />
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="font-semibold">{issue.title}</span>
                                                <Badge variant="outline" className="text-xs">
                                                    {issue.severity}
                                                </Badge>
                                            </div>
                                            {issue.employee_name && (
                                                <p className="text-sm opacity-80 mb-1">
                                                    Employee: {issue.employee_name}
                                                </p>
                                            )}
                                            <p className="text-sm opacity-80">{issue.description}</p>
                                            <p className="text-sm font-medium mt-2 flex items-center gap-1">
                                                <ArrowRight className="w-3 h-3" />
                                                {issue.action_required}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
