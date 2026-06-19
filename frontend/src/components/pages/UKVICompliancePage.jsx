import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Progress } from '../ui/progress';
import { toast } from 'sonner';
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
  ClipboardList,
  Play,
  Download,
  Eye,
  Loader2,
  CheckCircle2,
  XCircle as X
} from 'lucide-react';

import { useAuth } from '../../contexts/AuthContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function UKVICompliancePage() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [checklist, setChecklist] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  // Compliance Scanner state
  const [scannerStatus, setScannerStatus] = useState(null);
  const [scanLoading, setScanLoading] = useState(false);
  const [scanPreview, setScanPreview] = useState(null);
  const [exportLoading, setExportLoading] = useState(null);
  const [selectedScanId, setSelectedScanId] = useState(null);

  const fetchData = async () => {
    try {
      const token = token;
      const headers = { 'Authorization': `Bearer ${token}` };

      const [dashboardRes, checklistRes, alertsRes, scannerRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/ukvi/dashboard`, { headers }),
        fetch(`${BACKEND_URL}/api/ukvi/reporting/checklist`, { headers }),
        fetch(`${BACKEND_URL}/api/ukvi/alerts?resolved=false`, { headers }),
        fetch(`${BACKEND_URL}/api/ukvi/compliance/status`, { headers }),
      ]);

      if (dashboardRes.ok) setDashboard(await dashboardRes.json());
      if (checklistRes.ok) setChecklist(await checklistRes.json());
      if (alertsRes.ok) {
        const alertData = await alertsRes.json();
        setAlerts(alertData.alerts || []);
      }
      if (scannerRes.ok) setScannerStatus(await scannerRes.json());
    } catch (error) {
      console.error('Error fetching UKVI data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRunScan = async () => {
    setScanLoading(true);
    try {
      const token = token;
      const res = await fetch(`${BACKEND_URL}/api/ukvi/compliance/scans/run`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || 'Scan failed');
        return;
      }
      const data = await res.json();
      toast.success(`Scan complete — Score: ${data.overall_score}%`);
      setScannerStatus(null);
      setSelectedScanId(data.scan_id);
      if (data.preview) {
        setScanPreview(data.preview);
      } else {
        setScanPreview(null);
        await handleViewScan(data.scan_id);
      }
      fetchData();
    } catch (e) {
      toast.error('Scan failed — please try again');
    } finally {
      setScanLoading(false);
    }
  };

  const handleViewScan = async (scanId) => {
    setSelectedScanId(scanId);
    try {
      const token = token;
      const res = await fetch(`${BACKEND_URL}/api/ukvi/compliance/scans/${scanId}/preview`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        setScanPreview(await res.json());
      } else {
        toast.error('Could not load scan preview');
      }
    } catch (e) {
      toast.error('Failed to load scan preview');
    }
  };

  const handleExportReport = async (scanId, format) => {
    setExportLoading(format);
    try {
      const token = token;
      const res = await fetch(`${BACKEND_URL}/api/ukvi/compliance/scans/${scanId}/export?format=${format}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || 'Export failed');
        return;
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ukvi_compliance_${scanId.slice(0, 8)}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success(`${format.toUpperCase()} report downloaded`);
    } catch (e) {
      toast.error('Export failed');
    } finally {
      setExportLoading(null);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const handleResolveAlert = async (alertId, resolution) => {
    try {
      const token = token;
      const res = await fetch(`${BACKEND_URL}/api/ukvi/alerts/${alertId}/resolve`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution_note: resolution }),
      });
      if (res.ok) {
        toast.success('Alert resolved');
        fetchData();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to resolve alert');
      }
    } catch {
      toast.error('Error resolving alert');
    }
  };

  const handleUpdateAlertStatus = async (alertId, status) => {
    try {
      const token = token;
      const res = await fetch(`${BACKEND_URL}/api/ukvi/compliance/alerts/${alertId}`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (res.ok) {
        toast.success(`Alert marked as ${status.replace('_', ' ')}`);
        fetchData();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to update alert');
      }
    } catch {
      toast.error('Error updating alert');
    }
  };

  const handleGenerateAlerts = async () => {
    try {
      const token = token;
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
      <div className="flex gap-2 border-b pb-2 flex-wrap">
        {[
          { id: 'overview', label: 'Overview' },
          { id: 'scanner', label: 'Compliance Scanner' },
          { id: 'reporting', label: 'Reporting' },
          { id: 'alerts', label: 'Alerts' },
        ].map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab(tab.id)}
            data-testid={`ukvi-tab-${tab.id}`}
            className={activeTab === tab.id && tab.id === 'scanner' ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white' : ''}
          >
            {tab.id === 'scanner' && <Shield className="w-3 h-3 mr-1.5" />}
            {tab.label}
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

      {/* ======================================================= */}
      {/* COMPLIANCE SCANNER TAB                                  */}
      {/* ======================================================= */}
      {activeTab === 'scanner' && (
        <div className="space-y-6">
          {/* Scanner Header */}
          <Card className="border-purple-200 dark:border-purple-800">
            <CardHeader>
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Shield className="w-5 h-5 text-purple-600" />
                    UKVI Compliance Scanner
                  </CardTitle>
                  <CardDescription>
                    Automated compliance scan across all employees — checks RTW, visa, CoS, salary thresholds, and reporting obligations.
                  </CardDescription>
                </div>
                {scannerStatus?.quota && (
                  <div className="text-sm text-right">
                    <p className="font-semibold text-purple-700 dark:text-purple-300">
                      {scannerStatus.quota.scans_used} / {scannerStatus.quota.scans_limit} scans used
                    </p>
                    <p className="text-muted-foreground text-xs">
                      Resets {scannerStatus.quota.period_end}
                    </p>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4 flex-wrap">
                <Button
                  className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white"
                  onClick={handleRunScan}
                  disabled={scanLoading || (scannerStatus?.quota?.quota_exceeded)}
                >
                  {scanLoading ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Running scan…</>
                  ) : (
                    <><Play className="w-4 h-4 mr-2" /> Run Compliance Scan</>
                  )}
                </Button>
                {scannerStatus?.quota?.quota_exceeded && (
                  <p className="text-sm text-amber-600">
                    Monthly quota reached — resets {scannerStatus.quota.period_end}
                  </p>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                Scan preview is free. PDF/DOCX report download requires Professional or Enterprise plan.
              </p>
            </CardContent>
          </Card>

          {/* Scan Preview */}
          {scanPreview && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Eye className="w-4 h-4 text-indigo-600" />
                    Scan Results — {scanPreview.scan_id?.slice(0, 12)}
                  </CardTitle>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={exportLoading === 'pdf'}
                      onClick={() => handleExportReport(scanPreview.scan_id, 'pdf')}
                    >
                      {exportLoading === 'pdf' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4 mr-1" />}
                      PDF
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={exportLoading === 'docx'}
                      onClick={() => handleExportReport(scanPreview.scan_id, 'docx')}
                    >
                      {exportLoading === 'docx' ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4 mr-1" />}
                      DOCX
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Score */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { label: 'Overall Score', value: `${scanPreview.overall_score}%`, color: scanPreview.overall_score >= 90 ? 'text-emerald-600' : scanPreview.overall_score >= 75 ? 'text-amber-600' : 'text-red-600' },
                    { label: 'Risk Level', value: (scanPreview.risk_level || '').replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()), color: '' },
                    { label: 'Employees Scanned', value: scanPreview.summary?.total_employees ?? '—', color: '' },
                    { label: 'Issues Found', value: scanPreview.summary?.failed ?? 0, color: 'text-red-600' },
                  ].map((s, i) => (
                    <div key={i} className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/30 border text-center">
                      <p className="text-xs text-muted-foreground">{s.label}</p>
                      <p className={`font-bold text-lg ${s.color}`}>{s.value}</p>
                    </div>
                  ))}
                </div>

                {/* By Category */}
                {scanPreview.by_category && Object.keys(scanPreview.by_category).length > 0 && (
                  <div>
                    <p className="text-sm font-semibold mb-2">By Category</p>
                    <div className="space-y-2">
                      {Object.entries(scanPreview.by_category).map(([cat, counts]) => (
                        <div key={cat} className="flex items-center gap-3 text-sm">
                          <span className="w-36 capitalize text-muted-foreground">{cat.replace('_', ' ')}</span>
                          <span className="text-emerald-600 text-xs">{counts.passed} passed</span>
                          {counts.failed > 0 && <span className="text-red-600 text-xs">{counts.failed} failed</span>}
                          {counts.warnings > 0 && <span className="text-amber-600 text-xs">{counts.warnings} warnings</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Flagged Employees */}
                {scanPreview.employee_details?.filter(e => e.fail_count > 0 || e.warning_count > 0).length > 0 && (
                  <div>
                    <p className="text-sm font-semibold mb-2">Employees with Issues</p>
                    <div className="space-y-2 max-h-80 overflow-y-auto">
                      {scanPreview.employee_details
                        .filter(e => e.fail_count > 0 || e.warning_count > 0)
                        .map(emp => (
                          <div key={emp.employee_id} className="p-3 rounded-lg border bg-rose-50 dark:bg-rose-950/20">
                            <div className="flex items-center justify-between mb-1">
                              <p className="font-medium text-sm">{emp.employee_name}</p>
                              <div className="flex gap-1">
                                {emp.fail_count > 0 && <Badge variant="destructive" className="text-xs">{emp.fail_count} issue{emp.fail_count !== 1 ? 's' : ''}</Badge>}
                                {emp.warning_count > 0 && <Badge className="bg-amber-500 text-white text-xs">{emp.warning_count} warning{emp.warning_count !== 1 ? 's' : ''}</Badge>}
                              </div>
                            </div>
                            <ul className="space-y-0.5">
                              {emp.checks.filter(c => c.status !== 'pass').map((chk, i) => (
                                <li key={i} className="text-xs text-muted-foreground flex items-start gap-1">
                                  {chk.status === 'fail'
                                    ? <X className="w-3 h-3 text-red-500 flex-shrink-0 mt-0.5" />
                                    : <AlertTriangle className="w-3 h-3 text-amber-500 flex-shrink-0 mt-0.5" />}
                                  [{chk.rule_code}] {chk.message}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {scanPreview.employee_details?.every(e => e.fail_count === 0 && e.warning_count === 0) && (
                  <div className="text-center py-6">
                    <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-2" />
                    <p className="font-semibold text-emerald-700">All checks passed</p>
                    <p className="text-sm text-muted-foreground">No compliance issues found for any employee.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Recent Scans */}
          {scannerStatus?.recent_scans?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Recent Scans</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {scannerStatus.recent_scans.map((scan) => (
                    <div
                      key={scan.scan_id}
                      className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent/30 cursor-pointer"
                      onClick={() => handleViewScan(scan.scan_id)}
                    >
                      <div>
                        <p className="text-sm font-medium">{scan.scan_id?.slice(0, 16)}</p>
                        <p className="text-xs text-muted-foreground">
                          {scan.created_at ? new Date(scan.created_at).toLocaleString() : '—'}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {scan.overall_score !== undefined && (
                          <Badge
                            className={
                              scan.overall_score >= 90 ? 'bg-emerald-600 text-white' :
                              scan.overall_score >= 75 ? 'bg-amber-500 text-white' :
                              'bg-red-600 text-white'
                            }
                          >
                            {scan.overall_score}%
                          </Badge>
                        )}
                        <Eye className="w-4 h-4 text-muted-foreground" />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
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
                    className="flex items-start justify-between p-4 rounded-lg border gap-4"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <p className="font-medium">{alert.title}</p>
                        {getSeverityBadge(alert.severity)}
                        {alert.employee_name && (
                          <span className="text-xs text-muted-foreground">— {alert.employee_name}</span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">{alert.description}</p>
                      {alert.rule_code && (
                        <p className="text-xs text-muted-foreground mt-0.5">Rule: {alert.rule_code}</p>
                      )}
                    </div>
                    <div className="flex flex-col gap-1 flex-shrink-0">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleResolveAlert(alert.alert_id, `Resolved via UKVI dashboard by compliance team`)}
                      >
                        Resolve
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs text-muted-foreground"
                        onClick={() => handleUpdateAlertStatus(alert.alert_id, 'dismissed')}
                      >
                        Dismiss
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
