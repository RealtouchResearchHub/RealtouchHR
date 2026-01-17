import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Checkbox } from '../ui/checkbox';
import { toast } from 'sonner';
import {
  FileCheck, Send, CheckCircle, XCircle, AlertCircle, 
  Clock, FileText, RefreshCw, Shield, ArrowRight, ArrowLeft,
  Building2, ChevronRight, AlertTriangle, Lock, History,
  Info, ExternalLink, Eye
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Submission state labels
const STATE_LABELS = {
  preparing: { label: 'Preparing', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
  validation_pending: { label: 'Validating', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' },
  validation_failed: { label: 'Validation Failed', color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' },
  queued: { label: 'Queued', color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200' },
  approval_pending: { label: 'Awaiting Approval', color: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' },
  approved: { label: 'Approved', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
  submitting: { label: 'Submitting', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
  submitted: { label: 'Submitted', color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200' },
  accepted: { label: 'Accepted', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' },
  error: { label: 'Error', color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' },
  cancelled: { label: 'Cancelled', color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200' },
};

export default function HMRCSubmissionPage() {
  const { token } = useAuth();
  const [status, setStatus] = useState(null);
  const [payRuns, setPayRuns] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [selectedPayRun, setSelectedPayRun] = useState(null);
  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [healthCheck, setHealthCheck] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  
  // Wizard state
  const [wizardStep, setWizardStep] = useState(1);
  const [confirmationText, setConfirmationText] = useState('');
  const [acknowledgeDisclaimer, setAcknowledgeDisclaimer] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);

  const fetchData = useCallback(async () => {
    if (!token) return;
    
    try {
      setLoading(true);
      const headers = { 'Authorization': `Bearer ${token}` };
      
      const [statusRes, runsRes, subsRes] = await Promise.all([
        fetch(`${API_URL}/api/rti-sync/status`, { headers }),
        fetch(`${API_URL}/api/payroll/runs`, { headers }),
        fetch(`${API_URL}/api/rti-sync/submissions`, { headers })
      ]);

      if (statusRes.ok) setStatus(await statusRes.json());
      if (runsRes.ok) {
        const runs = await runsRes.json();
        setPayRuns(runs.filter(r => r.status === 'approved' || r.status === 'paid'));
      }
      if (subsRes.ok) {
        const data = await subsRes.json();
        setSubmissions(data.submissions || []);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const runHealthCheck = async (payrunId) => {
    try {
      setProcessing(true);
      const response = await fetch(`${API_URL}/api/rti-sync/health-check/${payrunId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const result = await response.json();
        setHealthCheck(result);
        return result;
      }
    } catch (error) {
      toast.error('Health check failed');
    } finally {
      setProcessing(false);
    }
    return null;
  };

  const prepareSubmission = async () => {
    if (!selectedPayRun) return;
    
    try {
      setProcessing(true);
      const response = await fetch(`${API_URL}/api/rti-sync/prepare`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ payrun_id: selectedPayRun.payrun_id })
      });

      const result = await response.json();
      
      if (response.ok) {
        toast.success('FPS prepared successfully');
        setSelectedSubmission({ submission_id: result.submission_id, ...result });
        setWizardStep(3);
        fetchData();
      } else {
        toast.error(result.detail || 'Preparation failed');
      }
    } catch (error) {
      toast.error('Error preparing submission');
    } finally {
      setProcessing(false);
    }
  };

  const requestApproval = async (submissionId) => {
    try {
      setProcessing(true);
      const response = await fetch(`${API_URL}/api/rti-sync/submissions/${submissionId}/request-approval`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        toast.success('Approval requested');
        setWizardStep(4);
        fetchData();
      } else {
        const data = await response.json();
        toast.error(data.detail || 'Request failed');
      }
    } catch (error) {
      toast.error('Error requesting approval');
    } finally {
      setProcessing(false);
    }
  };

  const approveSubmission = async (submissionId) => {
    const expectedText = `I confirm submission ${submissionId}`;
    if (confirmationText !== expectedText) {
      toast.error(`Confirmation must be exactly: "${expectedText}"`);
      return;
    }

    try {
      setProcessing(true);
      const response = await fetch(`${API_URL}/api/rti-sync/submissions/${submissionId}/approve`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ confirmation_text: confirmationText })
      });

      if (response.ok) {
        toast.success('Submission approved');
        setConfirmationText('');
        setWizardStep(5);
        fetchData();
      } else {
        const data = await response.json();
        toast.error(data.detail || 'Approval failed');
      }
    } catch (error) {
      toast.error('Error approving submission');
    } finally {
      setProcessing(false);
    }
  };

  const submitToHMRC = async (submissionId) => {
    if (!acknowledgeDisclaimer) {
      toast.error('You must acknowledge the compliance disclaimer');
      return;
    }

    try {
      setProcessing(true);
      const response = await fetch(`${API_URL}/api/rti-sync/submissions/${submissionId}/submit`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ acknowledge_disclaimer: true })
      });

      const result = await response.json();
      
      if (response.ok && result.status === 'submitted') {
        toast.success(`Submitted to HMRC (${result.mode}). Correlation ID: ${result.correlation_id}`);
        setWizardStep(6);
        fetchData();
      } else {
        toast.error(result.detail || result.message || 'Submission failed');
      }
    } catch (error) {
      toast.error('Error submitting to HMRC');
    } finally {
      setProcessing(false);
    }
  };

  const rejectSubmission = async (submissionId) => {
    if (rejectionReason.length < 10) {
      toast.error('Please provide a detailed reason (min 10 characters)');
      return;
    }

    try {
      setProcessing(true);
      const response = await fetch(`${API_URL}/api/rti-sync/submissions/${submissionId}/reject`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ reason: rejectionReason })
      });

      if (response.ok) {
        toast.success('Submission rejected');
        setShowRejectModal(false);
        setRejectionReason('');
        setWizardStep(1);
        setSelectedSubmission(null);
        fetchData();
      }
    } catch (error) {
      toast.error('Error rejecting submission');
    } finally {
      setProcessing(false);
    }
  };

  const getStateBadge = (state) => {
    const config = STATE_LABELS[state] || STATE_LABELS.preparing;
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
        {config.label}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="hmrc-submission-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Building2 className="h-7 w-7" />
            RTI Sync Engine
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            HMRC Real Time Information Submissions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            status?.engine_mode === 'live' ? 'bg-green-100 text-green-800' :
            status?.engine_mode === 'sandbox' ? 'bg-amber-100 text-amber-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {status?.engine_mode?.toUpperCase()} Mode
          </span>
          <Button variant="outline" size="sm" onClick={fetchData}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Compliance Disclaimer Banner */}
      <Alert className="bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800">
        <Info className="h-4 w-4 text-blue-600" />
        <AlertTitle className="text-blue-800 dark:text-blue-200">RTI Compliance Information</AlertTitle>
        <AlertDescription className="text-blue-700 dark:text-blue-300">
          <p className="mb-2">This software is <strong>HMRC RTI-compatible</strong> and <strong>HMRC-aligned</strong>.</p>
          <ul className="text-sm space-y-1 list-disc ml-4">
            <li>HMRC does not endorse, approve, or certify payroll software</li>
            <li>Compliance with RTI regulations is the employer's legal responsibility</li>
            <li>All submissions require explicit human approval</li>
            <li>Submission receipts and audit trails are retained for your records</li>
          </ul>
        </AlertDescription>
      </Alert>

      {/* Configuration Warning */}
      {status && !status.company_configured && (
        <Alert className="bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800">
          <AlertTriangle className="h-4 w-4 text-amber-600" />
          <AlertTitle className="text-amber-800 dark:text-amber-200">Configuration Required</AlertTitle>
          <AlertDescription className="text-amber-700 dark:text-amber-300">
            Configure PAYE Reference and Accounts Office Reference in Settings before making RTI submissions.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel - Wizard */}
        <div className="lg:col-span-2 space-y-6">
          {/* Progress */}
          <div className="flex items-center justify-between mb-8 overflow-x-auto">
            {[
              { num: 1, label: 'Select' },
              { num: 2, label: 'Validate' },
              { num: 3, label: 'Prepare' },
              { num: 4, label: 'Approve' },
              { num: 5, label: 'Submit' },
              { num: 6, label: 'Done' }
            ].map((step, idx) => (
              <div key={step.num} className="flex items-center">
                <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
                  wizardStep > step.num ? 'bg-green-500 text-white' :
                  wizardStep === step.num ? 'bg-indigo-600 text-white' :
                  'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                }`}>
                  {wizardStep > step.num ? <CheckCircle className="h-5 w-5" /> : step.num}
                </div>
                <span className={`ml-1 text-xs hidden md:inline ${wizardStep >= step.num ? 'text-gray-900 dark:text-white' : 'text-gray-400'}`}>
                  {step.label}
                </span>
                {idx < 5 && <ChevronRight className="h-4 w-4 mx-1 text-gray-400" />}
              </div>
            ))}
          </div>

          {/* Step 1 */}
          {wizardStep === 1 && (
            <Card>
              <CardHeader>
                <CardTitle>Step 1: Select Pay Run</CardTitle>
                <CardDescription>Choose an approved pay run for FPS</CardDescription>
              </CardHeader>
              <CardContent>
                {payRuns.length > 0 ? (
                  <div className="space-y-3">
                    {payRuns.map((run) => {
                      const existingSub = submissions.find(s => s.payrun_id === run.payrun_id && !['cancelled', 'rejected'].includes(s.state));
                      return (
                        <div
                          key={run.payrun_id}
                          className={`p-4 border rounded-lg cursor-pointer transition-all ${
                            selectedPayRun?.payrun_id === run.payrun_id
                              ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                              : 'border-gray-200 dark:border-gray-700 hover:border-indigo-300'
                          }`}
                          onClick={() => {
                            if (existingSub) {
                              setSelectedSubmission(existingSub);
                              if (['queued'].includes(existingSub.state)) setWizardStep(4);
                              else if (existingSub.state === 'approval_pending') setWizardStep(4);
                              else if (existingSub.state === 'approved') setWizardStep(5);
                              else if (['submitted', 'accepted'].includes(existingSub.state)) setWizardStep(6);
                            } else {
                              setSelectedPayRun(run);
                              setSelectedSubmission(null);
                            }
                          }}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-medium text-gray-900 dark:text-white">{run.period_start} - {run.period_end}</p>
                              <p className="text-sm text-gray-500">{run.employee_count} employees • £{run.total_gross?.toLocaleString()}</p>
                            </div>
                            <div className="flex items-center gap-2">
                              {existingSub && getStateBadge(existingSub.state)}
                              <ChevronRight className="h-5 w-5 text-gray-400" />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No approved pay runs</p>
                  </div>
                )}
              </CardContent>
              <CardFooter>
                <Button onClick={() => setWizardStep(2)} disabled={!selectedPayRun} className="ml-auto">
                  Continue <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </CardFooter>
            </Card>
          )}

          {/* Step 2 */}
          {wizardStep === 2 && (
            <Card>
              <CardHeader>
                <CardTitle>Step 2: RTI Health Check</CardTitle>
                <CardDescription>Validate data against HMRC specifications</CardDescription>
              </CardHeader>
              <CardContent>
                {healthCheck ? (
                  <div className="space-y-4">
                    <div className={`p-4 rounded-lg border ${healthCheck.ready_for_rti ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                      <div className="flex items-center gap-2 mb-2">
                        {healthCheck.ready_for_rti ? <CheckCircle className="h-5 w-5 text-green-600" /> : <XCircle className="h-5 w-5 text-red-600" />}
                        <span className={`font-medium ${healthCheck.ready_for_rti ? 'text-green-800' : 'text-red-800'}`}>
                          {healthCheck.ready_for_rti ? 'Ready for RTI' : 'Issues Found'}
                        </span>
                        <span className="ml-auto text-lg font-bold">Score: {healthCheck.score}%</span>
                      </div>
                      <p className="text-sm text-gray-600">{healthCheck.recommendation}</p>
                    </div>
                    {healthCheck.blocking_issues?.length > 0 && (
                      <div>
                        <h4 className="font-medium text-red-600 mb-2">Blocking Issues ({healthCheck.blocking_issues.length})</h4>
                        {healthCheck.blocking_issues.map((issue, idx) => (
                          <div key={idx} className="p-3 bg-red-50 rounded border border-red-200 mb-2">
                            <p className="font-medium text-red-800">{issue.message}</p>
                            <p className="text-xs text-red-600">Field: {issue.field} • Code: {issue.code}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Shield className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                    <p className="text-gray-500 mb-4">Run the health check to validate your data</p>
                    <Button onClick={() => runHealthCheck(selectedPayRun.payrun_id)} disabled={processing}>
                      {processing ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <FileCheck className="h-4 w-4 mr-2" />}
                      Run Health Check
                    </Button>
                  </div>
                )}
              </CardContent>
              <CardFooter className="flex justify-between">
                <Button variant="outline" onClick={() => setWizardStep(1)}><ArrowLeft className="h-4 w-4 mr-2" /> Back</Button>
                <Button onClick={prepareSubmission} disabled={!healthCheck?.ready_for_rti || processing}>
                  {processing ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : null}
                  Prepare FPS <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </CardFooter>
            </Card>
          )}

          {/* Steps 3-4 */}
          {(wizardStep === 3 || wizardStep === 4) && selectedSubmission && (
            <Card>
              <CardHeader>
                <CardTitle>Step {wizardStep}: Review & Approve</CardTitle>
                <CardDescription>Review and approve for HMRC submission</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
                    <p className="text-sm text-gray-500">Status</p>
                    {getStateBadge(selectedSubmission.state || 'queued')}
                  </div>
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
                    <p className="text-sm text-gray-500">Employees</p>
                    <p className="font-medium">{selectedSubmission.employee_count || healthCheck?.employee_count || '-'}</p>
                  </div>
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
                    <p className="text-sm text-gray-500">Total Pay</p>
                    <p className="font-medium">£{(selectedSubmission.total_pay || healthCheck?.total_pay || 0).toLocaleString()}</p>
                  </div>
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
                    <p className="text-sm text-gray-500">Payload Hash</p>
                    <p className="font-mono text-xs truncate">{selectedSubmission.payload_hash || '-'}</p>
                  </div>
                </div>

                {['queued'].includes(selectedSubmission.state) && (
                  <div className="p-4 border border-indigo-200 rounded-lg bg-indigo-50">
                    <h4 className="font-medium text-indigo-800 mb-2">Request Approval</h4>
                    <p className="text-sm text-indigo-600 mb-4">This submission requires approval before HMRC submission.</p>
                    <Button onClick={() => requestApproval(selectedSubmission.submission_id)} disabled={processing}>Request Approval</Button>
                  </div>
                )}

                {selectedSubmission.state === 'approval_pending' && (
                  <div className="p-4 border border-amber-200 rounded-lg bg-amber-50">
                    <h4 className="font-medium text-amber-800 mb-2 flex items-center gap-2"><Lock className="h-4 w-4" />Approve Submission</h4>
                    <p className="text-sm text-amber-600 mb-4">Type: "I confirm submission {selectedSubmission.submission_id}"</p>
                    <Input
                      value={confirmationText}
                      onChange={(e) => setConfirmationText(e.target.value)}
                      placeholder="Type confirmation..."
                      className="my-2 font-mono text-sm"
                    />
                    <div className="flex gap-2 mt-4">
                      <Button onClick={() => approveSubmission(selectedSubmission.submission_id)} disabled={processing || confirmationText !== `I confirm submission ${selectedSubmission.submission_id}`}>
                        <CheckCircle className="h-4 w-4 mr-2" /> Approve
                      </Button>
                      <Button variant="outline" onClick={() => setShowRejectModal(true)} className="text-red-600">
                        <XCircle className="h-4 w-4 mr-2" /> Reject
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
              <CardFooter className="flex justify-between">
                <Button variant="outline" onClick={() => { setWizardStep(1); setSelectedSubmission(null); }}>
                  <ArrowLeft className="h-4 w-4 mr-2" /> Start Over
                </Button>
                {selectedSubmission.state === 'approved' && (
                  <Button onClick={() => setWizardStep(5)}>Continue <ArrowRight className="h-4 w-4 ml-2" /></Button>
                )}
              </CardFooter>
            </Card>
          )}

          {/* Step 5 */}
          {wizardStep === 5 && selectedSubmission && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Send className="h-5 w-5" />Step 5: Submit to HMRC</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Alert className="bg-red-50 border-red-200">
                  <AlertTriangle className="h-4 w-4 text-red-600" />
                  <AlertTitle className="text-red-800">Important Compliance Disclaimer</AlertTitle>
                  <AlertDescription className="text-red-700 space-y-2">
                    <p>By submitting, you acknowledge that:</p>
                    <ul className="list-disc ml-4 text-sm space-y-1">
                      <li>This software is HMRC RTI-compatible but <strong>not endorsed</strong> by HMRC</li>
                      <li>Compliance is the <strong>employer's legal responsibility</strong></li>
                      <li>You have verified all payroll data accuracy</li>
                      <li>Current mode: <strong>{status?.engine_mode?.toUpperCase()}</strong></li>
                    </ul>
                  </AlertDescription>
                </Alert>
                <div className="flex items-start space-x-3 p-4 border rounded-lg">
                  <Checkbox id="ack" checked={acknowledgeDisclaimer} onCheckedChange={setAcknowledgeDisclaimer} />
                  <Label htmlFor="ack" className="font-medium">I acknowledge the compliance disclaimer</Label>
                </div>
              </CardContent>
              <CardFooter className="flex justify-between">
                <Button variant="outline" onClick={() => setWizardStep(4)}><ArrowLeft className="h-4 w-4 mr-2" /> Back</Button>
                <Button onClick={() => submitToHMRC(selectedSubmission.submission_id)} disabled={!acknowledgeDisclaimer || processing} className="bg-green-600 hover:bg-green-700">
                  {processing ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
                  Submit to HMRC
                </Button>
              </CardFooter>
            </Card>
          )}

          {/* Step 6 */}
          {wizardStep === 6 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-green-600"><CheckCircle className="h-6 w-6" />Submission Complete</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Alert className="bg-green-50 border-green-200">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <AlertTitle className="text-green-800">FPS Submitted Successfully</AlertTitle>
                  <AlertDescription className="text-green-700">
                    Your FPS has been sent to HMRC.{status?.engine_mode === 'sandbox' && ' (Sandbox Mode)'}
                  </AlertDescription>
                </Alert>
                <Button onClick={() => { setWizardStep(1); setSelectedPayRun(null); setSelectedSubmission(null); setHealthCheck(null); setAcknowledgeDisclaimer(false); }} className="w-full">
                  Start New Submission
                </Button>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Panel */}
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle className="text-lg flex items-center gap-2"><History className="h-5 w-5" />Recent Submissions</CardTitle></CardHeader>
            <CardContent>
              {submissions.length > 0 ? (
                <div className="space-y-3">
                  {submissions.slice(0, 5).map((sub) => (
                    <div key={sub.submission_id} className="p-3 border rounded-lg hover:bg-gray-50 cursor-pointer" onClick={() => { setSelectedSubmission(sub); }}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-xs text-gray-500">{sub.submission_id?.slice(0, 12)}...</span>
                        {getStateBadge(sub.state)}
                      </div>
                      <p className="text-sm text-gray-600">{sub.submission_type} • {sub.employee_count || '-'} employees</p>
                    </div>
                  ))}
                </div>
              ) : <p className="text-sm text-gray-500 text-center py-4">No submissions yet</p>}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-lg">Resources</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              <a href="https://www.gov.uk/paye-online/sending-real-time-submissions" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-indigo-600 hover:underline">
                <ExternalLink className="h-4 w-4" />HMRC RTI Guidance
              </a>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md mx-4">
            <CardHeader><CardTitle>Reject Submission</CardTitle></CardHeader>
            <CardContent>
              <textarea value={rejectionReason} onChange={(e) => setRejectionReason(e.target.value)} placeholder="Reason (min 10 chars)..." className="w-full h-24 p-2 border rounded-lg" />
            </CardContent>
            <CardFooter className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => setShowRejectModal(false)}>Cancel</Button>
              <Button variant="destructive" onClick={() => rejectSubmission(selectedSubmission?.submission_id)} disabled={rejectionReason.length < 10 || processing}>Reject</Button>
            </CardFooter>
          </Card>
        </div>
      )}
    </div>
  );
}
