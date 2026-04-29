import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Progress } from '../ui/progress';
import { 
  Shield, 
  AlertTriangle, 
  Clock, 
  CheckCircle, 
  XCircle,
  Users,
  FileText,
  Bell,
  Calendar,
  ChevronRight,
  Search,
  RefreshCw,
  AlertCircle,
  ClipboardList
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function UKVICompliancePage() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState(null);
  const [checklist, setChecklist] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [dashboardRes, checklistRes, alertsRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/ukvi/dashboard`, { headers }),
        fetch(`${BACKEND_URL}/api/ukvi/reporting/checklist`, { headers }),
        fetch(`${BACKEND_URL}/api/ukvi/alerts?resolved=false`, { headers })
      ]);

      if (dashboardRes.ok) {
        setDashboard(await dashboardRes.json());
      }
      if (checklistRes.ok) {
        setChecklist(await checklistRes.json());
      }
      if (alertsRes.ok) {
        const alertData = await alertsRes.json();
        setAlerts(alertData.alerts || []);
      }
    } catch (error) {
      console.error('Error fetching UKVI data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const handleGenerateAlerts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${BACKEND_URL}/api/ukvi/alerts/generate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        fetchData();
      }
    } catch (error) {
      console.error('Error generating alerts:', error);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'compliant': return 'bg-emerald-500';
      case 'action_required': return 'bg-amber-500';
      case 'urgent': return 'bg-orange-500';
      case 'expired': return 'bg-rose-500';
      default: return 'bg-slate-500';
    }
  };

  const getSeverityBadge = (severity) => {
    switch (severity) {
      case 'critical':
        return <Badge variant="destructive">Critical</Badge>;
      case 'high':
        return <Badge className="bg-orange-500 hover:bg-orange-600">High</Badge>;
      case 'medium':
        return <Badge className="bg-amber-500 hover:bg-amber-600">Medium</Badge>;
      default:
        return <Badge variant="secondary">Low</Badge>;
    }
  };

  const getUrgencyBadge = (urgency) => {
    switch (urgency) {
      case 'overdue':
        return <Badge variant="destructive">Overdue</Badge>;
      case 'urgent':
        return <Badge className="bg-orange-500 hover:bg-orange-600">Urgent</Badge>;
      default:
        return <Badge variant="secondary">Normal</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">UKVI Compliance</h1>
          <p className="text-muted-foreground mt-1">
            UK Visas & Immigration sponsor compliance management
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={handleGenerateAlerts}>
            <Bell className="w-4 h-4 mr-2" />
            Check Alerts
          </Button>
          <Button variant="outline" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Disclaimer */}
      <Card className="border-amber-200 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800">
        <CardContent className="pt-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-amber-800 dark:text-amber-200">
              This dashboard assists with UKVI compliance record-keeping but does not constitute legal advice. 
              Sponsor compliance is the employer's legal responsibility.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <div className="flex gap-2 border-b pb-2">
        {['overview', 'reporting', 'alerts'].map((tab) => (
          <Button
            key={tab}
            variant={activeTab === tab ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab(tab)}
            className="capitalize"
            data-testid={`ukvi-tab-${tab}`}
          >
            {tab}
          </Button>
        ))}
      </div>

      {activeTab === 'overview' && dashboard && (
        <>
          {/* Overview Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Overall Score</p>
                    <p className="text-3xl font-bold">{Math.round(dashboard.overall_score)}%</p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                    <Shield className="w-6 h-6 text-primary" />
                  </div>
                </div>
                <Progress value={dashboard.overall_score} className="mt-3" />
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Sponsored Employees</p>
                    <p className="text-3xl font-bold">{dashboard.total_sponsored_employees}</p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                    <Users className="w-6 h-6 text-blue-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Active Alerts</p>
                    <p className="text-3xl font-bold">{dashboard.active_alerts?.length || 0}</p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                    <Bell className="w-6 h-6 text-amber-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Pending Reports</p>
                    <p className="text-3xl font-bold">{dashboard.pending_reportable_events?.length || 0}</p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                    <FileText className="w-6 h-6 text-purple-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Status Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Employee Status Breakdown</CardTitle>
              <CardDescription>UKVI compliance status across sponsored employees</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(dashboard.status_breakdown || {}).map(([status, count]) => (
                  <div key={status} className="flex items-center gap-3 p-4 rounded-lg bg-muted/50">
                    <div className={`w-3 h-3 rounded-full ${getStatusColor(status)}`} />
                    <div>
                      <p className="font-medium capitalize">{status.replace('_', ' ')}</p>
                      <p className="text-2xl font-bold">{count}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Employees at Risk */}
          {dashboard.employees_at_risk?.length > 0 && (
            <Card className="border-rose-200 dark:border-rose-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-rose-600">
                  <AlertTriangle className="w-5 h-5" />
                  Employees at Risk
                </CardTitle>
                <CardDescription>Immediate attention required</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {dashboard.employees_at_risk.map((emp) => (
                    <div 
                      key={emp.employee_id}
                      className="flex items-center justify-between p-4 rounded-lg bg-rose-50 dark:bg-rose-900/20 cursor-pointer hover:bg-rose-100 dark:hover:bg-rose-900/30"
                      onClick={() => navigate(`/employees/${emp.employee_id}`)}
                    >
                      <div>
                        <p className="font-medium">{emp.name}</p>
                        <p className="text-sm text-muted-foreground capitalize">
                          {emp.visa_type?.replace('_', ' ')} • {emp.issues_count} issue(s)
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className={`px-3 py-1 rounded text-white text-sm ${getStatusColor(emp.status)}`}>
                          {emp.score}%
                        </div>
                        <ChevronRight className="w-4 h-4" />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {activeTab === 'reporting' && checklist && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardList className="w-5 h-5" />
              UKVI Reporting Checklist
            </CardTitle>
            <CardDescription>
              Events must be reported to UKVI within 10 working days via the Sponsor Management System
            </CardDescription>
          </CardHeader>
          <CardContent>
            {checklist.checklist?.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <CheckCircle className="w-12 h-12 mx-auto mb-3 text-emerald-500" />
                <p>No pending reports</p>
              </div>
            ) : (
              <div className="space-y-3">
                {checklist.checklist.map((item) => (
                  <div 
                    key={item.event_id}
                    className="flex items-center justify-between p-4 rounded-lg border"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium">{item.employee_name}</p>
                        {getUrgencyBadge(item.urgency)}
                      </div>
                      <p className="text-sm text-muted-foreground capitalize">
                        {item.event_type.replace('_', ' ')} • {item.days_since_event} days ago
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {item.working_days_remaining > 0 
                          ? `${item.working_days_remaining} working days remaining`
                          : 'Report overdue!'
                        }
                      </p>
                    </div>
                    <Button variant="outline" size="sm">
                      Mark Reported
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'alerts' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="w-5 h-5" />
              Active Alerts
            </CardTitle>
            <CardDescription>Document expiry and compliance alerts</CardDescription>
          </CardHeader>
          <CardContent>
            {alerts.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <CheckCircle className="w-12 h-12 mx-auto mb-3 text-emerald-500" />
                <p>No active alerts</p>
              </div>
            ) : (
              <div className="space-y-3">
                {alerts.map((alert) => (
                  <div 
                    key={alert.alert_id}
                    className="flex items-center justify-between p-4 rounded-lg border"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium">{alert.title}</p>
                        {getSeverityBadge(alert.severity)}
                      </div>
                      <p className="text-sm text-muted-foreground">{alert.description}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {alert.action_required}
                      </p>
                    </div>
                    <Button variant="outline" size="sm">
                      Resolve
                    </Button>
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
