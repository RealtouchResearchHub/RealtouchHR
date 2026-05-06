import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import { toast } from 'sonner';
import {
    CalendarCheck, FileCheck2, ShieldCheck, Loader2, AlertCircle, CheckCircle2,
    PoundSterling, FileText, Send,
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const TAX_YEARS = ["2024-25", "2023-24", "2025-26"];

export default function YearEndPage() {
    const [taxYear, setTaxYear] = useState("2024-25");
    const [preview, setPreview] = useState(null);
    const [loading, setLoading] = useState(false);
    const [closing, setClosing] = useState(false);
    const [closeResult, setCloseResult] = useState(null);

    const fetchPreview = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            const res = await axios.get(`${API_URL}/api/year-end/preview?tax_year=${taxYear}`, {
                headers: { Authorization: `Bearer ${token}` }, withCredentials: true,
            });
            setPreview(res.data);
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to load preview');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchPreview(); }, [taxYear]); // eslint-disable-line

    const handleClose = async () => {
        if (!window.confirm(`Close tax year ${taxYear}? This will queue P60s and create the EPS submission.`)) return;
        setClosing(true);
        try {
            const token = localStorage.getItem('token');
            const res = await axios.post(`${API_URL}/api/year-end/close?tax_year=${taxYear}`, {}, {
                headers: { Authorization: `Bearer ${token}` }, withCredentials: true,
            });
            setCloseResult(res.data);
            toast.success(`Year ${taxYear} closed — ${res.data.p60_queued} P60s queued`);
            fetchPreview();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Year-end close failed');
        } finally {
            setClosing(false);
        }
    };

    return (
        <div className="space-y-6" data-testid="year-end-page">
            <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Year-End Close</h1>
                    <p className="text-muted-foreground mt-1">
                        Finalize FPS, generate P60s and queue the EPS submission for HMRC.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Select value={taxYear} onValueChange={setTaxYear}>
                        <SelectTrigger className="w-40" data-testid="tax-year-select">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {TAX_YEARS.map(y => <SelectItem key={y} value={y}>{y}</SelectItem>)}
                        </SelectContent>
                    </Select>
                    <Button onClick={fetchPreview} variant="outline" disabled={loading}>
                        Refresh
                    </Button>
                </div>
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                </div>
            ) : preview ? (
                <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <Card data-testid="ye-employees">
                            <CardContent className="p-5">
                                <FileCheck2 className="w-5 h-5 text-indigo-600 mb-2" />
                                <p className="text-xs text-muted-foreground">P60-eligible employees</p>
                                <p className="text-3xl font-bold">{preview.p60_eligible_employees}</p>
                            </CardContent>
                        </Card>
                        <Card data-testid="ye-payslips">
                            <CardContent className="p-5">
                                <FileText className="w-5 h-5 text-emerald-600 mb-2" />
                                <p className="text-xs text-muted-foreground">Payslips in year</p>
                                <p className="text-3xl font-bold">{preview.payslip_count}</p>
                            </CardContent>
                        </Card>
                        <Card data-testid="ye-pay">
                            <CardContent className="p-5">
                                <PoundSterling className="w-5 h-5 text-amber-600 mb-2" />
                                <p className="text-xs text-muted-foreground">Total pay</p>
                                <p className="text-3xl font-bold">£{Number(preview.total_pay).toLocaleString()}</p>
                            </CardContent>
                        </Card>
                        <Card data-testid="ye-tax">
                            <CardContent className="p-5">
                                <ShieldCheck className="w-5 h-5 text-rose-600 mb-2" />
                                <p className="text-xs text-muted-foreground">Total PAYE tax</p>
                                <p className="text-3xl font-bold">£{Number(preview.total_tax).toLocaleString()}</p>
                            </CardContent>
                        </Card>
                    </div>

                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <CalendarCheck className="w-5 h-5 text-indigo-600" />
                                    <CardTitle>Tax year {taxYear}</CardTitle>
                                </div>
                                <Badge variant="outline" className={preview.ready_for_year_end
                                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                    : 'bg-amber-50 text-amber-700 border-amber-200'}>
                                    {preview.ready_for_year_end ? 'READY' : 'IN PROGRESS'}
                                </Badge>
                            </div>
                            <CardDescription>
                                {preview.tax_year_start} → {preview.tax_year_end}
                                {preview.last_pay_date_in_year && ` · Last pay date: ${preview.last_pay_date_in_year}`}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <h4 className="text-sm font-semibold mb-3">EPS Recovery Preview</h4>
                            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
                                {[
                                    ['SMP', preview.eps_recovery?.smp_recovered],
                                    ['SPP', preview.eps_recovery?.spp_recovered],
                                    ['SAP', preview.eps_recovery?.sap_recovered],
                                    ['ShPP', preview.eps_recovery?.shpp_recovered],
                                    ['Total', preview.eps_recovery?.total_recovery],
                                ].map(([label, val]) => (
                                    <div key={label} className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/30 border">
                                        <p className="text-xs text-muted-foreground">{label}</p>
                                        <p className="text-lg font-bold">£{Number(val || 0).toFixed(2)}</p>
                                    </div>
                                ))}
                            </div>

                            <div className="mt-6 flex justify-end">
                                <Button
                                    onClick={handleClose}
                                    disabled={closing}
                                    className="bg-indigo-600 hover:bg-indigo-700 text-white"
                                    data-testid="close-year-end-btn"
                                >
                                    {closing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
                                    Close Tax Year & Queue P60s
                                </Button>
                            </div>
                        </CardContent>
                    </Card>

                    {closeResult && (
                        <Card className="border-emerald-200 bg-emerald-50 dark:bg-emerald-950/30">
                            <CardContent className="p-5">
                                <div className="flex items-start gap-3">
                                    <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0" />
                                    <div>
                                        <p className="font-semibold text-emerald-900 dark:text-emerald-100">
                                            Year-end {closeResult.tax_year} closed
                                        </p>
                                        <p className="text-sm text-emerald-800 dark:text-emerald-200 mt-1">
                                            {closeResult.p60_queued} P60s queued · EPS submission {closeResult.eps_id} created
                                            {closeResult.final_fps_marked && ' · last FPS marked as final'}
                                        </p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </>
            ) : (
                <p className="text-center text-muted-foreground py-10">
                    <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    No preview data
                </p>
            )}
        </div>
    );
}
