import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Label } from '../ui/label';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem,
    DropdownMenuSeparator, DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '../ui/dialog';
import {
    Plus, Search, Users, AlertTriangle, ArrowRight, Mail, Briefcase,
    Filter, CheckCircle2, XCircle, MoreVertical, Download,
    RefreshCw, Eye, Archive, ArrowUpDown, ChevronLeft, ChevronRight as ChevronRightIcon,
    UserCheck, Save, LayoutList, LayoutGrid
} from 'lucide-react';
import { cn, getStatusColor, getComplianceColor } from '../../lib/utils';
import { toast } from 'sonner';
import { requestOrDefault } from '../../lib/loaders';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const STATUS_OPTIONS = [
    { value: 'all', label: 'All statuses' },
    { value: 'active', label: 'Active' },
    { value: 'onboarding', label: 'Onboarding' },
    { value: 'draft', label: 'Draft' },
    { value: 'on_leave', label: 'On Leave' },
    { value: 'suspended', label: 'Suspended' },
    { value: 'notice_period', label: 'Notice Period' },
    { value: 'leaver', label: 'Leaver' },
    { value: 'archived', label: 'Archived' },
];

const READINESS_OPTIONS = [
    { value: 'all', label: 'All readiness' },
    { value: 'payroll_ready', label: 'Payroll Ready' },
    { value: 'rti_ready', label: 'RTI Ready' },
    { value: 'rtw_ready', label: 'RTW Ready' },
    { value: 'not_payroll_ready', label: 'Not Payroll Ready' },
    { value: 'not_rti_ready', label: 'Not RTI Ready' },
];

const SORT_OPTIONS = [
    { value: 'name_asc', label: 'Name A–Z' },
    { value: 'name_desc', label: 'Name Z–A' },
    { value: 'start_date_desc', label: 'Newest first' },
    { value: 'start_date_asc', label: 'Oldest first' },
    { value: 'department', label: 'Department' },
    { value: 'status', label: 'Status' },
];

const WIZARD_STEPS = [
    { id: 'personal', label: 'Personal' },
    { id: 'contact', label: 'Contact' },
    { id: 'employment', label: 'Employment' },
    { id: 'payroll', label: 'Payroll & Tax' },
    { id: 'bank', label: 'Bank' },
    { id: 'rtw', label: 'Right to Work' },
    { id: 'emergency', label: 'Emergency Contact' },
    { id: 'review', label: 'Review & Save' },
];

const EMPTY_FORM = {
    // Personal
    title: '', first_name: '', middle_name: '', last_name: '', preferred_name: '',
    date_of_birth: '', gender: '', ni_number: '', nationality: '',
    // Contact
    email: '', work_email: '', mobile_phone: '', alternative_phone: '',
    address_line1: '', address_line2: '', town: '', county: '', postcode: '', country: 'United Kingdom',
    // Employment
    job_title: '', department: '', work_location: '', line_manager_id: '',
    employment_type: '', contract_type: '', start_date: '', probation_period: '',
    probation_end_date: '', working_pattern: '', weekly_hours: '', notice_period: '',
    // Payroll
    payroll_status: 'pending', pay_frequency: '', salary_type: 'annual',
    salary: '', tax_code: '', ni_category: 'A', student_loan_plan: '',
    postgraduate_loan: false, pension_status: '', auto_enrolment_status: '',
    payroll_start_date: '', starter_declaration: '',
    // Bank
    bank_name: '', account_holder_name: '', bank_sort_code: '', bank_account: '',
    building_society_roll: '', payment_reference: '', payment_method: 'bacs',
    // RTW
    right_to_work_status: '', rtw_check_date: '', rtw_document_type: '',
    rtw_expiry_date: '', rtw_followup_date: '',
    is_sponsored_worker: false, cos_number: '', soc_code: '',
    visa_type: '', visa_expiry_date: '', cos_salary: '',
    // Emergency
    emergency_name: '', emergency_relationship: '', emergency_phone: '',
    emergency_email: '',
    // Status
    status: 'draft',
};

function WizardStepIndicator({ current, total, steps }) {
    return (
        <div className="flex items-center gap-1 mb-6 overflow-x-auto pb-1">
            {steps.map((step, i) => (
                <React.Fragment key={step.id}>
                    <div className={cn(
                        'flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium whitespace-nowrap',
                        i === current ? 'bg-indigo-600 text-white' :
                        i < current ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300' :
                        'bg-muted text-muted-foreground'
                    )}>
                        {i < current ? <CheckCircle2 className="w-3 h-3" /> : <span className="w-3.5 h-3.5 flex items-center justify-center">{i + 1}</span>}
                        {step.label}
                    </div>
                    {i < steps.length - 1 && <div className="w-4 h-px bg-border flex-shrink-0" />}
                </React.Fragment>
            ))}
        </div>
    );
}

function StepPersonal({ form, set }) {
    return (
        <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
                <Label>Title</Label>
                <Select value={form.title} onValueChange={v => set({ ...form, title: v })}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                        {['Mr', 'Mrs', 'Miss', 'Ms', 'Dr', 'Prof', 'Mx'].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label>First Name <span className="text-rose-500">*</span></Label>
                <Input value={form.first_name} onChange={e => set({ ...form, first_name: e.target.value })} required data-testid="input-first-name" />
            </div>
            <div className="space-y-1.5">
                <Label>Middle Name</Label>
                <Input value={form.middle_name} onChange={e => set({ ...form, middle_name: e.target.value })} />
            </div>
            <div className="space-y-1.5">
                <Label>Last Name <span className="text-rose-500">*</span></Label>
                <Input value={form.last_name} onChange={e => set({ ...form, last_name: e.target.value })} required data-testid="input-last-name" />
            </div>
            <div className="space-y-1.5">
                <Label>Preferred Name</Label>
                <Input value={form.preferred_name} onChange={e => set({ ...form, preferred_name: e.target.value })} />
            </div>
            <div className="space-y-1.5">
                <Label>Date of Birth</Label>
                <Input type="date" value={form.date_of_birth} onChange={e => set({ ...form, date_of_birth: e.target.value })} />
            </div>
            <div className="space-y-1.5">
                <Label>Gender</Label>
                <Select value={form.gender} onValueChange={v => set({ ...form, gender: v })}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                        {['Male', 'Female', 'Non-binary', 'Prefer not to say', 'Other'].map(g => <SelectItem key={g} value={g}>{g}</SelectItem>)}
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label>NI Number</Label>
                <Input value={form.ni_number} onChange={e => set({ ...form, ni_number: e.target.value })} placeholder="AB123456C" data-testid="input-ni-number" />
            </div>
            <div className="space-y-1.5 col-span-2">
                <Label>Nationality</Label>
                <Input value={form.nationality} onChange={e => set({ ...form, nationality: e.target.value })} placeholder="e.g. British" />
            </div>
        </div>
    );
}

function StepContact({ form, set }) {
    return (
        <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
                <Label>Personal Email <span className="text-rose-500">*</span></Label>
                <Input type="email" value={form.email} onChange={e => set({ ...form, email: e.target.value })} required data-testid="input-email" />
            </div>
            <div className="space-y-1.5">
                <Label>Work Email</Label>
                <Input type="email" value={form.work_email} onChange={e => set({ ...form, work_email: e.target.value })} />
            </div>
            <div className="space-y-1.5">
                <Label>Mobile Number</Label>
                <Input value={form.mobile_phone} onChange={e => set({ ...form, mobile_phone: e.target.value })} placeholder="+44 7700 000000" />
            </div>
            <div className="space-y-1.5">
                <Label>Alternative Phone</Label>
                <Input value={form.alternative_phone} onChange={e => set({ ...form, alternative_phone: e.target.value })} />
            </div>
            <div className="space-y-1.5 col-span-2">
                <Label>Address Line 1</Label>
                <Input value={form.address_line1} onChange={e => set({ ...form, address_line1: e.target.value })} />
            </div>
            <div className="space-y-1.5 col-span-2">
                <Label>Address Line 2</Label>
                <Input value={form.address_line2} onChange={e => set({ ...form, address_line2: e.target.value })} />
            </div>
            <div className="space-y-1.5">
                <Label>Town / City</Label>
                <Input value={form.town} onChange={e => set({ ...form, town: e.target.value })} />
            </div>
            <div className="space-y-1.5">
                <Label>County</Label>
                <Input value={form.county} onChange={e => set({ ...form, county: e.target.value })} />
            </div>
            <div className="space-y-1.5">
                <Label>Postcode</Label>
                <Input value={form.postcode} onChange={e => set({ ...form, postcode: e.target.value })} placeholder="e.g. SW1A 1AA" />
            </div>
            <div className="space-y-1.5">
                <Label>Country</Label>
                <Input value={form.country} onChange={e => set({ ...form, country: e.target.value })} />
            </div>
        </div>
    );
}

function StepEmployment({ form, set }) {
    return (
        <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
                <Label>Job Title</Label>
                <Input value={form.job_title} onChange={e => set({ ...form, job_title: e.target.value })} data-testid="input-job-title" />
            </div>
            <div className="space-y-1.5">
                <Label>Department</Label>
                <Input value={form.department} onChange={e => set({ ...form, department: e.target.value })} data-testid="input-department" />
            </div>
            <div className="space-y-1.5">
                <Label>Work Location</Label>
                <Input value={form.work_location} onChange={e => set({ ...form, work_location: e.target.value })} />
            </div>
            <div className="space-y-1.5">
                <Label>Employment Type</Label>
                <Select value={form.employment_type} onValueChange={v => set({ ...form, employment_type: v })}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                        {['Full-time', 'Part-time', 'Casual', 'Zero hours', 'Agency'].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label>Contract Type</Label>
                <Select value={form.contract_type} onValueChange={v => set({ ...form, contract_type: v })}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                        {['Permanent', 'Fixed-term', 'Temporary', 'Apprenticeship', 'Internship'].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label>Start Date</Label>
                <Input type="date" value={form.start_date} onChange={e => set({ ...form, start_date: e.target.value })} />
            </div>
            <div className="space-y-1.5">
                <Label>Probation Period</Label>
                <Select value={form.probation_period} onValueChange={v => set({ ...form, probation_period: v })}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                        {['1 month', '2 months', '3 months', '6 months', 'None'].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label>Probation End Date</Label>
                <Input type="date" value={form.probation_end_date} onChange={e => set({ ...form, probation_end_date: e.target.value })} />
            </div>
            <div className="space-y-1.5">
                <Label>Working Pattern</Label>
                <Input value={form.working_pattern} onChange={e => set({ ...form, working_pattern: e.target.value })} placeholder="e.g. Mon-Fri 09:00-17:30" />
            </div>
            <div className="space-y-1.5">
                <Label>Weekly Contracted Hours</Label>
                <Input type="number" value={form.weekly_hours} onChange={e => set({ ...form, weekly_hours: e.target.value })} placeholder="e.g. 37.5" />
            </div>
            <div className="space-y-1.5 col-span-2">
                <Label>Notice Period</Label>
                <Select value={form.notice_period} onValueChange={v => set({ ...form, notice_period: v })}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                        {['1 week', '2 weeks', '1 month', '2 months', '3 months', '6 months'].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                    </SelectContent>
                </Select>
            </div>
        </div>
    );
}

function StepPayroll({ form, set }) {
    return (
        <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
                <Label>Payroll Status</Label>
                <Select value={form.payroll_status} onValueChange={v => set({ ...form, payroll_status: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                        {['pending', 'active', 'on_hold', 'excluded'].map(s => <SelectItem key={s} value={s}>{s.replace('_', ' ')}</SelectItem>)}
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label>Pay Frequency</Label>
                <Select value={form.pay_frequency} onValueChange={v => set({ ...form, pay_frequency: v })}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                        {['weekly', 'fortnightly', 'four_weekly', 'monthly'].map(s => <SelectItem key={s} value={s}>{s.replace('_', ' ')}</SelectItem>)}
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label>Salary Type</Label>
                <Select value={form.salary_type} onValueChange={v => set({ ...form, salary_type: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="annual">Annual Salary</SelectItem>
                        <SelectItem value="hourly">Hourly Rate</SelectItem>
                        <SelectItem value="daily">Daily Rate</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label>Salary / Rate (£)</Label>
                <Input type="number" value={form.salary} onChange={e => set({ ...form, salary: e.target.value })} placeholder="e.g. 35000" data-testid="input-salary" />
            </div>
            <div className="space-y-1.5">
                <Label>Tax Code</Label>
                <Input value={form.tax_code} onChange={e => set({ ...form, tax_code: e.target.value })} placeholder="e.g. 1257L" data-testid="input-tax-code" />
            </div>
            <div className="space-y-1.5">
                <Label>NI Category</Label>
                <Select value={form.ni_category} onValueChange={v => set({ ...form, ni_category: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                        {['A', 'B', 'C', 'H', 'J', 'M', 'X', 'Z'].map(c => <SelectItem key={c} value={c}>Category {c}</SelectItem>)}
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label>Student Loan Plan</Label>
                <Select value={form.student_loan_plan || 'none'} onValueChange={v => set({ ...form, student_loan_plan: v === 'none' ? '' : v })}>
                    <SelectTrigger><SelectValue placeholder="None" /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="none">None</SelectItem>
                        {['Plan 1', 'Plan 2', 'Plan 4', 'Plan 5'].map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label>Starter Declaration</Label>
                <Select value={form.starter_declaration || ''} onValueChange={v => set({ ...form, starter_declaration: v })}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="A">A — First job since 6 April</SelectItem>
                        <SelectItem value="B">B — Only job</SelectItem>
                        <SelectItem value="C">C — Another job / pension</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label>Auto-Enrolment Status</Label>
                <Select value={form.auto_enrolment_status || ''} onValueChange={v => set({ ...form, auto_enrolment_status: v })}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                        {['enrolled', 'opted_out', 'postponed', 'not_eligible'].map(s => <SelectItem key={s} value={s}>{s.replace('_', ' ')}</SelectItem>)}
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label>Payroll Start Date</Label>
                <Input type="date" value={form.payroll_start_date} onChange={e => set({ ...form, payroll_start_date: e.target.value })} />
            </div>
        </div>
    );
}

function StepBank({ form, set }) {
    return (
        <div className="space-y-4">
            <div className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/20 p-3 text-sm text-amber-700 dark:text-amber-300">
                Bank details are encrypted at rest and masked in the system. Access is audit-logged.
            </div>
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                    <Label>Account Holder Name</Label>
                    <Input value={form.account_holder_name} onChange={e => set({ ...form, account_holder_name: e.target.value })} />
                </div>
                <div className="space-y-1.5">
                    <Label>Bank Name</Label>
                    <Input value={form.bank_name} onChange={e => set({ ...form, bank_name: e.target.value })} placeholder="e.g. Barclays" />
                </div>
                <div className="space-y-1.5">
                    <Label>Sort Code</Label>
                    <Input value={form.bank_sort_code} onChange={e => set({ ...form, bank_sort_code: e.target.value })} placeholder="00-00-00" data-testid="input-sort-code" />
                </div>
                <div className="space-y-1.5">
                    <Label>Account Number</Label>
                    <Input value={form.bank_account} onChange={e => set({ ...form, bank_account: e.target.value })} placeholder="8 digits" data-testid="input-bank-account" />
                </div>
                <div className="space-y-1.5">
                    <Label>Building Society Roll No.</Label>
                    <Input value={form.building_society_roll} onChange={e => set({ ...form, building_society_roll: e.target.value })} placeholder="If applicable" />
                </div>
                <div className="space-y-1.5">
                    <Label>Payment Method</Label>
                    <Select value={form.payment_method} onValueChange={v => set({ ...form, payment_method: v })}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="bacs">BACS</SelectItem>
                            <SelectItem value="faster_payments">Faster Payments</SelectItem>
                            <SelectItem value="cash">Cash</SelectItem>
                            <SelectItem value="cheque">Cheque</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-1.5 col-span-2">
                    <Label>Payment Reference</Label>
                    <Input value={form.payment_reference} onChange={e => set({ ...form, payment_reference: e.target.value })} placeholder="e.g. employee ID or payroll ref" />
                </div>
            </div>
        </div>
    );
}

function StepRTW({ form, set }) {
    return (
        <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                    <Label>Right to Work Status</Label>
                    <Select value={form.right_to_work_status || ''} onValueChange={v => set({ ...form, right_to_work_status: v })}>
                        <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                        <SelectContent>
                            {['valid', 'time_limited', 'pending_check', 'not_required'].map(s => (
                                <SelectItem key={s} value={s}>{s.replace(/_/g, ' ')}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-1.5">
                    <Label>Document Type</Label>
                    <Select value={form.rtw_document_type || ''} onValueChange={v => set({ ...form, rtw_document_type: v })}>
                        <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                        <SelectContent>
                            {['Passport', 'Birth certificate + NI', 'BRP', 'eVisa share code', 'EEA ID card', 'Other'].map(t => (
                                <SelectItem key={t} value={t}>{t}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-1.5">
                    <Label>Check Date</Label>
                    <Input type="date" value={form.rtw_check_date} onChange={e => set({ ...form, rtw_check_date: e.target.value })} />
                </div>
                <div className="space-y-1.5">
                    <Label>RTW Expiry Date</Label>
                    <Input type="date" value={form.rtw_expiry_date} onChange={e => set({ ...form, rtw_expiry_date: e.target.value })} />
                </div>
                <div className="space-y-1.5 col-span-2">
                    <Label>Follow-up Check Date</Label>
                    <Input type="date" value={form.rtw_followup_date} onChange={e => set({ ...form, rtw_followup_date: e.target.value })} />
                </div>
            </div>

            <div className="border-t pt-4">
                <h4 className="font-medium mb-3 text-sm">Sponsored Worker / UKVI</h4>
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5 col-span-2">
                        <Label>Sponsored Worker?</Label>
                        <Select value={form.is_sponsored_worker ? 'yes' : 'no'} onValueChange={v => set({ ...form, is_sponsored_worker: v === 'yes' })}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="no">No</SelectItem>
                                <SelectItem value="yes">Yes — sponsored</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    {form.is_sponsored_worker && (<>
                        <div className="space-y-1.5">
                            <Label>CoS Number</Label>
                            <Input value={form.cos_number} onChange={e => set({ ...form, cos_number: e.target.value })} />
                        </div>
                        <div className="space-y-1.5">
                            <Label>SOC Code</Label>
                            <Input value={form.soc_code} onChange={e => set({ ...form, soc_code: e.target.value })} placeholder="e.g. 2135" />
                        </div>
                        <div className="space-y-1.5">
                            <Label>Visa Type</Label>
                            <Input value={form.visa_type} onChange={e => set({ ...form, visa_type: e.target.value })} placeholder="e.g. Skilled Worker" />
                        </div>
                        <div className="space-y-1.5">
                            <Label>Visa Expiry Date</Label>
                            <Input type="date" value={form.visa_expiry_date} onChange={e => set({ ...form, visa_expiry_date: e.target.value })} />
                        </div>
                        <div className="space-y-1.5 col-span-2">
                            <Label>Salary on CoS (£)</Label>
                            <Input type="number" value={form.cos_salary} onChange={e => set({ ...form, cos_salary: e.target.value })} />
                        </div>
                    </>)}
                </div>
            </div>
        </div>
    );
}

function StepEmergency({ form, set }) {
    return (
        <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5 col-span-2">
                <Label>Contact Name</Label>
                <Input value={form.emergency_name} onChange={e => set({ ...form, emergency_name: e.target.value })} />
            </div>
            <div className="space-y-1.5">
                <Label>Relationship</Label>
                <Select value={form.emergency_relationship || ''} onValueChange={v => set({ ...form, emergency_relationship: v })}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                        {['Spouse / Partner', 'Parent', 'Sibling', 'Child', 'Friend', 'Other'].map(r => (
                            <SelectItem key={r} value={r}>{r}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label>Primary Phone</Label>
                <Input value={form.emergency_phone} onChange={e => set({ ...form, emergency_phone: e.target.value })} />
            </div>
            <div className="space-y-1.5 col-span-2">
                <Label>Email</Label>
                <Input type="email" value={form.emergency_email} onChange={e => set({ ...form, emergency_email: e.target.value })} />
            </div>
        </div>
    );
}

function StepReview({ form }) {
    const sections = [
        { title: 'Personal', fields: [
            ['Name', `${form.title || ''} ${form.first_name} ${form.last_name}`.trim()],
            ['Preferred Name', form.preferred_name],
            ['Date of Birth', form.date_of_birth],
            ['NI Number', form.ni_number],
            ['Nationality', form.nationality],
        ]},
        { title: 'Contact', fields: [
            ['Email', form.email],
            ['Work Email', form.work_email],
            ['Mobile', form.mobile_phone],
            ['Postcode', form.postcode],
            ['Country', form.country],
        ]},
        { title: 'Employment', fields: [
            ['Job Title', form.job_title],
            ['Department', form.department],
            ['Start Date', form.start_date],
            ['Contract Type', form.contract_type],
            ['Employment Type', form.employment_type],
        ]},
        { title: 'Payroll & Tax', fields: [
            ['Salary', form.salary ? `£${form.salary}` : ''],
            ['Pay Frequency', form.pay_frequency],
            ['Tax Code', form.tax_code],
            ['NI Category', form.ni_category],
            ['Starter Declaration', form.starter_declaration],
        ]},
        { title: 'Bank', fields: [
            ['Account Holder', form.account_holder_name],
            ['Sort Code', form.bank_sort_code ? `**-**-${form.bank_sort_code.slice(-2)}` : ''],
            ['Account No.', form.bank_account ? `****${form.bank_account.slice(-4)}` : ''],
            ['Payment Method', form.payment_method],
        ]},
        { title: 'Emergency Contact', fields: [
            ['Name', form.emergency_name],
            ['Relationship', form.emergency_relationship],
            ['Phone', form.emergency_phone],
        ]},
    ];

    return (
        <div className="space-y-4">
            <div className="rounded-lg bg-muted/50 p-3 text-sm">
                Review details before saving. The employee will start with status <strong>{form.status}</strong>.
            </div>
            {sections.map(s => (
                <div key={s.title}>
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">{s.title}</h4>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                        {s.fields.filter(([, v]) => v).map(([k, v]) => (
                            <React.Fragment key={k}>
                                <span className="text-muted-foreground">{k}</span>
                                <span className="font-medium">{v}</span>
                            </React.Fragment>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}

function AddEmployeeWizard({ open, onOpenChange, onSaved }) {
    const [step, setStep] = useState(0);
    const [form, setForm] = useState({ ...EMPTY_FORM });
    const [saving, setSaving] = useState(false);

    const reset = () => { setStep(0); setForm({ ...EMPTY_FORM }); };

    const canProceed = () => {
        if (step === 0) return form.first_name && form.last_name;
        if (step === 1) return !!form.email;
        return true;
    };

    const submit = async (saveAsDraft) => {
        setSaving(true);
        try {
            const payload = {
                ...form,
                status: saveAsDraft ? 'draft' : (form.status === 'draft' ? 'onboarding' : form.status),
                salary: form.salary ? parseFloat(form.salary) : null,
                cos_salary: form.cos_salary ? parseFloat(form.cos_salary) : null,
                weekly_hours: form.weekly_hours ? parseFloat(form.weekly_hours) : null,
            };
            await axios.post(`${API_URL}/api/employees`, payload, { withCredentials: true });
            toast.success(saveAsDraft ? 'Employee saved as draft' : 'Employee added successfully');
            reset();
            onOpenChange(false);
            onSaved();
        } catch (error) {
            if (error.response?.status === 409) {
                toast.error(`Duplicate detected: ${error.response.data.detail}`);
            } else {
                toast.error(error.response?.data?.detail || 'Failed to add employee');
            }
        } finally {
            setSaving(false);
        }
    };

    const stepComponents = [
        <StepPersonal form={form} set={setForm} />,
        <StepContact form={form} set={setForm} />,
        <StepEmployment form={form} set={setForm} />,
        <StepPayroll form={form} set={setForm} />,
        <StepBank form={form} set={setForm} />,
        <StepRTW form={form} set={setForm} />,
        <StepEmergency form={form} set={setForm} />,
        <StepReview form={form} />,
    ];

    return (
        <Dialog open={open} onOpenChange={(o) => { if (!o) reset(); onOpenChange(o); }}>
            <DialogContent className="sm:max-w-[680px] max-h-[92vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Add New Employee</DialogTitle>
                    <DialogDescription>
                        Step {step + 1} of {WIZARD_STEPS.length} — {WIZARD_STEPS[step].label}
                    </DialogDescription>
                </DialogHeader>

                <WizardStepIndicator current={step} total={WIZARD_STEPS.length} steps={WIZARD_STEPS} />

                <div className="min-h-[320px]">
                    {stepComponents[step]}
                </div>

                <div className="flex items-center justify-between pt-4 border-t mt-4">
                    <Button variant="outline" size="sm" onClick={() => submit(true)} disabled={saving || !form.first_name}>
                        <Save className="w-3.5 h-3.5 mr-1.5" />
                        Save as Draft
                    </Button>
                    <div className="flex gap-2">
                        {step > 0 && (
                            <Button variant="outline" size="sm" onClick={() => setStep(s => s - 1)}>
                                <ChevronLeft className="w-3.5 h-3.5 mr-1" /> Back
                            </Button>
                        )}
                        {step < WIZARD_STEPS.length - 1 ? (
                            <Button size="sm" onClick={() => setStep(s => s + 1)} disabled={!canProceed()}>
                                Next <ChevronRightIcon className="w-3.5 h-3.5 ml-1" />
                            </Button>
                        ) : (
                            <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700" onClick={() => submit(false)} disabled={saving} data-testid="submit-employee-btn">
                                {saving ? <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <UserCheck className="w-3.5 h-3.5 mr-1.5" />}
                                {saving ? 'Saving...' : 'Add Employee'}
                            </Button>
                        )}
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}

function sortEmployees(employees, sortBy) {
    const arr = [...employees];
    switch (sortBy) {
        case 'name_asc': return arr.sort((a, b) => `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`));
        case 'name_desc': return arr.sort((a, b) => `${b.first_name} ${b.last_name}`.localeCompare(`${a.first_name} ${a.last_name}`));
        case 'start_date_desc': return arr.sort((a, b) => new Date(b.start_date || 0) - new Date(a.start_date || 0));
        case 'start_date_asc': return arr.sort((a, b) => new Date(a.start_date || 0) - new Date(b.start_date || 0));
        case 'department': return arr.sort((a, b) => (a.department || '').localeCompare(b.department || ''));
        case 'status': return arr.sort((a, b) => (a.status || '').localeCompare(b.status || ''));
        default: return arr;
    }
}

function ReadinessBadge({ ready, label }) {
    return (
        <span className={cn(
            'inline-flex items-center gap-0.5 text-xs px-1.5 py-0.5 rounded whitespace-nowrap',
            ready
                ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300'
                : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
        )}>
            {ready ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
            {label}
        </span>
    );
}

function ComplianceBadge({ score }) {
    if (score === null || score === undefined) {
        return <span className="text-xs text-muted-foreground">Unscanned</span>;
    }
    const color = score >= 90 ? 'text-emerald-600' : score >= 70 ? 'text-amber-600' : 'text-rose-600';
    return (
        <span className={cn('text-xs font-medium', color)}>
            {score}%
            {score < 80 && <AlertTriangle className="w-3 h-3 inline ml-1" />}
        </span>
    );
}

export default function EmployeesPage() {
    const navigate = useNavigate();
    const { token, user } = useAuth();
    const isAdmin = user?.role === 'owner' || user?.role === 'admin';
    const [employees, setEmployees] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [readinessFilter, setReadinessFilter] = useState('all');
    const [sortBy, setSortBy] = useState('name_asc');
    const [wizardOpen, setWizardOpen] = useState(false);
    const [viewMode, setViewMode] = useState('table');

    useEffect(() => {
        fetchEmployees();
    }, []);

    const fetchEmployees = async () => {
        try {
            const data = await requestOrDefault(
                axios.get(`${API_URL}/api/employees`, { withCredentials: true }),
                [],
                'employees'
            );
            setEmployees(Array.isArray(data) ? data : []);
        } finally {
            setLoading(false);
        }
    };

    const runReadinessCheck = async (employeeId, e) => {
        e.stopPropagation();
        try {
            await axios.get(`${API_URL}/api/employees/${employeeId}/readiness`, { withCredentials: true });
            toast.success('Readiness check complete');
            fetchEmployees();
        } catch {
            toast.error('Failed to run readiness check');
        }
    };

    const archiveEmployee = async (employeeId, e) => {
        e.stopPropagation();
        if (!window.confirm('Archive this employee? They will be moved to archived status.')) return;
        try {
            await axios.post(`${API_URL}/api/employees/${employeeId}/archive`, {}, { withCredentials: true });
            toast.success('Employee archived');
            fetchEmployees();
        } catch {
            toast.error('Failed to archive employee');
        }
    };

    const deleteEmployee = async (emp, e) => {
        e.stopPropagation();
        if (!window.confirm(`Permanently delete ${emp.first_name} ${emp.last_name}? This cannot be undone.`)) return;
        try {
            await axios.delete(`${API_URL}/api/employees/${emp.employee_id}`, {
                headers: { Authorization: `Bearer ${token}` },
                withCredentials: true,
            });
            toast.success('Employee deleted');
            fetchEmployees();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to delete employee');
        }
    };

    const exportEmployees = async () => {
        try {
            const token = localStorage.getItem('token');
            const res = await axios.get(`${API_URL}/api/employees-export`, {
                headers: { Authorization: `Bearer ${token}` },
                withCredentials: true,
                responseType: 'blob',
            });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const a = document.createElement('a');
            a.href = url;
            a.download = `employees_${new Date().toISOString().slice(0, 10)}.csv`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            toast.success('Export downloaded');
        } catch {
            toast.error('Export not available');
        }
    };

    const filteredEmployees = sortEmployees(
        employees.filter(emp => {
            const name = `${emp.first_name} ${emp.last_name}`.toLowerCase();
            const search = searchTerm.toLowerCase();
            const matchSearch = !searchTerm || name.includes(search) ||
                emp.email?.toLowerCase().includes(search) ||
                emp.job_title?.toLowerCase().includes(search) ||
                emp.ni_number?.toLowerCase().includes(search) ||
                emp.department?.toLowerCase().includes(search) ||
                emp.work_location?.toLowerCase().includes(search);

            const matchStatus = statusFilter === 'all' || emp.status?.toLowerCase() === statusFilter;

            let matchReadiness = true;
            if (readinessFilter === 'payroll_ready') matchReadiness = emp.payroll_ready === true;
            else if (readinessFilter === 'rti_ready') matchReadiness = emp.rti_ready === true;
            else if (readinessFilter === 'rtw_ready') matchReadiness = emp.right_to_work_ready === true;
            else if (readinessFilter === 'not_payroll_ready') matchReadiness = !emp.payroll_ready;
            else if (readinessFilter === 'not_rti_ready') matchReadiness = !emp.rti_ready;

            return matchSearch && matchStatus && matchReadiness;
        }),
        sortBy
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-6" data-testid="employees-page">
            <AddEmployeeWizard open={wizardOpen} onOpenChange={setWizardOpen} onSaved={fetchEmployees} />

            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Employees</h1>
                    <p className="text-muted-foreground mt-1">
                        {employees.length} total &mdash; {employees.filter(e => e.status === 'active').length} active
                    </p>
                </div>
                <div className="flex gap-2 flex-wrap">
                    {/* View toggle */}
                    <div className="flex rounded-md border overflow-hidden">
                        <button
                            className={cn('px-2.5 py-1.5 text-sm flex items-center gap-1.5 transition-colors', viewMode === 'table' ? 'bg-indigo-600 text-white' : 'hover:bg-muted')}
                            onClick={() => setViewMode('table')}
                            title="Table view"
                        >
                            <LayoutList className="w-4 h-4" />
                        </button>
                        <button
                            className={cn('px-2.5 py-1.5 text-sm flex items-center gap-1.5 transition-colors border-l', viewMode === 'grid' ? 'bg-indigo-600 text-white' : 'hover:bg-muted')}
                            onClick={() => setViewMode('grid')}
                            title="Grid view"
                        >
                            <LayoutGrid className="w-4 h-4" />
                        </button>
                    </div>
                    <Button variant="outline" size="sm" onClick={exportEmployees}>
                        <Download className="w-4 h-4 mr-2" />
                        Export
                    </Button>
                    <Button className="bg-indigo-600 hover:bg-indigo-700" onClick={() => setWizardOpen(true)} data-testid="add-employee-btn">
                        <Plus className="w-4 h-4 mr-2" />
                        Add Employee
                    </Button>
                </div>
            </div>

            {/* Search + Filters */}
            <div className="flex flex-wrap gap-3 items-center">
                <div className="relative flex-1 min-w-48 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                        placeholder="Search name, email, NI, department, location…"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-10"
                        data-testid="search-employees"
                    />
                </div>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-44" data-testid="filter-status">
                        <Filter className="w-3.5 h-3.5 mr-1" />
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {STATUS_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                    </SelectContent>
                </Select>
                <Select value={readinessFilter} onValueChange={setReadinessFilter}>
                    <SelectTrigger className="w-44" data-testid="filter-readiness">
                        <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {READINESS_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                    </SelectContent>
                </Select>
                <Select value={sortBy} onValueChange={setSortBy}>
                    <SelectTrigger className="w-40" data-testid="sort-employees">
                        <ArrowUpDown className="w-3.5 h-3.5 mr-1" />
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {SORT_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                    </SelectContent>
                </Select>
                {(statusFilter !== 'all' || readinessFilter !== 'all' || searchTerm) && (
                    <Button variant="ghost" size="sm" onClick={() => { setStatusFilter('all'); setReadinessFilter('all'); setSearchTerm(''); }}>
                        <XCircle className="w-3.5 h-3.5 mr-1" /> Clear
                    </Button>
                )}
                <span className="text-sm text-muted-foreground">{filteredEmployees.length} of {employees.length}</span>
            </div>

            {/* Empty state */}
            {filteredEmployees.length === 0 ? (
                <Card>
                    <CardContent className="py-16 text-center">
                        <Users className="w-16 h-16 mx-auto text-muted-foreground/50" />
                        <h3 className="mt-4 text-lg font-semibold">No employees found</h3>
                        <p className="text-muted-foreground mt-1">
                            {searchTerm || statusFilter !== 'all' || readinessFilter !== 'all'
                                ? 'Try adjusting your search or filters'
                                : 'Add your first employee to get started'}
                        </p>
                        {!searchTerm && statusFilter === 'all' && readinessFilter === 'all' && (
                            <Button className="mt-4 bg-indigo-600 hover:bg-indigo-700" onClick={() => setWizardOpen(true)}>
                                <Plus className="w-4 h-4 mr-2" /> Add First Employee
                            </Button>
                        )}
                    </CardContent>
                </Card>
            ) : viewMode === 'table' ? (
                /* ---- TABLE VIEW ---- */
                <Card className="overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b bg-muted/40">
                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground whitespace-nowrap">Employee</th>
                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground whitespace-nowrap">Department</th>
                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground whitespace-nowrap">Job Title</th>
                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground whitespace-nowrap">Status</th>
                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground whitespace-nowrap">Start Date</th>
                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground whitespace-nowrap">Payroll</th>
                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground whitespace-nowrap">RTI</th>
                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground whitespace-nowrap">RTW</th>
                                    <th className="text-left px-4 py-3 font-medium text-muted-foreground whitespace-nowrap">Compliance</th>
                                    <th className="text-right px-4 py-3 font-medium text-muted-foreground whitespace-nowrap">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredEmployees.map((emp, idx) => (
                                    <tr
                                        key={emp.employee_id}
                                        className={cn(
                                            'border-b last:border-0 hover:bg-accent/50 cursor-pointer transition-colors',
                                            idx % 2 === 0 ? '' : 'bg-muted/20'
                                        )}
                                        onClick={() => navigate(`/employees/${emp.employee_id}`)}
                                        data-testid={`employee-row-${emp.employee_id}`}
                                    >
                                        {/* Employee name + avatar */}
                                        <td className="px-4 py-3">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center flex-shrink-0">
                                                    <span className="text-xs font-semibold text-indigo-700 dark:text-indigo-300">
                                                        {emp.first_name?.[0]}{emp.last_name?.[0]}
                                                    </span>
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="font-medium truncate max-w-[140px]">{emp.first_name} {emp.last_name}</p>
                                                    <p className="text-xs text-muted-foreground truncate max-w-[140px]">{emp.email}</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground">{emp.department || '—'}</td>
                                        <td className="px-4 py-3 text-muted-foreground truncate max-w-[140px]">{emp.job_title || '—'}</td>
                                        <td className="px-4 py-3">
                                            <Badge className={getStatusColor(emp.status)} variant="secondary">
                                                {emp.status || 'active'}
                                            </Badge>
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                                            {emp.start_date ? emp.start_date.slice(0, 10) : '—'}
                                        </td>
                                        <td className="px-4 py-3">
                                            <ReadinessBadge ready={emp.payroll_ready} label="Payroll" />
                                        </td>
                                        <td className="px-4 py-3">
                                            <ReadinessBadge ready={emp.rti_ready} label="RTI" />
                                        </td>
                                        <td className="px-4 py-3">
                                            <ReadinessBadge ready={emp.right_to_work_ready} label="RTW" />
                                        </td>
                                        <td className="px-4 py-3">
                                            <ComplianceBadge score={emp.compliance_score} />
                                        </td>
                                        <td className="px-4 py-3 text-right" onClick={e => e.stopPropagation()}>
                                            <DropdownMenu>
                                                <DropdownMenuTrigger asChild>
                                                    <Button variant="ghost" size="icon" className="h-7 w-7">
                                                        <MoreVertical className="w-3.5 h-3.5" />
                                                    </Button>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent align="end">
                                                    <DropdownMenuItem onClick={() => navigate(`/employees/${emp.employee_id}`)}>
                                                        <Eye className="w-4 h-4 mr-2" /> View profile
                                                    </DropdownMenuItem>
                                                    <DropdownMenuItem onClick={(e) => runReadinessCheck(emp.employee_id, e)}>
                                                        <RefreshCw className="w-4 h-4 mr-2" /> Run readiness check
                                                    </DropdownMenuItem>
                                                    <DropdownMenuSeparator />
                                                    <DropdownMenuItem className="text-rose-600" onClick={(e) => archiveEmployee(emp.employee_id, e)}>
                                                        <Archive className="w-4 h-4 mr-2" /> Archive
                                                    </DropdownMenuItem>
                                                    {isAdmin && (
                                                        <DropdownMenuItem className="text-red-700 font-medium" onClick={(e) => deleteEmployee(emp, e)}>
                                                            <XCircle className="w-4 h-4 mr-2" /> Delete permanently
                                                        </DropdownMenuItem>
                                                    )}
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            ) : (
                /* ---- GRID / CARD VIEW ---- */
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredEmployees.map((emp) => (
                        <Card
                            key={emp.employee_id}
                            className="hover:shadow-md transition-all hover-lift cursor-pointer"
                            onClick={() => navigate(`/employees/${emp.employee_id}`)}
                            data-testid={`employee-card-${emp.employee_id}`}
                        >
                            <CardContent className="p-6">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="w-12 h-12 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center flex-shrink-0">
                                            <span className="text-lg font-medium text-indigo-700 dark:text-indigo-300">
                                                {emp.first_name?.[0]}{emp.last_name?.[0]}
                                            </span>
                                        </div>
                                        <div className="min-w-0">
                                            <h3 className="font-semibold truncate">{emp.first_name} {emp.last_name}</h3>
                                            <p className="text-sm text-muted-foreground truncate">{emp.job_title || 'No title'}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                                        <Badge className={getStatusColor(emp.status)}>{emp.status || 'active'}</Badge>
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild onClick={e => e.stopPropagation()}>
                                                <Button variant="ghost" size="icon" className="h-7 w-7">
                                                    <MoreVertical className="w-3.5 h-3.5" />
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end">
                                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigate(`/employees/${emp.employee_id}`); }}>
                                                    <Eye className="w-4 h-4 mr-2" /> View profile
                                                </DropdownMenuItem>
                                                <DropdownMenuItem onClick={(e) => runReadinessCheck(emp.employee_id, e)}>
                                                    <RefreshCw className="w-4 h-4 mr-2" /> Run readiness check
                                                </DropdownMenuItem>
                                                <DropdownMenuSeparator />
                                                <DropdownMenuItem className="text-rose-600" onClick={(e) => archiveEmployee(emp.employee_id, e)}>
                                                    <Archive className="w-4 h-4 mr-2" /> Archive
                                                </DropdownMenuItem>
                                                {isAdmin && (
                                                    <DropdownMenuItem className="text-red-700 font-medium" onClick={(e) => deleteEmployee(emp, e)}>
                                                        <XCircle className="w-4 h-4 mr-2" /> Delete permanently
                                                    </DropdownMenuItem>
                                                )}
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </div>
                                </div>

                                <div className="mt-3 space-y-1.5">
                                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                        <Mail className="w-3.5 h-3.5 flex-shrink-0" />
                                        <span className="truncate">{emp.email}</span>
                                    </div>
                                    {emp.department && (
                                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                            <Briefcase className="w-3.5 h-3.5 flex-shrink-0" />
                                            <span className="truncate">{emp.department}</span>
                                        </div>
                                    )}
                                </div>

                                {/* Readiness flags */}
                                <div className="mt-3 flex flex-wrap gap-1">
                                    <ReadinessBadge ready={emp.payroll_ready} label="Payroll" />
                                    <ReadinessBadge ready={emp.rti_ready} label="RTI" />
                                    <ReadinessBadge ready={emp.right_to_work_ready} label="RTW" />
                                </div>

                                <div className="mt-3 pt-3 border-t border-border flex items-center justify-between">
                                    <ComplianceBadge score={emp.compliance_score} />
                                    <ArrowRight className="w-4 h-4 text-muted-foreground" />
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
