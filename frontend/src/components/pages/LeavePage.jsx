import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Calendar } from '../ui/calendar';
import { 
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '../ui/dialog';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../ui/select';
import { 
    Plus, 
    Calendar as CalendarIcon,
    CheckCircle2,
    XCircle,
    Clock
} from 'lucide-react';
import { cn, formatDate, getStatusColor } from '../../lib/utils';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const leaveTypes = [
    { value: 'annual', label: 'Annual Leave' },
    { value: 'sick', label: 'Sick Leave' },
    { value: 'personal', label: 'Personal Leave' },
    { value: 'maternity', label: 'Maternity Leave' },
    { value: 'paternity', label: 'Paternity Leave' },
    { value: 'other', label: 'Other' }
];

export default function LeavePage() {
    const navigate = useNavigate();
    const [leaves, setLeaves] = useState([]);
    const [loading, setLoading] = useState(true);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [selectedDate, setSelectedDate] = useState(new Date());
    const [formData, setFormData] = useState({
        leave_type: '',
        start_date: '',
        end_date: '',
        reason: ''
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        fetchLeaves();
    }, []);

    const fetchLeaves = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/leave`, { withCredentials: true });
            setLeaves(response.data);
        } catch (error) {
            toast.error('Failed to load leave requests');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await axios.post(`${API_URL}/api/leave`, formData, { withCredentials: true });
            toast.success('Leave request submitted');
            setDialogOpen(false);
            setFormData({ leave_type: '', start_date: '', end_date: '', reason: '' });
            fetchLeaves();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to submit request');
        } finally {
            setSubmitting(false);
        }
    };

    const handleApprove = async (leaveId) => {
        try {
            await axios.put(`${API_URL}/api/leave/${leaveId}`, { status: 'approved' }, { withCredentials: true });
            toast.success('Leave approved');
            fetchLeaves();
        } catch (error) {
            toast.error('Failed to approve leave');
        }
    };

    const handleReject = async (leaveId) => {
        try {
            await axios.put(`${API_URL}/api/leave/${leaveId}`, { status: 'rejected' }, { withCredentials: true });
            toast.success('Leave rejected');
            fetchLeaves();
        } catch (error) {
            toast.error('Failed to reject leave');
        }
    };

    // Get dates with leaves for calendar highlighting
    const leaveDates = leaves
        .filter(l => l.status === 'approved')
        .flatMap(l => {
            const dates = [];
            const start = new Date(l.start_date);
            const end = new Date(l.end_date);
            for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
                dates.push(new Date(d));
            }
            return dates;
        });

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-6" data-testid="leave-page">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Leave & Absence</h1>
                    <p className="text-muted-foreground mt-1">Manage leave requests and view the team calendar</p>
                </div>
                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                    <DialogTrigger asChild>
                        <Button className="bg-indigo-600 hover:bg-indigo-700" data-testid="request-leave-btn">
                            <Plus className="w-4 h-4 mr-2" />
                            Request Leave
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Request Leave</DialogTitle>
                            <DialogDescription>
                                Submit a new leave request for approval
                            </DialogDescription>
                        </DialogHeader>
                        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                            <div className="space-y-2">
                                <Label>Leave Type</Label>
                                <Select
                                    value={formData.leave_type}
                                    onValueChange={(value) => setFormData({ ...formData, leave_type: value })}
                                >
                                    <SelectTrigger data-testid="select-leave-type">
                                        <SelectValue placeholder="Select leave type" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {leaveTypes.map(type => (
                                            <SelectItem key={type.value} value={type.value}>
                                                {type.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="start_date">Start Date</Label>
                                    <Input
                                        id="start_date"
                                        type="date"
                                        value={formData.start_date}
                                        onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                                        required
                                        data-testid="input-start-date"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="end_date">End Date</Label>
                                    <Input
                                        id="end_date"
                                        type="date"
                                        value={formData.end_date}
                                        onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                                        required
                                        data-testid="input-end-date"
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="reason">Reason (optional)</Label>
                                <Textarea
                                    id="reason"
                                    value={formData.reason}
                                    onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                                    placeholder="Add any notes..."
                                    data-testid="input-reason"
                                />
                            </div>
                            <div className="flex justify-end gap-3 mt-6">
                                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                                    Cancel
                                </Button>
                                <Button type="submit" disabled={submitting} data-testid="submit-leave-btn">
                                    {submitting ? 'Submitting...' : 'Submit Request'}
                                </Button>
                            </div>
                        </form>
                    </DialogContent>
                </Dialog>
            </div>

            {/* Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Calendar */}
                <Card className="lg:col-span-1" data-testid="leave-calendar">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <CalendarIcon className="w-5 h-5" />
                            Team Calendar
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Calendar
                            mode="single"
                            selected={selectedDate}
                            onSelect={setSelectedDate}
                            className="rounded-md border"
                            modifiers={{
                                leave: leaveDates
                            }}
                            modifiersStyles={{
                                leave: { backgroundColor: 'hsl(var(--primary) / 0.2)', borderRadius: '4px' }
                            }}
                        />
                    </CardContent>
                </Card>

                {/* Leave Requests */}
                <Card className="lg:col-span-2" data-testid="leave-requests">
                    <CardHeader>
                        <CardTitle>Leave Requests</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {leaves.length === 0 ? (
                            <div className="text-center py-8 text-muted-foreground">
                                <CalendarIcon className="w-12 h-12 mx-auto opacity-50" />
                                <p className="mt-4">No leave requests yet</p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {leaves.map((leave) => (
                                    <div 
                                        key={leave.leave_id}
                                        className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className={cn(
                                                "p-2 rounded-lg",
                                                leave.status === 'approved' ? 'bg-emerald-100 dark:bg-emerald-900/30' :
                                                leave.status === 'rejected' ? 'bg-rose-100 dark:bg-rose-900/30' :
                                                'bg-amber-100 dark:bg-amber-900/30'
                                            )}>
                                                {leave.status === 'approved' ? (
                                                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                                                ) : leave.status === 'rejected' ? (
                                                    <XCircle className="w-5 h-5 text-rose-600" />
                                                ) : (
                                                    <Clock className="w-5 h-5 text-amber-600" />
                                                )}
                                            </div>
                                            <div>
                                                <p className="font-medium capitalize">{leave.leave_type.replace('_', ' ')}</p>
                                                <p className="text-sm text-muted-foreground">
                                                    {formatDate(leave.start_date)} - {formatDate(leave.end_date)} ({leave.days} days)
                                                </p>
                                                {leave.reason && (
                                                    <p className="text-sm text-muted-foreground mt-1">{leave.reason}</p>
                                                )}
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <Badge className={getStatusColor(leave.status)}>{leave.status}</Badge>
                                            {leave.status === 'pending' && (
                                                <div className="flex gap-2">
                                                    <Button 
                                                        size="sm" 
                                                        variant="outline"
                                                        className="text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                                                        onClick={() => handleApprove(leave.leave_id)}
                                                        data-testid={`approve-leave-${leave.leave_id}`}
                                                    >
                                                        Approve
                                                    </Button>
                                                    <Button 
                                                        size="sm" 
                                                        variant="outline"
                                                        className="text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                                                        onClick={() => handleReject(leave.leave_id)}
                                                        data-testid={`reject-leave-${leave.leave_id}`}
                                                    >
                                                        Reject
                                                    </Button>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
