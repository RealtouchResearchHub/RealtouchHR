import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { toast } from 'sonner';
import {
  FileCheck, Send, CheckCircle, XCircle, AlertCircle, 
  Clock, FileText, RefreshCw, Shield, ArrowRight,
  Building2, ChevronRight
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function HMRCDashboard() {
  const { token } = useAuth();
  const [submissions, setSubmissions] = useState([]);
  const [payRuns, setPayRuns] = useState([]);
  const [selectedPayRun, setSelectedPayRun] = useState(null);
  const [healthCheck, setHealthCheck] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchData();
  }, [token]);

  const fetchData = async () => {
    if (!token) return;
    
    try {
      setLoading(true);
      const headers = { 'Authorization': `Bearer ${token}` };
      
      const [subsRes, runsRes] = await Promise.all([
        fetch(`${API_URL}/api/hmrc/submissions`, { headers }),
        fetch(`${API_URL}/api/payroll/runs`, { headers })
      ]);

      if (subsRes.ok) setSubmissions(await subsRes.json());
      if (runsRes.ok) {
        const runs = await runsRes.json();
        setPayRuns(runs.filter(r => r.status === 'approved' || r.status === 'paid'));
      }
    } catch (error) {
      console.error('Error fetching HMRC data:', error);
    } finally {
      setLoading(false);
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

  const submitFPS = async (payrunId) => {
    setSubmitting(true);
    try {
      // Run health check first
      const health = await runHealthCheck(payrunId);
      if (health && !health.can_proceed) {
        toast.error('Cannot submit: Please fix critical issues first');
        setSubmitting(false);
        return;
      }

      // Submit FPS
      const response = await fetch(`${API_URL}/api/hmrc/fps/submit`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          payrun_id: payrunId,
          submission_type: 'FPS',
          test_mode: true
        })
      });

      const result = await response.json();
      
      if (result.success) {
        toast.success('FPS submitted successfully (Test Mode)');
        fetchData();
      } else if (result.errors) {
        toast.error(`Submission failed: ${result.errors.length} validation errors`);
        setValidationResult(result);
      } else {
        toast.error(result.error || 'Submission failed');
      }
    } catch (error) {
      toast.error('Error submitting FPS');
    } finally {
      setSubmitting(false);
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
        <Button variant="outline" onClick={fetchData}>
          <RefreshCw className="h-4 w-4 mr-2" /> Refresh
        </Button>
      </div>

      {/* Test Mode Banner */}
      <Alert className="bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800">
        <Shield className="h-4 w-4 text-amber-600" />
        <AlertTitle className="text-amber-800 dark:text-amber-200">Test Mode Active</AlertTitle>
        <AlertDescription className="text-amber-700 dark:text-amber-300">
          All submissions are sent to HMRC's test environment. To submit to production, 
          configure HMRC Gateway credentials in Settings.
        </AlertDescription>
      </Alert>

      {/* Submission Flow */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pay Run Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Select Pay Run
            </CardTitle>
            <CardDescription>Choose an approved pay run to submit to HMRC</CardDescription>
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
                    }}
                    data-testid={`payrun-${run.payrun_id}`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">
                          {run.period_start} - {run.period_end}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {run.employee_count} employees • £{run.total_gross?.toLocaleString()} gross
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {run.rti_submitted && (
                          <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded dark:bg-green-900 dark:text-green-200">
                            RTI Submitted
                          </span>
                        )}
                        <ChevronRight className="h-5 w-5 text-gray-400" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No approved pay runs available</p>
                <p className="text-sm mt-2">Approve a pay run first to submit to HMRC</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Submission Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Send className="h-5 w-5" />
              Submission Actions
            </CardTitle>
            <CardDescription>
              {selectedPayRun 
                ? `Pay run: ${selectedPayRun.period_start} - ${selectedPayRun.period_end}`
                : 'Select a pay run to begin'
              }
            </CardDescription>
          </CardHeader>
          <CardContent>
            {selectedPayRun ? (
              <div className="space-y-4">
                {/* Step 1: Health Check */}
                <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-400 rounded-full flex items-center justify-center text-sm font-medium">1</span>
                      <span className="font-medium text-gray-900 dark:text-white">Health Check</span>
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => runHealthCheck(selectedPayRun.payrun_id)}
                      data-testid="run-health-check-btn"
                    >
                      <FileCheck className="h-4 w-4 mr-1" /> Run Check
                    </Button>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 ml-8">
                    Verify data quality before submission
                  </p>
                </div>

                {/* Step 2: Validate */}
                <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-400 rounded-full flex items-center justify-center text-sm font-medium">2</span>
                      <span className="font-medium text-gray-900 dark:text-white">Validate</span>
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => validatePayRun(selectedPayRun.payrun_id)}
                      data-testid="validate-btn"
                    >
                      <CheckCircle className="h-4 w-4 mr-1" /> Validate
                    </Button>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 ml-8">
                    Check against HMRC RTI rules
                  </p>
                </div>

                {/* Step 3: Submit */}
                <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-400 rounded-full flex items-center justify-center text-sm font-medium">3</span>
                      <span className="font-medium text-gray-900 dark:text-white">Submit FPS</span>
                    </div>
                    <Button 
                      onClick={() => submitFPS(selectedPayRun.payrun_id)}
                      disabled={submitting || selectedPayRun.rti_submitted}
                      data-testid="submit-fps-btn"
                    >
                      {submitting ? (
                        <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                      ) : (
                        <Send className="h-4 w-4 mr-1" />
                      )}
                      {selectedPayRun.rti_submitted ? 'Already Submitted' : 'Submit to HMRC'}
                    </Button>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 ml-8">
                    Send Full Payment Submission to HMRC
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <ArrowRight className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Select a pay run to see submission options</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

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
