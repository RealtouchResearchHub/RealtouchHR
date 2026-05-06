import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import { toast } from 'sonner';
import {
    Calculator, Heart, Baby, FileHeart, Loader2, Save, Info,
    PoundSterling, AlertCircle, Users, BookOpen,
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function StatutoryPaymentsPage() {
    const [employees, setEmployees] = useState([]);
    const [rates, setRates] = useState(null);
    const [active, setActive] = useState([]);
    const [loading, setLoading] = useState(true);
    const [calcType, setCalcType] = useState('ssp');

    // SSP form
    const [sspForm, setSspForm] = useState({
        employee_id: '',
        sick_start_date: '',
        sick_end_date: '',
        qualifying_days_per_week: 5,
    });
    // SMP form
    const [smpForm, setSmpForm] = useState({
        employee_id: '',
        expected_week_of_childbirth: '',
        maternity_start_date: '',
        is_small_employer: false,
    });
    // SPP form
    const [sppForm, setSppForm] = useState({
        employee_id: '',
        birth_date: '',
        paternity_weeks: 2,
    });
    // ShPP form
    const [shppForm, setShppForm] = useState({
        employee_id: '',
        share_start_date: '',
        weeks: 20,
        is_small_employer: false,
    });
    // SAP form
    const [sapForm, setSapForm] = useState({
        employee_id: '',
        adoption_placement_date: '',
        adoption_start_date: '',
        is_small_employer: false,
    });

    const [calcResult, setCalcResult] = useState(null);
    const [calcLoading, setCalcLoading] = useState(false);
    const [savingRecord, setSavingRecord] = useState(false);

    const fetchData = async () => {
        try {
            const token = localStorage.getItem('token');
            const headers = { Authorization: `Bearer ${token}` };
            const [empRes, ratesRes, activeRes] = await Promise.all([
                axios.get(`${API_URL}/api/employees`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/statutory/rates`, { headers, withCredentials: true }),
                axios.get(`${API_URL}/api/statutory/active`, { headers, withCredentials: true }),
            ]);
            setEmployees(empRes.data || []);
            setRates(ratesRes.data);
            setActive(activeRes.data?.payments || []);
        } catch (err) {
            toast.error('Failed to load statutory data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchData(); }, []);

    const handleCalculate = async () => {
        setCalcLoading(true);
        setCalcResult(null);
        const token = localStorage.getItem('token');
        const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

        try {
            let url, body;
            if (calcType === 'ssp') {
                if (!sspForm.employee_id || !sspForm.sick_start_date || !sspForm.sick_end_date) {
                    toast.error('Fill all fields');
                    setCalcLoading(false);
                    return;
                }
                url = `${API_URL}/api/statutory/ssp/calculate`;
                body = sspForm;
            } else if (calcType === 'smp') {
                if (!smpForm.employee_id || !smpForm.expected_week_of_childbirth || !smpForm.maternity_start_date) {
                    toast.error('Fill all fields');
                    setCalcLoading(false);
                    return;
                }
                url = `${API_URL}/api/statutory/smp/calculate`;
                body = smpForm;
            } else if (calcType === 'shpp') {
                if (!shppForm.employee_id || !shppForm.share_start_date) {
                    toast.error('Fill all fields');
                    setCalcLoading(false);
                    return;
                }
                url = `${API_URL}/api/statutory/shpp/calculate`;
                body = shppForm;
            } else if (calcType === 'sap') {
                if (!sapForm.employee_id || !sapForm.adoption_placement_date || !sapForm.adoption_start_date) {
                    toast.error('Fill all fields');
                    setCalcLoading(false);
                    return;
                }
                url = `${API_URL}/api/statutory/sap/calculate`;
                body = sapForm;
            } else {
                if (!sppForm.employee_id || !sppForm.birth_date) {
                    toast.error('Fill all fields');
                    setCalcLoading(false);
                    return;
                }
                url = `${API_URL}/api/statutory/spp/calculate`;
                body = sppForm;
            }
            const res = await axios.post(url, body, { headers, withCredentials: true });
            setCalcResult(res.data);
            if (res.data.eligible === false) {
                toast.warning(`Not eligible: ${res.data.reason}`);
            } else {
                toast.success('Calculation complete');
            }
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Calculation failed');
        } finally {
            setCalcLoading(false);
        }
    };

    const handleSaveRecord = async () => {
        if (!calcResult || calcResult.eligible === false) return;
        setSavingRecord(true);
        const token = localStorage.getItem('token');
        try {
            let employeeId, startDate, endDate;
            if (calcType === 'ssp') {
                employeeId = sspForm.employee_id;
                startDate = sspForm.sick_start_date;
                endDate = sspForm.sick_end_date;
            } else if (calcType === 'smp') {
                employeeId = smpForm.employee_id;
                startDate = smpForm.maternity_start_date;
                endDate = null;
            } else if (calcType === 'shpp') {
                employeeId = shppForm.employee_id;
                startDate = shppForm.share_start_date;
                endDate = null;
            } else if (calcType === 'sap') {
                employeeId = sapForm.employee_id;
                startDate = sapForm.adoption_start_date;
                endDate = null;
            } else {
                employeeId = sppForm.employee_id;
                startDate = sppForm.birth_date;
                endDate = null;
            }
            await axios.post(
                `${API_URL}/api/statutory/record`,
                {
                    employee_id: employeeId,
                    payment_type: calcType,
                    start_date: startDate,
                    end_date: endDate,
                    calculation: calcResult,
                },
                { headers: { Authorization: `Bearer ${token}` }, withCredentials: true }
            );
            toast.success('Statutory payment recorded');
            setCalcResult(null);
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to save');
        } finally {
            setSavingRecord(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    return (
        <div className="space-y-6" data-testid="statutory-payments-page">
            <div>
                <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Statutory Payments</h1>
                <p className="text-muted-foreground mt-1">
                    Calculate and record SSP, SMP, and SPP for UK employees (Tax Year 2025-26).
                </p>
            </div>

            {/* Rates overview */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                    { label: 'SSP / week', value: rates?.ssp_weekly_rate, icon: Heart, color: 'text-rose-600' },
                    { label: 'SMP / week', value: rates?.smp_weekly_rate, icon: Baby, color: 'text-pink-600' },
                    { label: 'SPP / week', value: rates?.spp_weekly_rate, icon: FileHeart, color: 'text-indigo-600' },
                    { label: 'Lower Earnings Limit', value: rates?.lower_earnings_limit, icon: PoundSterling, color: 'text-amber-600' },
                ].map((r, i) => {
                    const Icon = r.icon;
                    return (
                        <Card key={i} data-testid={`rate-card-${i}`}>
                            <CardContent className="p-4">
                                <div className="flex items-center gap-2 mb-1">
                                    <Icon className={`w-4 h-4 ${r.color}`} />
                                    <p className="text-xs text-muted-foreground">{r.label}</p>
                                </div>
                                <p className="text-2xl font-bold">£{Number(r.value || 0).toFixed(2)}</p>
                            </CardContent>
                        </Card>
                    );
                })}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Calculator */}
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Calculator className="w-5 h-5 text-indigo-600" />
                            <CardTitle>Statutory Payment Calculator</CardTitle>
                        </div>
                        <CardDescription>
                            Select a payment type and enter employee details to calculate entitlement.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Tabs value={calcType} onValueChange={(v) => { setCalcType(v); setCalcResult(null); }}>
                            <TabsList className="grid grid-cols-5 w-full mb-4">
                                <TabsTrigger value="ssp" data-testid="tab-ssp">SSP</TabsTrigger>
                                <TabsTrigger value="smp" data-testid="tab-smp">SMP</TabsTrigger>
                                <TabsTrigger value="spp" data-testid="tab-spp">SPP</TabsTrigger>
                                <TabsTrigger value="shpp" data-testid="tab-shpp">ShPP</TabsTrigger>
                                <TabsTrigger value="sap" data-testid="tab-sap">SAP</TabsTrigger>
                            </TabsList>

                            <TabsContent value="ssp" className="space-y-4">
                                <EmployeeSelect
                                    value={sspForm.employee_id}
                                    onChange={(v) => setSspForm({ ...sspForm, employee_id: v })}
                                    employees={employees}
                                    testId="ssp-employee"
                                />
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <Label>Sick start date</Label>
                                        <Input
                                            type="date"
                                            value={sspForm.sick_start_date}
                                            onChange={(e) => setSspForm({ ...sspForm, sick_start_date: e.target.value })}
                                            data-testid="ssp-start"
                                        />
                                    </div>
                                    <div>
                                        <Label>Sick end date</Label>
                                        <Input
                                            type="date"
                                            value={sspForm.sick_end_date}
                                            onChange={(e) => setSspForm({ ...sspForm, sick_end_date: e.target.value })}
                                            data-testid="ssp-end"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <Label>Qualifying days per week</Label>
                                    <Input
                                        type="number"
                                        min="1"
                                        max="7"
                                        value={sspForm.qualifying_days_per_week}
                                        onChange={(e) => setSspForm({ ...sspForm, qualifying_days_per_week: parseInt(e.target.value) || 5 })}
                                        data-testid="ssp-qdays"
                                    />
                                </div>
                            </TabsContent>

                            <TabsContent value="smp" className="space-y-4">
                                <EmployeeSelect
                                    value={smpForm.employee_id}
                                    onChange={(v) => setSmpForm({ ...smpForm, employee_id: v })}
                                    employees={employees}
                                    testId="smp-employee"
                                />
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <Label>Expected week of childbirth</Label>
                                        <Input
                                            type="date"
                                            value={smpForm.expected_week_of_childbirth}
                                            onChange={(e) => setSmpForm({ ...smpForm, expected_week_of_childbirth: e.target.value })}
                                            data-testid="smp-ewc"
                                        />
                                    </div>
                                    <div>
                                        <Label>Maternity start date</Label>
                                        <Input
                                            type="date"
                                            value={smpForm.maternity_start_date}
                                            onChange={(e) => setSmpForm({ ...smpForm, maternity_start_date: e.target.value })}
                                            data-testid="smp-start"
                                        />
                                    </div>
                                </div>
                                <label className="flex items-center gap-2 text-sm">
                                    <input
                                        type="checkbox"
                                        checked={smpForm.is_small_employer}
                                        onChange={(e) => setSmpForm({ ...smpForm, is_small_employer: e.target.checked })}
                                        data-testid="smp-small-employer"
                                    />
                                    Small employer (claim 103% recovery)
                                </label>
                            </TabsContent>

                            <TabsContent value="spp" className="space-y-4">
                                <EmployeeSelect
                                    value={sppForm.employee_id}
                                    onChange={(v) => setSppForm({ ...sppForm, employee_id: v })}
                                    employees={employees}
                                    testId="spp-employee"
                                />
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <Label>Child birth date</Label>
                                        <Input
                                            type="date"
                                            value={sppForm.birth_date}
                                            onChange={(e) => setSppForm({ ...sppForm, birth_date: e.target.value })}
                                            data-testid="spp-birth"
                                        />
                                    </div>
                                    <div>
                                        <Label>Paternity weeks</Label>
                                        <Select
                                            value={String(sppForm.paternity_weeks)}
                                            onValueChange={(v) => setSppForm({ ...sppForm, paternity_weeks: parseInt(v) })}
                                        >
                                            <SelectTrigger data-testid="spp-weeks">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="1">1 week</SelectItem>
                                                <SelectItem value="2">2 weeks</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                            </TabsContent>

                            <TabsContent value="shpp" className="space-y-4">
                                <EmployeeSelect
                                    value={shppForm.employee_id}
                                    onChange={(v) => setShppForm({ ...shppForm, employee_id: v })}
                                    employees={employees}
                                    testId="shpp-employee"
                                />
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <Label>Share-leave start date</Label>
                                        <Input
                                            type="date"
                                            value={shppForm.share_start_date}
                                            onChange={(e) => setShppForm({ ...shppForm, share_start_date: e.target.value })}
                                            data-testid="shpp-start"
                                        />
                                    </div>
                                    <div>
                                        <Label>Weeks (max 37)</Label>
                                        <Input
                                            type="number" min="1" max="37"
                                            value={shppForm.weeks}
                                            onChange={(e) => setShppForm({ ...shppForm, weeks: parseInt(e.target.value) || 1 })}
                                            data-testid="shpp-weeks"
                                        />
                                    </div>
                                </div>
                                <label className="flex items-center gap-2 text-sm">
                                    <input type="checkbox" checked={shppForm.is_small_employer}
                                        onChange={(e) => setShppForm({ ...shppForm, is_small_employer: e.target.checked })}
                                        data-testid="shpp-small-employer" />
                                    Small employer (claim 103% recovery)
                                </label>
                            </TabsContent>

                            <TabsContent value="sap" className="space-y-4">
                                <EmployeeSelect
                                    value={sapForm.employee_id}
                                    onChange={(v) => setSapForm({ ...sapForm, employee_id: v })}
                                    employees={employees}
                                    testId="sap-employee"
                                />
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <Label>Adoption start</Label>
                                        <Input
                                            type="date"
                                            value={sapForm.adoption_start_date}
                                            onChange={(e) => setSapForm({ ...sapForm, adoption_start_date: e.target.value })}
                                            data-testid="sap-start"
                                        />
                                    </div>
                                    <div>
                                        <Label>Placement date</Label>
                                        <Input
                                            type="date"
                                            value={sapForm.adoption_placement_date}
                                            onChange={(e) => setSapForm({ ...sapForm, adoption_placement_date: e.target.value })}
                                            data-testid="sap-placement"
                                        />
                                    </div>
                                </div>
                                <label className="flex items-center gap-2 text-sm">
                                    <input type="checkbox" checked={sapForm.is_small_employer}
                                        onChange={(e) => setSapForm({ ...sapForm, is_small_employer: e.target.checked })}
                                        data-testid="sap-small-employer" />
                                    Small employer (claim 103% recovery)
                                </label>
                            </TabsContent>
                        </Tabs>

                        <Button
                            className="w-full mt-4 bg-indigo-600 hover:bg-indigo-700 text-white"
                            onClick={handleCalculate}
                            disabled={calcLoading}
                            data-testid="calculate-btn"
                        >
                            {calcLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Calculator className="w-4 h-4 mr-2" />}
                            Calculate
                        </Button>
                    </CardContent>
                </Card>

                {/* Result */}
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <BookOpen className="w-5 h-5 text-indigo-600" />
                            <CardTitle>Calculation Result</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent>
                        {!calcResult ? (
                            <div className="text-center py-8 text-muted-foreground">
                                <Info className="w-10 h-10 mx-auto mb-2 opacity-40" />
                                <p>Run a calculation to see results here</p>
                            </div>
                        ) : calcResult.eligible === false ? (
                            <div className="p-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 rounded-lg">
                                <div className="flex gap-2 text-amber-800 dark:text-amber-300">
                                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                                    <div>
                                        <p className="font-semibold">Not eligible</p>
                                        <p className="text-sm mt-1">{calcResult.reason}</p>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-3" data-testid="calc-result">
                                <div className="p-4 bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30 rounded-lg">
                                    <p className="text-sm text-muted-foreground">Total amount</p>
                                    <p className="text-3xl font-bold text-indigo-900 dark:text-indigo-100 mt-1">
                                        £{Number(
                                            calcResult.total_ssp_amount ??
                                            calcResult.total_smp ??
                                            calcResult.total_spp ??
                                            calcResult.total_shpp ??
                                            calcResult.total_sap ?? 0
                                        ).toFixed(2)}
                                    </p>
                                </div>
                                <div className="text-sm space-y-1">
                                    {calcResult.average_weekly_earnings !== undefined && (
                                        <ResultRow label="Average weekly earnings" value={`£${calcResult.average_weekly_earnings}`} />
                                    )}
                                    {calcResult.weeks_of_ssp !== undefined && (
                                        <ResultRow label="Weeks of SSP" value={calcResult.weeks_of_ssp} />
                                    )}
                                    {calcResult.qualifying_days !== undefined && (
                                        <ResultRow label="Qualifying days" value={calcResult.qualifying_days} />
                                    )}
                                    {calcResult.first_6_weeks && (
                                        <>
                                            <ResultRow label="First 6 weeks (90% AWE)" value={`£${calcResult.first_6_weeks.total}`} />
                                            <ResultRow label="Remaining 33 weeks" value={`£${calcResult.remaining_33_weeks.total}`} />
                                            <ResultRow label="Recoverable" value={`£${calcResult.recoverable_amount}`} />
                                        </>
                                    )}
                                    {calcResult.weeks !== undefined && (
                                        <ResultRow label="Weeks" value={calcResult.weeks} />
                                    )}
                                </div>
                                <Button
                                    variant="outline"
                                    className="w-full"
                                    onClick={handleSaveRecord}
                                    disabled={savingRecord}
                                    data-testid="save-record-btn"
                                >
                                    {savingRecord ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                                    Save as Record
                                </Button>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Active payments */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Users className="w-5 h-5 text-indigo-600" />
                        <CardTitle>Active Statutory Payments</CardTitle>
                    </div>
                    <CardDescription>Currently running SSP/SMP/SPP records</CardDescription>
                </CardHeader>
                <CardContent>
                    {!active.length ? (
                        <p className="text-center py-8 text-muted-foreground">No active statutory payments</p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead className="text-xs text-muted-foreground uppercase tracking-wide">
                                    <tr className="border-b">
                                        <th className="text-left p-3">Employee</th>
                                        <th className="text-left p-3">Type</th>
                                        <th className="text-left p-3">Start</th>
                                        <th className="text-right p-3">AWE</th>
                                        <th className="text-right p-3">Recoverable</th>
                                        <th className="text-center p-3">Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {active.map((p) => (
                                        <tr key={p.payment_id} className="border-b hover:bg-accent/50" data-testid={`stat-row-${p.payment_id}`}>
                                            <td className="p-3 font-medium">{p.employee_name || p.employee_id}</td>
                                            <td className="p-3 uppercase">{p.payment_type}</td>
                                            <td className="p-3">{p.start_date}</td>
                                            <td className="p-3 text-right">£{Number(p.average_weekly_earnings || 0).toFixed(2)}</td>
                                            <td className="p-3 text-right">£{Number(p.amount_recoverable || 0).toFixed(2)}</td>
                                            <td className="p-3 text-center">
                                                <Badge variant="outline" className="bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-950/30">
                                                    {(p.status || '').toUpperCase()}
                                                </Badge>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

function EmployeeSelect({ value, onChange, employees, testId }) {
    return (
        <div>
            <Label>Employee</Label>
            <Select value={value} onValueChange={onChange}>
                <SelectTrigger data-testid={testId}>
                    <SelectValue placeholder="Select employee" />
                </SelectTrigger>
                <SelectContent>
                    {employees.map((e) => (
                        <SelectItem key={e.employee_id} value={e.employee_id}>
                            {e.first_name} {e.last_name} — {e.job_title || 'Employee'}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </div>
    );
}

function ResultRow({ label, value }) {
    return (
        <div className="flex justify-between border-b pb-1">
            <span className="text-muted-foreground">{label}</span>
            <span className="font-medium">{value}</span>
        </div>
    );
}
