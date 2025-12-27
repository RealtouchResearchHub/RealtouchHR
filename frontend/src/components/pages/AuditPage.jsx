import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { 
    Shield,
    User,
    FileText,
    CreditCard,
    Calendar,
    Clock,
    CheckCircle2,
    AlertTriangle,
    Settings,
    ArrowRight
} from 'lucide-react';
import { cn, formatDateTime } from '../../lib/utils';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const actionIcons = {
    create: CheckCircle2,
    update: Settings,
    delete: AlertTriangle,
    clock_in: Clock,
    clock_out: Clock
};

const entityIcons = {
    employee: User,
    company: Settings,
    leave: Calendar,
    document: FileText,
    shift: Clock,
    payrun: CreditCard,
    timesheet: Clock,
    compliance_task: Shield
};

export default function AuditPage() {
    const [auditLog, setAuditLog] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchAuditLog();
    }, []);

    const fetchAuditLog = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/audit`, { withCredentials: true });
            setAuditLog(response.data);
        } catch (error) {
            console.error('Failed to load audit log:', error);
        } finally {
            setLoading(false);
        }
    };

    const getActionColor = (action) => {
        switch (action) {
            case 'create': return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
            case 'update': return 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400';
            case 'delete': return 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400';
            case 'clock_in': return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
            case 'clock_out': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
            default: return 'bg-slate-100 text-slate-700 dark:bg-slate-900/30 dark:text-slate-400';
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
        <div className="space-y-6" data-testid="audit-page">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Audit Log</h1>
                <p className="text-muted-foreground mt-1">Immutable record of all system activities</p>
            </div>

            {/* Info Banner */}
            <Card className="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30 border-indigo-100 dark:border-indigo-900/50">
                <CardContent className="p-6">
                    <div className="flex items-start gap-4">
                        <div className="p-3 rounded-xl bg-indigo-100 dark:bg-indigo-900/50">
                            <Shield className="w-6 h-6 text-indigo-600" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-lg">Compliance Audit Trail</h3>
                            <p className="text-muted-foreground mt-1">
                                Every action is logged with timestamp, user, and reason. This immutable record supports GDPR compliance and audit requirements.
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Audit Timeline */}
            <Card data-testid="audit-timeline">
                <CardHeader>
                    <CardTitle>Activity Timeline</CardTitle>
                </CardHeader>
                <CardContent>
                    {auditLog.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                            <Shield className="w-12 h-12 mx-auto opacity-50" />
                            <p className="mt-4">No activity recorded yet</p>
                        </div>
                    ) : (
                        <ScrollArea className="h-[600px] pr-4">
                            <div className="space-y-4">
                                {auditLog.map((entry, index) => {
                                    const ActionIcon = actionIcons[entry.action] || Settings;
                                    const EntityIcon = entityIcons[entry.entity_type] || FileText;
                                    
                                    return (
                                        <div 
                                            key={entry.audit_id}
                                            className="flex gap-4 p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors"
                                        >
                                            {/* Timeline dot */}
                                            <div className="relative">
                                                <div className={cn(
                                                    "w-10 h-10 rounded-full flex items-center justify-center",
                                                    getActionColor(entry.action)
                                                )}>
                                                    <ActionIcon className="w-5 h-5" />
                                                </div>
                                                {index < auditLog.length - 1 && (
                                                    <div className="absolute top-10 left-1/2 -translate-x-1/2 w-0.5 h-full bg-border" />
                                                )}
                                            </div>

                                            {/* Content */}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-start justify-between gap-4">
                                                    <div>
                                                        <div className="flex items-center gap-2 flex-wrap">
                                                            <span className="font-medium">{entry.user_name}</span>
                                                            <Badge className={getActionColor(entry.action)}>
                                                                {entry.action.replace('_', ' ')}
                                                            </Badge>
                                                            <span className="text-muted-foreground">•</span>
                                                            <div className="flex items-center gap-1 text-muted-foreground">
                                                                <EntityIcon className="w-4 h-4" />
                                                                <span className="capitalize">{entry.entity_type.replace('_', ' ')}</span>
                                                            </div>
                                                        </div>
                                                        
                                                        {entry.details && Object.keys(entry.details).length > 0 && (
                                                            <div className="mt-2 text-sm text-muted-foreground">
                                                                {Object.entries(entry.details).map(([key, value]) => (
                                                                    <span key={key} className="mr-3">
                                                                        <span className="font-medium capitalize">{key.replace('_', ' ')}:</span>{' '}
                                                                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                                                    </span>
                                                                ))}
                                                            </div>
                                                        )}

                                                        {entry.reason && (
                                                            <p className="mt-1 text-sm text-muted-foreground italic">
                                                                Reason: {entry.reason}
                                                            </p>
                                                        )}
                                                    </div>
                                                    
                                                    <span className="text-xs text-muted-foreground whitespace-nowrap">
                                                        {formatDateTime(entry.timestamp)}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </ScrollArea>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
