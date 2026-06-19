import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import {
    BarChart3, Download, Calendar, Users, FileText, Clock,
    Loader2, RefreshCw, AlertTriangle, TrendingDown, Shield,
    Activity, Receipt, GraduationCap, MapPin, Briefcase,
} from 'lucide-react';

import { useAuth } from '../../contexts/AuthContext';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const REPORTS = [
    { key: 'absence',              label: 'Absence Report',              icon: Calendar,       desc: 'All absences by type, employee and date range',       dateFilter: true },
    { key: 'annual-leave-summary', label: 'Annual Leave Summary',        icon: Calendar,       desc: 'Entitlement, taken, pending and remaining per employee', dateFilter: false },
    { key: 'lateness',             label: 'Lateness Report',             icon: Clock,          desc: 'Late arrivals and duration over a period',             dateFilter: true },
    { key: 'sickness',             label: 'Sickness Report',             icon: Activity,       desc: 'Sickness spells, days and Bradford Factor per employee', dateFilter: true },
    { key: 'employee-details',     label: 'Employee Details Report',     icon: Users,          desc: 'Full employee data export — contracts, NI, salary',    dateFilter: false },
    { key: 'employee-information', label: 'Employee Information Report', icon: Users,          desc: 'Summary contact and contract info for all employees',  dateFilter: false },
    { key: 'length-of-service',    label: 'Length of Service',          icon: TrendingDown,   desc: 'Tenure calculated for all active employees',          dateFilter: false },
    { key: 'overtime',             label: 'Overtime Report',             icon: Clock,          desc: 'Pending and approved overtime requests by period',     dateFilter: true },
    { key: 'payroll-exceptions',   label: 'Payroll Exceptions Report',   icon: Receipt,        desc: 'Absence data formatted for payroll (SSP, SMP, unpaid)', dateFilter: false },
    { key: 'turnover-retention',   label: 'Turnover & Retention',        icon: TrendingDown,   desc: 'Leavers, reason for leaving and turnover rate',        dateFilter: true },
    { key: 'sensitive-documents',  label: 'Sensitive Documents Report',  icon: Shield,         desc: 'Document expiry tracking — passports, visas, certs',  dateFilter: false },
    { key: 'working-status',       label: 'Working Status Report',       icon: MapPin,         desc: "Current working location status for all employees",   dateFilter: false },
    { key: 'timesheet',            label: 'Timesheet Report',            icon: Clock,          desc: 'Clock-in/out data and total hours worked',             dateFilter: true },
    { key: 'rota',                 label: 'Rota Report',                 icon: Calendar,       desc: 'Scheduled shifts and hours per employee',             dateFilter: true },
    { key: 'training',             label: 'Training Report',             icon: GraduationCap,  desc: 'Course completions and mandatory training status',     dateFilter: false },
    { key: 'expenses',             label: 'Expenses Report',             icon: Receipt,        desc: 'Expense claims by employee and category',             dateFilter: true },
];

function ReportCard({ report, onRun, onDownload, running }) {
    const Icon = report.icon;
    const [dateFrom, setDateFrom] = useState('');
    const [dateTo, setDateTo] = useState('');
    const [preview, setPreview] = useState(null);

    const handleRun = async () => {
        const data = await onRun(report.key, dateFrom, dateTo);
        setPreview(data);
    };

    return (
        <Card className="flex flex-col">
            <CardHeader className="pb-3">
                <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/30">
                        <Icon className="w-5 h-5 text-indigo-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <CardTitle className="text-sm font-semibold">{report.label}</CardTitle>
                        <p className="text-xs text-muted-foreground mt-0.5">{report.desc}</p>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="pt-0 flex flex-col gap-3 flex-1">
                {report.dateFilter && (
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <Label className="text-xs">From</Label>
                            <Input type="date" className="h-8 text-xs" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
                        </div>
                        <div>
                            <Label className="text-xs">To</Label>
                            <Input type="date" className="h-8 text-xs" value={dateTo} onChange={e => setDateTo(e.target.value)} />
                        </div>
                    </div>
                )}

                {/* Preview strip */}
                {preview && (
                    <div className="rounded-lg bg-muted/40 p-3 text-xs space-y-1 max-h-32 overflow-y-auto">
                        {preview.total !== undefined && <p className="font-medium">{preview.total} records</p>}
                        {preview.turnover_rate_pct !== undefined && <p>Turnover rate: <strong>{preview.turnover_rate_pct}%</strong></p>}
                        {preview.expired !== undefined && <p>Expired: <strong className="text-rose-600">{preview.expired}</strong> · Expiring 30d: <strong className="text-amber-600">{preview.expiring_30d}</strong></p>}
                        {preview.summary && preview.summary.slice(0, 3).map((s, i) => (
                            <p key={i}>{s.employee}: {s.spells} spells · {s.total_days} days · BF {s.bradford_factor}</p>
                        ))}
                        {preview.records && preview.records.slice(0, 3).map((r, i) => (
                            <p key={i} className="truncate">
                                {r.employee || r.employee_name || `${r.first_name || ''} ${r.last_name || ''}`.trim()} — {r.start_date || r.expense_date || r.journey_date || r.completion_date || r.shift_date || r.clock_in_time || r.start_date || ''}
                            </p>
                        ))}
                        {preview.records?.length > 3 && <p className="text-muted-foreground">…and {preview.records.length - 3} more</p>}
                    </div>
                )}

                <div className="flex gap-2 mt-auto">
                    <Button size="sm" variant="outline" className="flex-1" onClick={handleRun} disabled={running === report.key}>
                        {running === report.key ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <BarChart3 className="w-3 h-3 mr-1" />}
                        Preview
                    </Button>
                    <Button size="sm" className="flex-1" onClick={() => onDownload(report.key, dateFrom, dateTo)} disabled={running === report.key}>
                        <Download className="w-3 h-3 mr-1" />
                        CSV
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}

export default function ReportsPage() {
    const { token } = useAuth();
    const auth = () => ({ headers: { Authorization: `Bearer ${token}` }, withCredentials: true });
    const [running, setRunning] = useState(null);
    const [search, setSearch] = useState('');

    const runReport = async (key, dateFrom, dateTo) => {
        setRunning(key);
        try {
            const params = new URLSearchParams({ fmt: 'json' });
            if (dateFrom) params.set('date_from', dateFrom);
            if (dateTo) params.set('date_to', dateTo);
            const res = await axios.get(`${API_URL}/api/reports/${key}?${params}`, auth());
            return res.data;
        } catch (e) {
            toast.error(e.response?.data?.detail || `Failed to run ${key} report`);
            return null;
        } finally {
            setRunning(null);
        }
    };

    const downloadReport = (key, dateFrom, dateTo) => {
        const token = localStorage.getItem('token');
        const params = new URLSearchParams({ fmt: 'csv' });
        if (dateFrom) params.set('date_from', dateFrom);
        if (dateTo) params.set('date_to', dateTo);
        const url = `${API_URL}/api/reports/${key}?${params}&token=${token}`;
        // Open via fetch to attach auth header
        fetch(`${API_URL}/api/reports/${key}?${params}`, {
            headers: { Authorization: `Bearer ${token}` },
        }).then(res => {
            if (!res.ok) { toast.error('Download failed'); return; }
            return res.blob();
        }).then(blob => {
            if (!blob) return;
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `${key}_${new Date().toISOString().slice(0, 10)}.csv`;
            a.click();
            URL.revokeObjectURL(a.href);
            toast.success('Report downloaded');
        }).catch(() => toast.error('Download failed'));
    };

    const filtered = REPORTS.filter(r =>
        r.label.toLowerCase().includes(search.toLowerCase()) ||
        r.desc.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2"><BarChart3 className="w-6 h-6" /> Reports</h1>
                    <p className="text-muted-foreground text-sm mt-1">{REPORTS.length} reports — preview data or download as CSV</p>
                </div>
                <Input
                    className="w-64"
                    placeholder="Search reports..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filtered.map(report => (
                    <ReportCard
                        key={report.key}
                        report={report}
                        onRun={runReport}
                        onDownload={downloadReport}
                        running={running}
                    />
                ))}
            </div>

            {filtered.length === 0 && (
                <div className="text-center py-16 text-muted-foreground">
                    <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p>No reports match "{search}"</p>
                </div>
            )}
        </div>
    );
}
