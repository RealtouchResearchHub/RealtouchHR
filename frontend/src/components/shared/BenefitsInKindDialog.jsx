import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import { toast } from 'sonner';
import { Plus, Trash2, FileDown, Loader2 } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const BENEFIT_CATEGORIES = [
    { id: "company_car", label: "Company car" },
    { id: "fuel", label: "Fuel benefit" },
    { id: "private_medical", label: "Private medical insurance" },
    { id: "loan", label: "Beneficial loan" },
    { id: "accommodation", label: "Living accommodation" },
    { id: "vouchers", label: "Vouchers / non-cash" },
    { id: "expenses", label: "Expense payments" },
    { id: "other", label: "Other" },
];

export default function BenefitsInKindDialog({ open, onOpenChange, employee }) {
    const [taxYear, setTaxYear] = useState("2024-25");
    const [benefits, setBenefits] = useState([]);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [downloading, setDownloading] = useState(false);

    const fetchExisting = async () => {
        if (!employee?.employee_id || !open) return;
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            const res = await axios.get(`${API_URL}/api/tax-docs/p11d/${employee.employee_id}`, {
                headers: { Authorization: `Bearer ${token}` }, withCredentials: true,
            });
            const found = (res.data.records || []).find(r => r.tax_year === taxYear);
            setBenefits(found?.benefits || []);
        } catch (err) {
            setBenefits([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchExisting(); }, [open, taxYear]); // eslint-disable-line

    const addBenefit = () => setBenefits([...benefits, { category: "other", description: "", cash_equivalent: 0 }]);
    const removeBenefit = (idx) => setBenefits(benefits.filter((_, i) => i !== idx));
    const updateBenefit = (idx, field, value) => {
        const next = [...benefits];
        next[idx] = { ...next[idx], [field]: field === "cash_equivalent" ? parseFloat(value) || 0 : value };
        setBenefits(next);
    };

    const totalCash = benefits.reduce((sum, b) => sum + (Number(b.cash_equivalent) || 0), 0);
    const class1aNi = totalCash * 0.138;

    const handleSave = async () => {
        setSaving(true);
        try {
            const token = localStorage.getItem('token');
            await axios.post(`${API_URL}/api/tax-docs/p11d`, {
                employee_id: employee.employee_id,
                tax_year: taxYear,
                benefits,
            }, {
                headers: { Authorization: `Bearer ${token}` }, withCredentials: true,
            });
            toast.success("P11D record saved");
        } catch (err) {
            toast.error(err.response?.data?.detail || "Save failed");
        } finally {
            setSaving(false);
        }
    };

    const handleDownload = async () => {
        setDownloading(true);
        try {
            const token = localStorage.getItem('token');
            const res = await axios.get(`${API_URL}/api/tax-docs/p11d/${employee.employee_id}/${taxYear}`, {
                headers: { Authorization: `Bearer ${token}` }, withCredentials: true,
                responseType: 'blob',
            });
            const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
            const a = document.createElement('a');
            a.href = url;
            a.download = `P11D_${employee.first_name}_${employee.last_name}_${taxYear}.pdf`;
            a.click();
            window.URL.revokeObjectURL(url);
            toast.success("P11D downloaded");
        } catch (err) {
            toast.error(err.response?.data?.detail || "Download failed — save the record first");
        } finally {
            setDownloading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl" data-testid="bik-dialog">
                <DialogHeader>
                    <DialogTitle>Benefits in Kind (P11D)</DialogTitle>
                    <DialogDescription>
                        {employee?.first_name} {employee?.last_name} — record taxable benefits and generate P11D.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <Label>Tax year</Label>
                            <Select value={taxYear} onValueChange={setTaxYear}>
                                <SelectTrigger data-testid="bik-tax-year">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {["2024-25", "2025-26", "2023-24", "2022-23"].map(y => (
                                        <SelectItem key={y} value={y}>{y}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="flex items-end">
                            <Button variant="outline" onClick={addBenefit} data-testid="add-benefit-btn">
                                <Plus className="w-4 h-4 mr-2" /> Add benefit
                            </Button>
                        </div>
                    </div>

                    {loading ? (
                        <div className="text-center py-6"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
                    ) : benefits.length === 0 ? (
                        <p className="text-center text-sm text-muted-foreground py-6">
                            No benefits recorded for {taxYear}. Click "Add benefit" to start.
                        </p>
                    ) : (
                        <div className="space-y-2 max-h-72 overflow-y-auto">
                            {benefits.map((b, idx) => (
                                <div key={idx} className="grid grid-cols-12 gap-2 items-end" data-testid={`benefit-row-${idx}`}>
                                    <div className="col-span-3">
                                        <Label className="text-xs">Category</Label>
                                        <Select value={b.category} onValueChange={(v) => updateBenefit(idx, "category", v)}>
                                            <SelectTrigger><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                {BENEFIT_CATEGORIES.map(c => (
                                                    <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="col-span-5">
                                        <Label className="text-xs">Description</Label>
                                        <Input value={b.description} placeholder="e.g. BMW 3-series, full year"
                                            onChange={(e) => updateBenefit(idx, "description", e.target.value)} />
                                    </div>
                                    <div className="col-span-3">
                                        <Label className="text-xs">Cash equivalent (£)</Label>
                                        <Input type="number" step="0.01" min="0" value={b.cash_equivalent}
                                            onChange={(e) => updateBenefit(idx, "cash_equivalent", e.target.value)} />
                                    </div>
                                    <Button variant="ghost" size="icon" className="col-span-1 text-rose-600"
                                        onClick={() => removeBenefit(idx)}>
                                        <Trash2 className="w-4 h-4" />
                                    </Button>
                                </div>
                            ))}
                        </div>
                    )}

                    {benefits.length > 0 && (
                        <div className="grid grid-cols-2 gap-3 p-3 bg-indigo-50 dark:bg-indigo-950/30 rounded-lg">
                            <div>
                                <p className="text-xs text-muted-foreground">Total cash equivalent</p>
                                <p className="text-2xl font-bold">£{totalCash.toFixed(2)}</p>
                            </div>
                            <div>
                                <p className="text-xs text-muted-foreground">Class 1A NIC due (13.8%)</p>
                                <p className="text-2xl font-bold">£{class1aNi.toFixed(2)}</p>
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
                    <Button variant="outline" onClick={handleDownload} disabled={downloading}
                        data-testid="download-p11d-btn">
                        {downloading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileDown className="w-4 h-4 mr-2" />}
                        Download P11D
                    </Button>
                    <Button onClick={handleSave} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700 text-white"
                        data-testid="save-p11d-btn">
                        {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                        Save record
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
