import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import { Loader2, UserMinus, FileDown, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function OffboardingDialog({ open, onOpenChange, employee, onComplete }) {
    const [reasons, setReasons] = useState([]);
    const [step, setStep] = useState(1);
    const [submitting, setSubmitting] = useState(false);
    const [result, setResult] = useState(null);
    const [form, setForm] = useState({
        leaving_date: '',
        reason: '',
        notes: '',
        redundancy_payment: 0,
        holiday_payout_days: 0,
    });

    useEffect(() => {
        if (!open) return;
        setStep(1);
        setResult(null);
        setForm({
            leaving_date: new Date().toISOString().split('T')[0],
            reason: '',
            notes: '',
            redundancy_payment: 0,
            holiday_payout_days: 0,
        });
        (async () => {
            try {
                const token = localStorage.getItem('token');
                const res = await axios.get(`${API_URL}/api/offboarding/reasons`, {
                    headers: { Authorization: `Bearer ${token}` },
                    withCredentials: true,
                });
                setReasons(res.data?.reasons || []);
            } catch (err) {
                toast.error('Failed to load reasons');
            }
        })();
    }, [open]);

    const handleSubmit = async () => {
        if (!form.leaving_date || !form.reason) {
            toast.error('Leaving date and reason are required');
            return;
        }
        setSubmitting(true);
        try {
            const token = localStorage.getItem('token');
            const res = await axios.post(
                `${API_URL}/api/offboarding/terminate`,
                {
                    employee_id: employee.employee_id,
                    leaving_date: form.leaving_date,
                    reason: form.reason,
                    notes: form.notes,
                    redundancy_payment: Number(form.redundancy_payment) || 0,
                    holiday_payout_days: Number(form.holiday_payout_days) || 0,
                },
                { headers: { Authorization: `Bearer ${token}` }, withCredentials: true }
            );
            setResult(res.data);
            setStep(3);
            toast.success('Employee offboarded successfully');
            if (onComplete) onComplete(res.data);
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Termination failed');
        } finally {
            setSubmitting(false);
        }
    };

    const downloadP45 = async () => {
        try {
            const token = localStorage.getItem('token');
            const res = await axios.get(
                `${API_URL}/api/tax-docs/p45/${employee.employee_id}`,
                {
                    headers: { Authorization: `Bearer ${token}` },
                    withCredentials: true,
                    responseType: 'blob',
                }
            );
            const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
            const a = document.createElement('a');
            a.href = url;
            a.download = `P45_${employee.first_name}_${employee.last_name}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            toast.error('Failed to download P45');
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg" data-testid="offboarding-dialog">
                <DialogHeader>
                    <div className="flex items-center gap-2">
                        <div className="w-10 h-10 rounded-lg bg-rose-100 dark:bg-rose-950/30 flex items-center justify-center">
                            <UserMinus className="w-5 h-5 text-rose-600" />
                        </div>
                        <div>
                            <DialogTitle>Offboard Employee</DialogTitle>
                            <DialogDescription>
                                {employee?.first_name} {employee?.last_name}
                            </DialogDescription>
                        </div>
                    </div>
                </DialogHeader>

                {step === 1 && (
                    <div className="space-y-4">
                        <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 flex gap-2 text-amber-800 dark:text-amber-300 text-sm">
                            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                            <div>
                                <p className="font-semibold">This will:</p>
                                <ul className="mt-1 list-disc pl-4 space-y-0.5 text-xs">
                                    <li>Mark employee as leaver in payroll and HR</li>
                                    <li>Generate a P45 document</li>
                                    <li>Queue them as leaver on the next FPS</li>
                                    <li>Trigger UKVI report if sponsored</li>
                                    <li>Cease pension contributions</li>
                                </ul>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label>Leaving date</Label>
                                <Input
                                    type="date"
                                    value={form.leaving_date}
                                    onChange={(e) => setForm({ ...form, leaving_date: e.target.value })}
                                    data-testid="offboard-leaving-date"
                                />
                            </div>
                            <div>
                                <Label>Reason</Label>
                                <Select value={form.reason} onValueChange={(v) => setForm({ ...form, reason: v })}>
                                    <SelectTrigger data-testid="offboard-reason">
                                        <SelectValue placeholder="Select reason" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {reasons.map((r) => (
                                            <SelectItem key={r.id} value={r.id}>{r.label}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label>Redundancy (£, optional)</Label>
                                <Input
                                    type="number"
                                    min="0"
                                    step="0.01"
                                    value={form.redundancy_payment}
                                    onChange={(e) => setForm({ ...form, redundancy_payment: e.target.value })}
                                    data-testid="offboard-redundancy"
                                />
                            </div>
                            <div>
                                <Label>Holiday payout (days)</Label>
                                <Input
                                    type="number"
                                    min="0"
                                    step="0.5"
                                    value={form.holiday_payout_days}
                                    onChange={(e) => setForm({ ...form, holiday_payout_days: e.target.value })}
                                    data-testid="offboard-holiday"
                                />
                            </div>
                        </div>

                        <div>
                            <Label>Notes</Label>
                            <Textarea
                                rows={3}
                                placeholder="Optional notes..."
                                value={form.notes}
                                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                                data-testid="offboard-notes"
                            />
                        </div>
                    </div>
                )}

                {step === 2 && (
                    <div className="space-y-4">
                        <p className="text-sm">Please confirm you want to offboard this employee:</p>
                        <dl className="divide-y rounded-lg border">
                            <Row label="Name" value={`${employee?.first_name} ${employee?.last_name}`} />
                            <Row label="Leaving date" value={form.leaving_date} />
                            <Row label="Reason" value={reasons.find((r) => r.id === form.reason)?.label} />
                            <Row label="Redundancy" value={`£${Number(form.redundancy_payment || 0).toFixed(2)}`} />
                            <Row label="Holiday payout (days)" value={form.holiday_payout_days || 0} />
                        </dl>
                    </div>
                )}

                {step === 3 && result && (
                    <div className="space-y-4">
                        <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200">
                            <p className="font-semibold text-emerald-900 dark:text-emerald-100">
                                Offboarding complete
                            </p>
                            <p className="text-sm text-emerald-800 dark:text-emerald-200 mt-1">
                                Leaver queued for next FPS · Pension {result.pension_closed ? 'closed' : 'not active'}
                                {result.ukvi_report_id ? ' · UKVI report queued' : ''}
                            </p>
                        </div>
                        <Button
                            variant="outline"
                            className="w-full"
                            onClick={downloadP45}
                            data-testid="download-p45-btn"
                        >
                            <FileDown className="w-4 h-4 mr-2" /> Download P45 PDF
                        </Button>
                    </div>
                )}

                <DialogFooter>
                    {step === 1 && (
                        <>
                            <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
                            <Button
                                onClick={() => setStep(2)}
                                disabled={!form.leaving_date || !form.reason}
                                data-testid="offboard-next-btn"
                            >
                                Review
                            </Button>
                        </>
                    )}
                    {step === 2 && (
                        <>
                            <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
                            <Button
                                className="bg-rose-600 hover:bg-rose-700 text-white"
                                onClick={handleSubmit}
                                disabled={submitting}
                                data-testid="offboard-confirm-btn"
                            >
                                {submitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <UserMinus className="w-4 h-4 mr-2" />}
                                Confirm Offboarding
                            </Button>
                        </>
                    )}
                    {step === 3 && (
                        <Button onClick={() => onOpenChange(false)} data-testid="offboard-done-btn">
                            Close
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function Row({ label, value }) {
    return (
        <div className="flex justify-between px-3 py-2 text-sm">
            <span className="text-muted-foreground">{label}</span>
            <span className="font-medium">{value}</span>
        </div>
    );
}
