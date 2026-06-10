import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { Badge } from '../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../ui/dialog';
import { toast } from 'sonner';
import {
  FileCheck, Send, CheckCircle, XCircle, AlertCircle,
  Clock, FileText, RefreshCw, Shield, ArrowRight,
  Building2, ChevronRight, Settings, Lock, ChevronUp,
  Eye, EyeOff, Save, AlertTriangle
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const GO_LIVE_CHECKLIST_LABELS = {
  sandbox_fps_submitted: 'Successfully submitted at least one test FPS in sandbox',
  sandbox_eps_submitted: 'Successfully submitted at least one test EPS in sandbox',
  gateway_credentials_configured: 'HMRC Government Gateway credentials configured',
  employer_paye_ref_verified: 'Employer PAYE reference verified with HMRC',
  accounts_office_ref_verified: 'Accounts Office reference confirmed',
  employer_address_complete: 'Employer registered address matches HMRC records',
  employee_data_reviewed: 'All active employee NI numbers and tax codes verified',
  tax_codes_verified: 'Starting tax codes assigned from P45/HMRC coding notices',
  bank_details_encrypted: 'Employee bank details encrypted at rest',
  ni_numbers_verified: 'All NI numbers validated (format and uniqueness)',
  payroll_periods_correct: 'Payroll periods and frequencies confirmed',
  fps_timing_understood: 'FPS on-or-before rule understood and scheduled',
  eps_procedure_understood: 'EPS procedure confirmed (for nil payment months)',
  data_backup_confirmed: 'Payroll data backup and recovery tested',
  team_training_complete: 'Payroll team trained on RTI submission workflow',
};

export default function HMRCDashboard() {
  const { token } = useAuth();
  const [submissions, setSubmissions] = useState([]);
  const [payRuns, setPayRuns] = useState([]);
  const [selectedPayRun, setSelectedPayRun] = useState(null);
  const [healthCheck, setHealthCheck] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // RTI config state
  const [rtiConfig, setRtiConfig] = useState(null);
  const [showRtiConfig, setShowRtiConfig] = useState(false);
  const [rtiConfigSaving, setRtiConfigSaving] = useState(false);
  const [rtiConfigForm, setRtiConfigForm] = useState({ gateway_user_id: '', gateway_password: '', sender_id: '' });
  const [showGatewayPassword, setShowGatewayPassword] = useState(false);

  // FPS approval gate state
  const [fpsApproveDialogOpen, setFpsApproveDialogOpen] = useState(false);
  const [fpsPendingPayrunId, setFpsPendingPayrunId] = useState(null);
  const [fpsState, setFpsState] = useState('idle'); // idle | validated | prepared | approved | submitted

  // EPS state
  const [epsReason, setEpsReason] = useState('');
  const [epsData, setEpsData] = useState({
    no_payment_period: '', smp_recovered: '', spp_recovered: '',
    sap_recovered: '', employment_allowance: false, final_submission: false,
  });
  const [epsSubmitting, setEpsSubmitting] = useState(false);
  const [epsApproveDialogOpen, setEpsApproveDialogOpen] = useState(false);

  const EPS_REASONS = [
    { value: 'no_payment', label: 'No payment to employees this period' },
    { value: 'smp_recovery', label: 'Statutory Maternity Pay recovery' },
    { value: 'spp_recovery', label: 'Statutory Paternity Pay recovery' },
    { value: 'sap_recovery', label: 'Statutory Adoption Pay recovery' },
    { value: 'employment_allowance', label: 'Employment Allowance claim' },
    { value: 'period_of_inactivity', label: 'Period of inactivity / no employees' },
    { value: 'final_submission', label: 'Final submission / PAYE scheme closure' },
  ];

  useEffect(() => {
    fetchData();
  }, [token]);

  const fetchData = async () => {
    if (!token) return;

    try {
      setLoading(true);
      const headers = { 'Authorization': `Bearer ${token}` };

      const [subsRes, runsRes, rtiRes] = await Promise.all([
        fetch(`${API_URL}/api/hmrc/submissions`, { headers }),
        fetch(`${API_URL}/api/payroll/runs`, { headers }),
        fetch(`${API_URL}/api/hmrc/rti-config`, { headers }),
      ]);

      if (subsRes.ok) setSubmissions(await subsRes.json());
      if (runsRes.ok) {
        const runs = await runsRes.json();
        setPayRuns(runs.filter(r => r.status === 'approved' || r.status === 'paid'));
      }
      if (rtiRes.ok) {
        const cfg = await rtiRes.json();
        setRtiConfig(cfg);
        setRtiConfigForm({ gateway_user_id: cfg.gateway_user_id || '', gateway_password: '', sender_id: cfg.sender_id || '' });
      }
    } catch (error) {
      console.error('Error fetching HMRC data:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveRtiConfig = async () => {
    setRtiConfigSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/hmrc/rti-config`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(rtiConfigForm),
      });
      const data = await res.json();
      if (res.ok) {
        setRtiConfig(data);
        toast.success('RTI configuration saved');
      } else {
        toast.error(data.detail || 'Failed to save RTI config');
      }
    } catch {
      toast.error('Error saving RTI config');
    } finally {
      setRtiConfigSaving(false);
    }
  };

  const toggleChecklistItem = async (itemKey) => {
    try {
      const res = await fetch(`${API_URL}/api/hmrc/rti-config/checklist/${itemKey}`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setRtiConfig(prev => ({ ...prev, go_live_checklist: data.go_live_checklist }));
      } else {
        toast.error('Failed to update checklist');
      }
    } catch {
      toast.error('Error updating checklist');
    }
  };

  const testConnection = async () => {
    setRtiConfigSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/hmrc/rti-config/test-connection`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.passed) {
        toast.success(data.message);
      } else {
        data.issues.forEach(i => toast.error(`${i.field}: ${i.message}`));
      }
    } catch {
      toast.error('Error running connection test');
    } finally {
      setRtiConfigSaving(false);
    }
  };

  const switchToProduction = async () => {
    const checklist = rtiConfig?.go_live_checklist || {};
    const incompleteRequired = Object.keys(GO_LIVE_CHECKLIST_LABELS).filter(k => !checklist[k]);
    if (incompleteRequired.length > 0) {
      toast.error(`Complete all ${incompleteRequired.length} checklist items before going live`);
      setShowRtiConfig(true);
      return;
    }
    setRtiConfigSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/hmrc/rti-config`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ rti_mode: 'production' }),
      });
      if (res.ok) {
        const data = await res.json();
        setRtiConfig(data);
        toast.success('Switched to production mode');
      } else {
        const data = await res.json();
        toast.error(data.detail || 'Cannot switch to production');
      }
    } catch {
      toast.error('Error switching mode');
    } finally {
      setRtiConfigSaving(false);
    }
  };

  const runHealthCheck = async (payrunId) => {
    try {
      const response = await fetch(`${API_URL}/api/hmrc/health-check/${payrunId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const result = await response.json();
        setHealthCheck(result);
        return result;
      } else {
        toast.error('Health check failed');
        return null;
      }
    } catch (error) {
      toast.error('Error running health check');
      return null;
    }
  };

  const validatePayRun = async (payrunId) => {
    try {
      const response = await fetch(`${API_URL}/api/hmrc/validate/${payrunId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const result = await response.json();
        setValidationResult(result);
        return result;
      } else {
        toast.error('Validation failed');
        return null;
      }
    } catch (error) {
      toast.error('Error validating pay run');
      return null;
    }
  };

  const prepareFPS = async (payrunId) => {
    // Run health check + validate, then open approval dialog
    const health = await runHealthCheck(payrunId);
    if (health && !health.can_proceed) {
      toast.error('Fix critical issues before preparing FPS');
      return;
    }
    const validation = await validatePayRun(payrunId);
    if (validation && !validation.valid) {
      toast.error('FPS validation failed. Fix errors before approving.');
      return;
    }
    setFpsState('prepared');
    setFpsPendingPayrunId(payrunId);
    setFpsApproveDialogOpen(true);
  };

  const submitFPS = async (payrunId) => {
    setFpsApproveDialogOpen(false);
    setSubmitting(true);
    setFpsState('submitted');
    try {
      const isProduction = rtiConfig?.rti_mode === 'production';
      const response = await fetch(`${API_URL}/api/hmrc/fps/submit`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          payrun_id: payrunId,
          submission_type: 'FPS',
          test_mode: !isProduction,
        })
      });

      const result = await response.json();
      if (result.success) {
        setFpsState('accepted');
        toast.success(`FPS submitted successfully (${isProduction ? 'LIVE' : 'Sandbox'})`);
        fetchData();
      } else if (result.errors) {
        setFpsState('idle');
        toast.error(`Submission failed: ${result.errors.length} validation errors`);
        setValidationResult(result);
      } else {
        setFpsState('idle');
        toast.error(result.error || 'Submission failed');
      }
    } catch {
      setFpsState('idle');
      toast.error('Error submitting FPS');
    } finally {
      setSubmitting(false);
    }
  };

  const submitEPS = async () => {
    if (!epsReason) { toast.error('Select an EPS reason first'); return; }
    setEpsApproveDialogOpen(false);
    setEpsSubmitting(true);
    try {
      const isProduction = rtiConfig?.rti_mode === 'production';
      const payload = {
        eps_reason: epsReason,
        test_mode: !isProduction,
        no_payment_period: epsData.no_payment_period || null,
        smp_recovered: parseFloat(epsData.smp_recovered) || 0,
        spp_recovered: parseFloat(epsData.spp_recovered) || 0,
        sap_recovered: parseFloat(epsData.sap_recovered) || 0,
        employment_allowance: epsData.employment_allowance,
        final_submission: epsData.final_submission,
      };
      const res = await fetch(`${API_URL}/api/hmrc/eps/submit`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await res.json();
      if (res.ok) {
        toast.success(`EPS submitted (${isProduction ? 'LIVE' : 'Sandbox'})`);
        fetchData();
        setEpsReason('');
      } else {
        toast.error(result.detail || 'EPS submission failed');
      }
    } catch {
      toast.error('Error submitting EPS');
    } finally {
      setEpsSubmitting(false);
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      draft: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
      validating: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      validated: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      submitted: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
      accepted: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      rejected: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    };
    
    const icons = {
      draft: <Clock className="h-3 w-3 mr-1" />,
      validating: <RefreshCw className="h-3 w-3 mr-1 animate-spin" />,
      validated: <CheckCircle className="h-3 w-3 mr-1" />,
      submitted: <Send className="h-3 w-3 mr-1" />,
      accepted: <CheckCircle className="h-3 w-3 mr-1" />,
      rejected: <XCircle className="h-3 w-3 mr-1" />,
      error: <AlertCircle className="h-3 w-3 mr-1" />
    };

    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${styles[status] || styles.draft}`}>
        {icons[status]}
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'warning':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-blue-500" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="hmrc-dashboard">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Building2 className="h-7 w-7" />
            HMRC RTI Submissions
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Real Time Information submissions for Full Payment (FPS) and Employer Payment Summary (EPS)
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowRtiConfig(v => !v)}>
            <Settings className="h-4 w-4 mr-1" /> RTI Config
          </Button>
          <Button variant="outline" onClick={fetchData}>
            <RefreshCw className="h-4 w-4 mr-2" /> Refresh
          </Button>
        </div>
      </div>

      {/* RTI Mode Banner */}
      {rtiConfig?.rti_mode === 'production' ? (
        <Alert className="bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800">
          <Shield className="h-4 w-4 text-green-600" />
          <AlertTitle className="text-green-800 dark:text-green-200">Production Mode Active</AlertTitle>
          <AlertDescription className="text-green-700 dark:text-green-300">
            RTI submissions will be sent to HMRC live systems. Ensure all data is accurate before submitting.
          </AlertDescription>
        </Alert>
      ) : (
        <Alert className="bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800">
          <Shield className="h-4 w-4 text-amber-600" />
          <AlertTitle className="text-amber-800 dark:text-amber-200">Sandbox Mode Active</AlertTitle>
          <AlertDescription className="text-amber-700 dark:text-amber-300 flex items-center justify-between flex-wrap gap-2">
            <span>All submissions are sent to HMRC's test environment. Complete the go-live checklist to switch to production.</span>
            <Button variant="outline" size="sm" className="border-amber-400 text-amber-700" onClick={() => setShowRtiConfig(v => !v)}>
              <Settings className="h-3 w-3 mr-1" /> Configure RTI
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* RTI Configuration Panel */}
      {showRtiConfig && (
        <Card className="border-indigo-200">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-base">
                <Settings className="h-5 w-5 text-indigo-600" />
                HMRC RTI Configuration
              </span>
              <Button variant="ghost" size="sm" onClick={() => setShowRtiConfig(false)}>
                <ChevronUp className="h-4 w-4" />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Gateway credentials */}
            <div className="space-y-3">
              <h4 className="font-medium text-sm">Government Gateway Credentials</h4>
              <p className="text-xs text-muted-foreground">Never share credentials via chat, email, or source code. Enter them only here.</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Gateway User ID</label>
                  <input
                    className="mt-1 w-full border rounded px-3 py-2 text-sm bg-background"
                    value={rtiConfigForm.gateway_user_id}
                    onChange={e => setRtiConfigForm(f => ({ ...f, gateway_user_id: e.target.value }))}
                    placeholder="12-digit ID"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground">
                    Gateway Password {rtiConfig?.gateway_password_set && <Badge className="ml-1 text-xs bg-emerald-100 text-emerald-700">Set</Badge>}
                  </label>
                  <div className="relative mt-1">
                    <input
                      type={showGatewayPassword ? 'text' : 'password'}
                      className="w-full border rounded px-3 py-2 text-sm bg-background pr-8"
                      value={rtiConfigForm.gateway_password}
                      onChange={e => setRtiConfigForm(f => ({ ...f, gateway_password: e.target.value }))}
                      placeholder={rtiConfig?.gateway_password_set ? '(leave blank to keep existing)' : 'Enter password'}
                    />
                    <button type="button" className="absolute right-2 top-2.5 text-muted-foreground" onClick={() => setShowGatewayPassword(v => !v)}>
                      {showGatewayPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Sender ID (optional)</label>
                  <input
                    className="mt-1 w-full border rounded px-3 py-2 text-sm bg-background"
                    value={rtiConfigForm.sender_id}
                    onChange={e => setRtiConfigForm(f => ({ ...f, sender_id: e.target.value }))}
                    placeholder="Agent/bureau sender ID"
                  />
                </div>
              </div>
              <div className="flex gap-2 flex-wrap">
                <Button size="sm" onClick={saveRtiConfig} disabled={rtiConfigSaving}>
                  <Save className="h-3 w-3 mr-1" /> {rtiConfigSaving ? 'Saving…' : 'Save Credentials'}
                </Button>
                <Button size="sm" variant="outline" onClick={testConnection} disabled={rtiConfigSaving}>
                  <CheckCircle className="h-3 w-3 mr-1" /> Test Connection
                </Button>
              </div>
            </div>

            {/* Go-live checklist */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-medium text-sm flex items-center gap-2">
                  <Lock className="h-4 w-4 text-rose-500" />
                  Production Go-Live Checklist
                </h4>
                {rtiConfig?.rti_mode === 'sandbox' && (
                  <Button
                    size="sm"
                    onClick={switchToProduction}
                    disabled={rtiConfigSaving}
                    className="bg-rose-600 hover:bg-rose-700 text-white"
                  >
                    Switch to Production
                  </Button>
                )}
              </div>
              <p className="text-xs text-muted-foreground">All items must be checked before production mode can be enabled.</p>
              <div className="space-y-2">
                {Object.entries(GO_LIVE_CHECKLIST_LABELS).map(([key, label]) => {
                  const checked = !!(rtiConfig?.go_live_checklist?.[key]);
                  return (
                    <label key={key} className="flex items-start gap-3 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-900/30 cursor-pointer">
                      <input
                        type="checkbox"
                        className="mt-0.5 h-4 w-4 rounded border-gray-300 text-indigo-600"
                        checked={checked}
                        onChange={() => toggleChecklistItem(key)}
                      />
                      <span className={`text-sm ${checked ? 'line-through text-muted-foreground' : ''}`}>{label}</span>
                      {checked && <CheckCircle className="h-4 w-4 text-emerald-500 flex-shrink-0 ml-auto" />}
                    </label>
                  );
                })}
              </div>
              <div className="pt-2">
                {(() => {
                  const checklist = rtiConfig?.go_live_checklist || {};
                  const done = Object.keys(GO_LIVE_CHECKLIST_LABELS).filter(k => checklist[k]).length;
                  const total = Object.keys(GO_LIVE_CHECKLIST_LABELS).length;
                  const pct = Math.round((done / total) * 100);
                  return (
                    <div>
                      <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                        <span>Progress: {done}/{total} items</span>
                        <span>{pct}%</span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800">
                        <div className="h-2 rounded-full bg-indigo-500 transition-all" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* FPS Approval Dialog */}
      <Dialog open={fpsApproveDialogOpen} onOpenChange={setFpsApproveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-indigo-600" />
              Approve FPS Submission
            </DialogTitle>
            <DialogDescription>
              You are about to submit a Full Payment Submission to HMRC{rtiConfig?.rti_mode === 'production' ? ' in LIVE production mode' : ' in Sandbox/Test mode'}. This action is recorded with your user ID and timestamp.
            </DialogDescription>
          </DialogHeader>
          {selectedPayRun && (
            <div className="rounded-lg bg-muted/50 p-4 space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">Pay period</span><span className="font-medium">{selectedPayRun.period_start} – {selectedPayRun.period_end}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Employees</span><span className="font-medium">{selectedPayRun.employee_count}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Total gross</span><span className="font-medium">£{selectedPayRun.total_gross?.toLocaleString()}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Mode</span><span className={`font-medium ${rtiConfig?.rti_mode === 'production' ? 'text-rose-600' : 'text-amber-600'}`}>{rtiConfig?.rti_mode === 'production' ? 'LIVE PRODUCTION' : 'Sandbox / Test'}</span></div>
            </div>
          )}
          {rtiConfig?.rti_mode === 'production' && (
            <Alert className="border-rose-200 bg-rose-50 dark:bg-rose-950/20">
              <AlertTriangle className="h-4 w-4 text-rose-600" />
              <AlertDescription className="text-rose-700 dark:text-rose-300 text-sm">
                This will submit REAL payroll data to HMRC live systems. Ensure all data is accurate.
              </AlertDescription>
            </Alert>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setFpsApproveDialogOpen(false)}>Cancel</Button>
            <Button className="bg-indigo-600 hover:bg-indigo-700" onClick={() => submitFPS(fpsPendingPayrunId)} data-testid="approve-submit-fps-btn">
              <Send className="w-4 h-4 mr-2" /> Confirm & Submit FPS
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* EPS Approval Dialog */}
      <Dialog open={epsApproveDialogOpen} onOpenChange={setEpsApproveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-indigo-600" />
              Approve EPS Submission
            </DialogTitle>
            <DialogDescription>
              You are about to submit an Employer Payment Summary to HMRC. This action is recorded.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-lg bg-muted/50 p-4 text-sm">
            <div className="flex justify-between"><span className="text-muted-foreground">Reason</span><span className="font-medium">{EPS_REASONS.find(r => r.value === epsReason)?.label}</span></div>
            <div className="flex justify-between mt-1"><span className="text-muted-foreground">Mode</span><span className={`font-medium ${rtiConfig?.rti_mode === 'production' ? 'text-rose-600' : 'text-amber-600'}`}>{rtiConfig?.rti_mode === 'production' ? 'LIVE PRODUCTION' : 'Sandbox / Test'}</span></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEpsApproveDialogOpen(false)}>Cancel</Button>
            <Button className="bg-indigo-600 hover:bg-indigo-700" onClick={submitEPS} disabled={epsSubmitting}>
              <Send className="w-4 h-4 mr-2" /> Confirm & Submit EPS
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* FPS Workflow */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pay Run Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Select Pay Run (FPS)
            </CardTitle>
            <CardDescription>Only approved pay runs can be submitted to HMRC</CardDescription>
          </CardHeader>
          <CardContent>
            {payRuns.length > 0 ? (
              <div className="space-y-3">
                {payRuns.map((run) => (
                  <div
                    key={run.payrun_id}
                    className={`p-4 border rounded-lg cursor-pointer transition-all ${
                      selectedPayRun?.payrun_id === run.payrun_id
                        ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-indigo-300'
                    }`}
                    onClick={() => {
                      setSelectedPayRun(run);
                      setHealthCheck(null);
                      setValidationResult(null);
                      setFpsState('idle');
                    }}
                    data-testid={`payrun-${run.payrun_id}`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{run.period_start} – {run.period_end}</p>
                        <p className="text-sm text-muted-foreground">{run.employee_count} employees · £{run.total_gross?.toLocaleString()} gross</p>
                      </div>
                      <div className="flex items-center gap-2">
                        {run.rti_submitted && (
                          <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">RTI Submitted</Badge>
                        )}
                        <ChevronRight className="h-5 w-5 text-muted-foreground" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No approved pay runs available</p>
                <p className="text-sm mt-2">Approve a pay run first to submit to HMRC</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* FPS Submission Steps */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Send className="h-5 w-5" />
              FPS Workflow
            </CardTitle>
            <CardDescription>
              {selectedPayRun
                ? `Pay run: ${selectedPayRun.period_start} – ${selectedPayRun.period_end}`
                : 'Select a pay run to begin'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {selectedPayRun ? (
              <div className="space-y-3">
                {/* State indicator */}
                {fpsState !== 'idle' && (
                  <div className="flex items-center gap-2 p-2 rounded bg-indigo-50 dark:bg-indigo-950/20 text-sm text-indigo-700 dark:text-indigo-300">
                    <Shield className="w-4 h-4" />
                    FPS state: <strong>{fpsState.replace('_', ' ')}</strong>
                  </div>
                )}

                {/* Step 1: Health Check */}
                <div className="p-3 bg-muted/30 rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center text-xs font-medium">1</span>
                    <span className="text-sm font-medium">Health Check</span>
                    {healthCheck?.overall_status === 'pass' && <CheckCircle className="w-4 h-4 text-emerald-500" />}
                    {healthCheck?.overall_status === 'fail' && <XCircle className="w-4 h-4 text-red-500" />}
                  </div>
                  <Button variant="outline" size="sm" onClick={() => runHealthCheck(selectedPayRun.payrun_id)} data-testid="run-health-check-btn">
                    <FileCheck className="h-4 w-4 mr-1" /> Run
                  </Button>
                </div>

                {/* Step 2: Validate */}
                <div className="p-3 bg-muted/30 rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center text-xs font-medium">2</span>
                    <span className="text-sm font-medium">Validate</span>
                    {validationResult?.valid && <CheckCircle className="w-4 h-4 text-emerald-500" />}
                    {validationResult && !validationResult.valid && <XCircle className="w-4 h-4 text-red-500" />}
                  </div>
                  <Button variant="outline" size="sm" onClick={() => validatePayRun(selectedPayRun.payrun_id)} data-testid="validate-btn">
                    <CheckCircle className="h-4 w-4 mr-1" /> Validate
                  </Button>
                </div>

                {/* Step 3: Prepare & Approve */}
                <div className="p-3 bg-muted/30 rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center text-xs font-medium">3</span>
                    <span className="text-sm font-medium">Prepare & Approve</span>
                    {fpsState === 'prepared' && <CheckCircle className="w-4 h-4 text-emerald-500" />}
                  </div>
                  <Button
                    variant="outline" size="sm"
                    onClick={() => prepareFPS(selectedPayRun.payrun_id)}
                    disabled={submitting || (fpsState === 'accepted')}
                    data-testid="prepare-fps-btn"
                  >
                    <Shield className="h-4 w-4 mr-1" /> Prepare
                  </Button>
                </div>

                {/* Step 4: Submit */}
                <div className="p-3 bg-muted/30 rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center text-xs font-medium">4</span>
                    <span className="text-sm font-medium">Submit FPS</span>
                    {fpsState === 'accepted' && <Badge className="bg-emerald-100 text-emerald-700">Accepted</Badge>}
                    {fpsState === 'submitted' && <Badge className="bg-indigo-100 text-indigo-700">Submitted</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground">Via approval step</p>
                </div>

                {selectedPayRun.rti_submitted && (
                  <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/20 text-sm text-emerald-700 dark:text-emerald-300 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" /> This pay run has already been submitted to HMRC.
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <ArrowRight className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Select a pay run to see submission options</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* EPS Workflow */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Employer Payment Summary (EPS)
          </CardTitle>
          <CardDescription>Submit EPS only when there is a valid EPS reason. Do not submit every month automatically.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>EPS Reason <span className="text-rose-500">*</span></Label>
              <Select value={epsReason} onValueChange={setEpsReason}>
                <SelectTrigger><SelectValue placeholder="Select a reason" /></SelectTrigger>
                <SelectContent>
                  {EPS_REASONS.map(r => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {(epsReason === 'no_payment' || epsReason === 'period_of_inactivity') && (
              <div className="space-y-2">
                <Label>Tax Period (e.g. 2025-04)</Label>
                <Input value={epsData.no_payment_period} onChange={e => setEpsData(d => ({ ...d, no_payment_period: e.target.value }))} placeholder="YYYY-MM" />
              </div>
            )}
            {epsReason === 'smp_recovery' && (
              <div className="space-y-2">
                <Label>SMP Amount to Recover (£)</Label>
                <Input type="number" value={epsData.smp_recovered} onChange={e => setEpsData(d => ({ ...d, smp_recovered: e.target.value }))} />
              </div>
            )}
            {epsReason === 'spp_recovery' && (
              <div className="space-y-2">
                <Label>SPP Amount to Recover (£)</Label>
                <Input type="number" value={epsData.spp_recovered} onChange={e => setEpsData(d => ({ ...d, spp_recovered: e.target.value }))} />
              </div>
            )}
            {epsReason === 'sap_recovery' && (
              <div className="space-y-2">
                <Label>SAP Amount to Recover (£)</Label>
                <Input type="number" value={epsData.sap_recovered} onChange={e => setEpsData(d => ({ ...d, sap_recovered: e.target.value }))} />
              </div>
            )}
          </div>
          {epsReason === 'final_submission' && (
            <Alert className="border-rose-200 bg-rose-50 dark:bg-rose-950/20">
              <AlertTriangle className="h-4 w-4 text-rose-600" />
              <AlertDescription className="text-rose-700 dark:text-rose-300 text-sm">
                Final submission closes the PAYE scheme. Only proceed if you intend to cease this PAYE scheme.
              </AlertDescription>
            </Alert>
          )}
          <div className="flex justify-end">
            <Button
              className="bg-indigo-600 hover:bg-indigo-700"
              disabled={!epsReason || epsSubmitting}
              onClick={() => setEpsApproveDialogOpen(true)}
              data-testid="prepare-eps-btn"
            >
              {epsSubmitting ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Shield className="w-4 h-4 mr-2" />}
              Prepare & Approve EPS
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Health Check Results */}
      {healthCheck && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileCheck className="h-5 w-5" />
              Health Check Results
              <span className={`ml-2 px-2 py-1 rounded text-xs font-medium ${
                healthCheck.overall_status === 'pass' ? 'bg-green-100 text-green-800' :
                healthCheck.overall_status === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                Score: {healthCheck.score}%
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {healthCheck.issues.length > 0 ? (
              <div className="space-y-3">
                {healthCheck.issues.map((issue, idx) => (
                  <div 
                    key={idx} 
                    className={`p-4 rounded-lg border ${
                      issue.severity === 'critical' ? 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20' :
                      issue.severity === 'warning' ? 'border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20' :
                      'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {getSeverityIcon(issue.severity)}
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-gray-900 dark:text-white">{issue.title}</span>
                          <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">
                            {issue.category}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-300">{issue.description}</p>
                        {issue.employee_name && (
                          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            Employee: {issue.employee_name}
                          </p>
                        )}
                        <p className="text-sm text-indigo-600 dark:text-indigo-400 mt-2">
                          ➜ {issue.action_required}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-green-600">
                <CheckCircle className="h-12 w-12 mx-auto mb-2" />
                <p className="font-medium">All checks passed!</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Ready to submit to HMRC</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Validation Results */}
      {validationResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              Validation Results
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <p className="text-sm text-gray-500 dark:text-gray-400">Status</p>
                <p className={`text-lg font-bold ${validationResult.valid ? 'text-green-600' : 'text-red-600'}`}>
                  {validationResult.valid ? 'Valid' : 'Invalid'}
                </p>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <p className="text-sm text-gray-500 dark:text-gray-400">Employees</p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">{validationResult.employee_count}</p>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <p className="text-sm text-gray-500 dark:text-gray-400">Total Pay</p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  £{validationResult.total_pay?.toLocaleString()}
                </p>
              </div>
            </div>

            {validationResult.errors?.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-medium text-red-600">Errors ({validationResult.errors.length})</h4>
                {validationResult.errors.map((err, idx) => (
                  <div key={idx} className="p-3 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
                    <span className="text-sm text-red-700 dark:text-red-300">{err.message}</span>
                  </div>
                ))}
              </div>
            )}

            {validationResult.warnings?.length > 0 && (
              <div className="space-y-2 mt-4">
                <h4 className="font-medium text-yellow-600">Warnings ({validationResult.warnings.length})</h4>
                {validationResult.warnings.map((warn, idx) => (
                  <div key={idx} className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded border border-yellow-200 dark:border-yellow-800">
                    <span className="text-sm text-yellow-700 dark:text-yellow-300">{warn.message}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Submission History */}
      <Card>
        <CardHeader>
          <CardTitle>Submission History</CardTitle>
          <CardDescription>Past RTI submissions to HMRC</CardDescription>
        </CardHeader>
        <CardContent>
          {submissions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b dark:border-gray-700">
                    <th className="text-left py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Submission ID</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Type</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Pay Run</th>
                    <th className="text-center py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Submitted</th>
                  </tr>
                </thead>
                <tbody>
                  {submissions.map((sub) => (
                    <tr key={sub.submission_id} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="py-3 px-4 font-mono text-sm text-gray-900 dark:text-white">
                        {sub.submission_id?.slice(0, 16)}...
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-1 bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200 rounded text-xs font-medium">
                          {sub.submission_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-600 dark:text-gray-300">
                        {sub.payrun_id?.slice(0, 12)}...
                      </td>
                      <td className="py-3 px-4 text-center">{getStatusBadge(sub.status)}</td>
                      <td className="py-3 px-4 text-gray-600 dark:text-gray-300">
                        {sub.submitted_at ? new Date(sub.submitted_at).toLocaleString() : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <Send className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No submissions yet</p>
              <p className="text-sm mt-2">Submit your first FPS to see it here</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
