import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { 
  Clock, 
  Play, 
  Pause, 
  Square,
  Calendar,
  Users,
  FileText,
  CheckCircle,
  XCircle,
  RefreshCw,
  Plus,
  ChevronLeft,
  ChevronRight,
  Coffee,
  MapPin
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function TimeSchedulingPage() {
  const [activeTab, setActiveTab] = useState('clock');
  const [clockStatus, setClockStatus] = useState(null);
  const [shifts, setShifts] = useState([]);
  const [timesheets, setTimesheets] = useState([]);
  const [pendingTimesheets, setPendingTimesheets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [clockLoading, setClockLoading] = useState(false);
  const [selectedWeek, setSelectedWeek] = useState(getWeekStart(new Date()));

  function getWeekStart(d) {
    const date = new Date(d);
    const day = date.getDay();
    const diff = date.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(date.setDate(diff)).toISOString().split('T')[0];
  }

  function getWeekEnd(startDate) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + 6);
    return date.toISOString().split('T')[0];
  }

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      // Fetch clock status
      const statusRes = await fetch(`${BACKEND_URL}/api/time/status`, { headers });
      if (statusRes.ok) {
        setClockStatus(await statusRes.json());
      }

      // Fetch shifts for selected week
      const weekEnd = getWeekEnd(selectedWeek);
      const shiftsRes = await fetch(
        `${BACKEND_URL}/api/time/shifts?start_date=${selectedWeek}&end_date=${weekEnd}`,
        { headers }
      );
      if (shiftsRes.ok) {
        const data = await shiftsRes.json();
        setShifts(data.shifts || []);
      }

      // Fetch timesheets
      const tsRes = await fetch(`${BACKEND_URL}/api/time/timesheets?limit=10`, { headers });
      if (tsRes.ok) {
        const data = await tsRes.json();
        setTimesheets(data.timesheets || []);
      }

      // Fetch pending timesheets for approval
      const pendingRes = await fetch(`${BACKEND_URL}/api/time/timesheets/pending`, { headers });
      if (pendingRes.ok) {
        const data = await pendingRes.json();
        setPendingTimesheets(data.timesheets || []);
      }
    } catch (error) {
      console.error('Error fetching time data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedWeek]);

  const handleClockIn = async () => {
    setClockLoading(true);
    try {
      const token = localStorage.getItem('token');
      
      // Get location if available
      let location = null;
      if (navigator.geolocation) {
        try {
          const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
          });
          location = {
            lat: position.coords.latitude,
            lng: position.coords.longitude
          };
        } catch (e) {
          console.log('Location not available');
        }
      }

      const response = await fetch(`${BACKEND_URL}/api/time/clock-in`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ location })
      });

      if (response.ok) {
        fetchData();
      }
    } catch (error) {
      console.error('Clock in error:', error);
    } finally {
      setClockLoading(false);
    }
  };

  const handleClockOut = async () => {
    setClockLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${BACKEND_URL}/api/time/clock-out`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
      });

      if (response.ok) {
        fetchData();
      }
    } catch (error) {
      console.error('Clock out error:', error);
    } finally {
      setClockLoading(false);
    }
  };

  const handleBreakStart = async () => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`${BACKEND_URL}/api/time/break/start`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchData();
    } catch (error) {
      console.error('Break start error:', error);
    }
  };

  const handleBreakEnd = async () => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`${BACKEND_URL}/api/time/break/end`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchData();
    } catch (error) {
      console.error('Break end error:', error);
    }
  };

  const handleApproveTimesheet = async (timesheetId) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`${BACKEND_URL}/api/time/timesheets/${timesheetId}/approve`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchData();
    } catch (error) {
      console.error('Approve error:', error);
    }
  };

  const formatDuration = (minutes) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'clocked_in':
        return <Badge className="bg-emerald-500">Clocked In</Badge>;
      case 'on_break':
        return <Badge className="bg-amber-500">On Break</Badge>;
      default:
        return <Badge variant="secondary">Not Clocked In</Badge>;
    }
  };

  const navigateWeek = (direction) => {
    const current = new Date(selectedWeek);
    current.setDate(current.getDate() + (direction * 7));
    setSelectedWeek(current.toISOString().split('T')[0]);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen" data-testid="time-page-loading">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  // Check if user has no employee record
  const noEmployeeRecord = clockStatus?.status === 'not_clocked_in' && !clockStatus?.last_event;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Time & Scheduling</h1>
          <p className="text-muted-foreground mt-1">
            Clock in/out, view schedules, and manage timesheets
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b pb-2">
        {[
          { id: 'clock', label: 'Clock In/Out', icon: Clock },
          { id: 'schedule', label: 'Schedule', icon: Calendar },
          { id: 'timesheets', label: 'Timesheets', icon: FileText },
          { id: 'approvals', label: 'Approvals', icon: CheckCircle }
        ].map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab(tab.id)}
            className="gap-2"
            data-testid={`time-tab-${tab.id}`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
            {tab.id === 'approvals' && pendingTimesheets.length > 0 && (
              <Badge variant="destructive" className="ml-1 px-1.5 py-0.5 text-xs">
                {pendingTimesheets.length}
              </Badge>
            )}
          </Button>
        ))}
      </div>

      {/* Clock Tab */}
      {activeTab === 'clock' && (
        <div className="grid gap-6 md:grid-cols-2">
          <Card className="md:col-span-1">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5" />
                Time Clock
              </CardTitle>
              <CardDescription>Record your work hours</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="text-center">
                <p className="text-5xl font-bold font-mono mb-4">
                  {new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                </p>
                <p className="text-muted-foreground">
                  {new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}
                </p>
              </div>

              <div className="flex justify-center">
                {getStatusBadge(clockStatus?.status)}
              </div>

              {clockStatus?.status === 'clocked_in' && clockStatus?.duration_minutes && (
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Working for</p>
                  <p className="text-2xl font-bold">{formatDuration(clockStatus.duration_minutes)}</p>
                </div>
              )}

              <div className="flex justify-center gap-3">
                {clockStatus?.status === 'not_clocked_in' ? (
                  <Button 
                    size="lg" 
                    onClick={handleClockIn}
                    disabled={clockLoading}
                    className="gap-2"
                    data-testid="clock-in-btn"
                  >
                    <Play className="w-5 h-5" />
                    Clock In
                  </Button>
                ) : clockStatus?.status === 'clocked_in' ? (
                  <>
                    <Button 
                      variant="outline" 
                      size="lg"
                      onClick={handleBreakStart}
                      className="gap-2"
                    >
                      <Coffee className="w-5 h-5" />
                      Start Break
                    </Button>
                    <Button 
                      variant="destructive" 
                      size="lg"
                      onClick={handleClockOut}
                      disabled={clockLoading}
                      className="gap-2"
                      data-testid="clock-out-btn"
                    >
                      <Square className="w-5 h-5" />
                      Clock Out
                    </Button>
                  </>
                ) : clockStatus?.status === 'on_break' ? (
                  <Button 
                    size="lg"
                    onClick={handleBreakEnd}
                    className="gap-2"
                  >
                    <Play className="w-5 h-5" />
                    End Break
                  </Button>
                ) : null}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Today's Activity</CardTitle>
            </CardHeader>
            <CardContent>
              {clockStatus?.last_event ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-emerald-500" />
                      <span className="capitalize">{clockStatus.last_event.event_type?.replace('_', ' ')}</span>
                    </div>
                    <span className="text-sm text-muted-foreground">
                      {new Date(clockStatus.last_event.timestamp).toLocaleTimeString('en-GB')}
                    </span>
                  </div>
                  {clockStatus.last_event.location_name && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <MapPin className="w-4 h-4" />
                      {clockStatus.last_event.location_name}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  No activity today
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Schedule Tab */}
      {activeTab === 'schedule' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Weekly Schedule</CardTitle>
                <CardDescription>
                  Week of {new Date(selectedWeek).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="icon" onClick={() => navigateWeek(-1)}>
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <Button variant="outline" size="icon" onClick={() => navigateWeek(1)}>
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {shifts.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No shifts scheduled for this week</p>
              </div>
            ) : (
              <div className="space-y-3">
                {shifts.map((shift) => (
                  <div 
                    key={shift.shift_id}
                    className="flex items-center justify-between p-4 rounded-lg border"
                  >
                    <div>
                      <p className="font-medium">
                        {new Date(shift.date).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short' })}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(shift.start_time).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })} - 
                        {new Date(shift.end_time).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                      </p>
                      {shift.location && (
                        <p className="text-xs text-muted-foreground mt-1">
                          <MapPin className="w-3 h-3 inline mr-1" />
                          {shift.location}
                        </p>
                      )}
                    </div>
                    <Badge variant={shift.status === 'completed' ? 'default' : 'secondary'}>
                      {shift.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Timesheets Tab */}
      {activeTab === 'timesheets' && (
        <Card>
          <CardHeader>
            <CardTitle>My Timesheets</CardTitle>
            <CardDescription>View and submit weekly timesheets</CardDescription>
          </CardHeader>
          <CardContent>
            {timesheets.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No timesheets yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {timesheets.map((ts) => (
                  <div 
                    key={ts.timesheet_id}
                    className="flex items-center justify-between p-4 rounded-lg border"
                  >
                    <div>
                      <p className="font-medium">
                        Week of {new Date(ts.week_start_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                      </p>
                      <div className="flex gap-4 text-sm text-muted-foreground mt-1">
                        <span>Total: {ts.total_hours}h</span>
                        <span>Regular: {ts.regular_hours}h</span>
                        {ts.overtime_hours > 0 && <span className="text-amber-600">OT: {ts.overtime_hours}h</span>}
                      </div>
                    </div>
                    <Badge variant={
                      ts.status === 'approved' ? 'default' :
                      ts.status === 'submitted' ? 'secondary' :
                      ts.status === 'rejected' ? 'destructive' : 'outline'
                    }>
                      {ts.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Approvals Tab */}
      {activeTab === 'approvals' && (
        <Card>
          <CardHeader>
            <CardTitle>Pending Approvals</CardTitle>
            <CardDescription>Timesheets awaiting your approval</CardDescription>
          </CardHeader>
          <CardContent>
            {pendingTimesheets.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <CheckCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No pending approvals</p>
              </div>
            ) : (
              <div className="space-y-3">
                {pendingTimesheets.map((ts) => (
                  <div 
                    key={ts.timesheet_id}
                    className="flex items-center justify-between p-4 rounded-lg border"
                  >
                    <div>
                      <p className="font-medium">{ts.employee_name || 'Employee'}</p>
                      <p className="text-sm text-muted-foreground">
                        Week of {new Date(ts.week_start_date).toLocaleDateString('en-GB')} • {ts.total_hours}h total
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button 
                        size="sm" 
                        variant="outline"
                        className="text-red-600"
                      >
                        <XCircle className="w-4 h-4 mr-1" />
                        Reject
                      </Button>
                      <Button 
                        size="sm"
                        onClick={() => handleApproveTimesheet(ts.timesheet_id)}
                      >
                        <CheckCircle className="w-4 h-4 mr-1" />
                        Approve
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
