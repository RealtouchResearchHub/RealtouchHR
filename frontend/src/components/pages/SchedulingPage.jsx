import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../ui/select';
import { 
    Plus, 
    Clock,
    Calendar,
    Play,
    Square,
    Users
} from 'lucide-react';
import { cn, formatDate, getStatusColor } from '../../lib/utils';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function SchedulingPage() {
    const [shifts, setShifts] = useState([]);
    const [employees, setEmployees] = useState([]);
    const [loading, setLoading] = useState(true);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [formData, setFormData] = useState({
        employee_id: '',
        date: '',
        start_time: '',
        end_time: '',
        break_minutes: 30
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [shiftsRes, empRes] = await Promise.all([
                axios.get(`${API_URL}/api/shifts`, { withCredentials: true }),
                axios.get(`${API_URL}/api/employees`, { withCredentials: true })
            ]);
            setShifts(shiftsRes.data);
            setEmployees(empRes.data);
        } catch (error) {
            toast.error('Failed to load scheduling data');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await axios.post(`${API_URL}/api/shifts`, formData, { withCredentials: true });
            toast.success('Shift created successfully');
            setDialogOpen(false);
            setFormData({
                employee_id: '',
                date: '',
                start_time: '',
                end_time: '',
                break_minutes: 30
            });
            fetchData();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to create shift');
        } finally {
            setSubmitting(false);
        }
    };

    const handleClockIn = async (shiftId) => {
        try {
            await axios.post(`${API_URL}/api/shifts/${shiftId}/clock-in`, {}, { withCredentials: true });
            toast.success('Clocked in successfully');
            fetchData();
        } catch (error) {
            toast.error('Failed to clock in');
        }
    };

    const handleClockOut = async (shiftId) => {
        try {
            await axios.post(`${API_URL}/api/shifts/${shiftId}/clock-out`, {}, { withCredentials: true });
            toast.success('Clocked out successfully');
            fetchData();
        } catch (error) {
            toast.error('Failed to clock out');
        }
    };

    const getEmployeeName = (empId) => {
        const emp = employees.find(e => e.employee_id === empId);
        return emp ? `${emp.first_name} ${emp.last_name}` : 'Unknown';
    };

    // Group shifts by date
    const shiftsByDate = shifts.reduce((acc, shift) => {
        const date = shift.date;
        if (!acc[date]) acc[date] = [];
        acc[date].push(shift);
        return acc;
    }, {});

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-6" data-testid="scheduling-page">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Scheduling</h1>
                    <p className="text-muted-foreground mt-1">Manage shifts, rotas, and clock-ins</p>
                </div>
                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                    <DialogTrigger asChild>
                        <Button className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-shift-btn">
                            <Plus className="w-4 h-4 mr-2" />
                            Add Shift
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Create New Shift</DialogTitle>
                            <DialogDescription>
                                Schedule a shift for an employee
                            </DialogDescription>
                        </DialogHeader>
                        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                            <div className="space-y-2">
                                <Label>Employee</Label>
                                <Select
                                    value={formData.employee_id}
                                    onValueChange={(value) => setFormData({ ...formData, employee_id: value })}
                                >
                                    <SelectTrigger data-testid="select-employee">
                                        <SelectValue placeholder="Select employee" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {employees.map(emp => (
                                            <SelectItem key={emp.employee_id} value={emp.employee_id}>
                                                {emp.first_name} {emp.last_name}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="date">Date</Label>
                                <Input
                                    id="date"
                                    type="date"
                                    value={formData.date}
                                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                                    required
                                    data-testid="input-shift-date"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="start_time">Start Time</Label>
                                    <Input
                                        id="start_time"
                                        type="time"
                                        value={formData.start_time}
                                        onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                                        required
                                        data-testid="input-start-time"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="end_time">End Time</Label>
                                    <Input
                                        id="end_time"
                                        type="time"
                                        value={formData.end_time}
                                        onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                                        required
                                        data-testid="input-end-time"
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="break_minutes">Break (minutes)</Label>
                                <Input
                                    id="break_minutes"
                                    type="number"
                                    value={formData.break_minutes}
                                    onChange={(e) => setFormData({ ...formData, break_minutes: parseInt(e.target.value) })}
                                    min="0"
                                    data-testid="input-break-minutes"
                                />
                            </div>
                            <div className="flex justify-end gap-3 mt-6">
                                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                                    Cancel
                                </Button>
                                <Button type="submit" disabled={submitting} data-testid="submit-shift-btn">
                                    {submitting ? 'Creating...' : 'Create Shift'}
                                </Button>
                            </div>
                        </form>
                    </DialogContent>
                </Dialog>
            </div>

            {/* Shifts by Date */}
            {Object.keys(shiftsByDate).length === 0 ? (
                <Card>
                    <CardContent className="py-16 text-center">
                        <Clock className="w-16 h-16 mx-auto text-muted-foreground/50" />
                        <h3 className="mt-4 text-lg font-semibold">No shifts scheduled</h3>
                        <p className="text-muted-foreground mt-1">
                            Add a shift to get started with scheduling
                        </p>
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-6">
                    {Object.entries(shiftsByDate)
                        .sort((a, b) => new Date(b[0]) - new Date(a[0]))
                        .map(([date, dateShifts]) => (
                            <Card key={date} data-testid={`shifts-${date}`}>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <Calendar className="w-5 h-5" />
                                        {formatDate(date)}
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-3">
                                        {dateShifts.map((shift) => (
                                            <div 
                                                key={shift.shift_id}
                                                className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors"
                                            >
                                                <div className="flex items-center gap-4">
                                                    <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
                                                        <Users className="w-5 h-5 text-indigo-600" />
                                                    </div>
                                                    <div>
                                                        <p className="font-medium">{getEmployeeName(shift.employee_id)}</p>
                                                        <p className="text-sm text-muted-foreground">
                                                            {shift.start_time} - {shift.end_time} ({shift.break_minutes}min break)
                                                        </p>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <Badge className={getStatusColor(shift.status)}>{shift.status}</Badge>
                                                    {shift.status === 'scheduled' && (
                                                        <Button 
                                                            size="sm" 
                                                            variant="outline"
                                                            className="text-emerald-600"
                                                            onClick={() => handleClockIn(shift.shift_id)}
                                                            data-testid={`clock-in-${shift.shift_id}`}
                                                        >
                                                            <Play className="w-4 h-4 mr-1" />
                                                            Clock In
                                                        </Button>
                                                    )}
                                                    {shift.status === 'in-progress' && (
                                                        <Button 
                                                            size="sm" 
                                                            variant="outline"
                                                            className="text-rose-600"
                                                            onClick={() => handleClockOut(shift.shift_id)}
                                                            data-testid={`clock-out-${shift.shift_id}`}
                                                        >
                                                            <Square className="w-4 h-4 mr-1" />
                                                            Clock Out
                                                        </Button>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                </div>
            )}
        </div>
    );
}
