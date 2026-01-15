import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { toast } from 'sonner';
import { 
  User, FileText, Calendar, CreditCard, 
  Download, Clock, CheckCircle, XCircle, AlertCircle,
  Edit, Save, X
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function SelfServicePortal() {
  const { token } = useAuth();
  const [profile, setProfile] = useState(null);
  const [payslips, setPayslips] = useState([]);
  const [leaveBalance, setLeaveBalance] = useState(null);
  const [leaveRequests, setLeaveRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({});

  useEffect(() => {
    fetchData();
  }, [token]);

  const fetchData = async () => {
    if (!token) return;
    
    try {
      setLoading(true);
      const headers = { 'Authorization': `Bearer ${token}` };
      
      const [profileRes, payslipsRes, balanceRes, requestsRes] = await Promise.all([
        fetch(`${API_URL}/api/self-service/profile`, { headers }),
        fetch(`${API_URL}/api/self-service/payslips`, { headers }),
        fetch(`${API_URL}/api/self-service/leave/balance`, { headers }),
        fetch(`${API_URL}/api/self-service/leave/requests`, { headers })
      ]);

      if (profileRes.ok) {
        const data = await profileRes.json();
        setProfile(data);
        setEditData(data);
      }
      if (payslipsRes.ok) setPayslips(await payslipsRes.json());
      if (balanceRes.ok) setLeaveBalance(await balanceRes.json());
      if (requestsRes.ok) setLeaveRequests(await requestsRes.json());
    } catch (error) {
      console.error('Error fetching self-service data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    try {
      const response = await fetch(`${API_URL}/api/self-service/profile`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(editData)
      });

      if (response.ok) {
        toast.success('Profile updated successfully');
        setIsEditing(false);
        fetchData();
      } else {
        toast.error('Failed to update profile');
      }
    } catch (error) {
      toast.error('Error updating profile');
    }
  };

  const handleDownloadPayslip = async (payrunId) => {
    try {
      const response = await fetch(`${API_URL}/api/self-service/payslips/${payrunId}/download`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `payslip_${payrunId}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        toast.success('Payslip downloaded');
      } else {
        toast.error('Failed to download payslip');
      }
    } catch (error) {
      toast.error('Error downloading payslip');
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      approved: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      rejected: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
      paid: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
    };
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
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
    <div className="space-y-6" data-testid="self-service-portal">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Employee Self-Service
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Welcome back, {profile?.first_name}
          </p>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-indigo-500 to-purple-600 text-white">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-indigo-100 text-sm">Leave Balance</p>
                <p className="text-2xl font-bold">{leaveBalance?.remaining || 0} days</p>
              </div>
              <Calendar className="h-8 w-8 opacity-75" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 dark:text-gray-400 text-sm">Used Leave</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {leaveBalance?.used || 0} days
                </p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 dark:text-gray-400 text-sm">Pending Leave</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {leaveBalance?.pending || 0} days
                </p>
              </div>
              <Clock className="h-8 w-8 text-yellow-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 dark:text-gray-400 text-sm">Payslips</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {payslips.length}
                </p>
              </div>
              <FileText className="h-8 w-8 text-indigo-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          {['overview', 'payslips', 'leave', 'profile'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
              }`}
              data-testid={`tab-${tab}`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Payslips */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Recent Payslips
              </CardTitle>
            </CardHeader>
            <CardContent>
              {payslips.length > 0 ? (
                <div className="space-y-3">
                  {payslips.slice(0, 3).map((ps) => (
                    <div key={ps.payrun_id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">
                          {ps.period_start} - {ps.period_end}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Net: £{ps.net_pay?.toLocaleString()}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDownloadPayslip(ps.payrun_id)}
                        data-testid={`download-payslip-${ps.payrun_id}`}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                  No payslips available yet
                </p>
              )}
            </CardContent>
          </Card>

          {/* Leave Requests */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Recent Leave Requests
              </CardTitle>
            </CardHeader>
            <CardContent>
              {leaveRequests.length > 0 ? (
                <div className="space-y-3">
                  {leaveRequests.slice(0, 3).map((leave) => (
                    <div key={leave.leave_id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">
                          {leave.leave_type}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {leave.start_date} - {leave.end_date} ({leave.days} days)
                        </p>
                      </div>
                      {getStatusBadge(leave.status)}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                  No leave requests
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'payslips' && (
        <Card>
          <CardHeader>
            <CardTitle>Payslip History</CardTitle>
            <CardDescription>Download your payslips as PDF</CardDescription>
          </CardHeader>
          <CardContent>
            {payslips.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b dark:border-gray-700">
                      <th className="text-left py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Period</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Pay Date</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Gross</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Net</th>
                      <th className="text-center py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Status</th>
                      <th className="text-center py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payslips.map((ps) => (
                      <tr key={ps.payrun_id} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="py-3 px-4 text-gray-900 dark:text-white">
                          {ps.period_start} - {ps.period_end}
                        </td>
                        <td className="py-3 px-4 text-gray-600 dark:text-gray-300">{ps.pay_date}</td>
                        <td className="py-3 px-4 text-right text-gray-900 dark:text-white">
                          £{ps.gross_pay?.toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-right font-medium text-gray-900 dark:text-white">
                          £{ps.net_pay?.toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-center">{getStatusBadge(ps.status)}</td>
                        <td className="py-3 px-4 text-center">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDownloadPayslip(ps.payrun_id)}
                          >
                            <Download className="h-4 w-4 mr-1" /> Download
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No payslips available yet</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'leave' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle>Leave Balance</CardTitle>
              <CardDescription>Annual leave entitlement</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-500 dark:text-gray-400">Total Entitlement</span>
                  <span className="font-bold text-gray-900 dark:text-white">
                    {leaveBalance?.annual_entitlement || 28} days
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-500 dark:text-gray-400">Used</span>
                  <span className="font-medium text-red-600">{leaveBalance?.used || 0} days</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-500 dark:text-gray-400">Pending</span>
                  <span className="font-medium text-yellow-600">{leaveBalance?.pending || 0} days</span>
                </div>
                <div className="border-t dark:border-gray-700 pt-4 flex justify-between items-center">
                  <span className="font-medium text-gray-900 dark:text-white">Remaining</span>
                  <span className="text-xl font-bold text-green-600">{leaveBalance?.remaining || 28} days</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Leave Requests</CardTitle>
            </CardHeader>
            <CardContent>
              {leaveRequests.length > 0 ? (
                <div className="space-y-3">
                  {leaveRequests.map((leave) => (
                    <div key={leave.leave_id} className="p-4 border dark:border-gray-700 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-gray-900 dark:text-white">{leave.leave_type}</span>
                        {getStatusBadge(leave.status)}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        <p>{leave.start_date} - {leave.end_date} ({leave.days} days)</p>
                        {leave.reason && <p className="mt-1 italic">"{leave.reason}"</p>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No leave requests</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'profile' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>My Profile</CardTitle>
                <CardDescription>Update your personal information</CardDescription>
              </div>
              {!isEditing ? (
                <Button variant="outline" onClick={() => setIsEditing(true)} data-testid="edit-profile-btn">
                  <Edit className="h-4 w-4 mr-2" /> Edit
                </Button>
              ) : (
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setIsEditing(false)}>
                    <X className="h-4 w-4 mr-2" /> Cancel
                  </Button>
                  <Button onClick={handleSaveProfile} data-testid="save-profile-btn">
                    <Save className="h-4 w-4 mr-2" /> Save
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <Label>First Name</Label>
                <Input value={profile?.first_name || ''} disabled className="mt-1" />
              </div>
              <div>
                <Label>Last Name</Label>
                <Input value={profile?.last_name || ''} disabled className="mt-1" />
              </div>
              <div>
                <Label>Email</Label>
                <Input value={profile?.email || ''} disabled className="mt-1" />
              </div>
              <div>
                <Label>Job Title</Label>
                <Input value={profile?.job_title || ''} disabled className="mt-1" />
              </div>
              <div>
                <Label>Department</Label>
                <Input value={profile?.department || ''} disabled className="mt-1" />
              </div>
              <div>
                <Label>Start Date</Label>
                <Input value={profile?.start_date || ''} disabled className="mt-1" />
              </div>
              
              {/* Editable fields */}
              <div className="md:col-span-2">
                <h3 className="font-medium text-gray-900 dark:text-white mb-4 mt-4">
                  Editable Information
                </h3>
              </div>
              <div>
                <Label>Phone Number</Label>
                <Input 
                  value={editData.phone || ''} 
                  onChange={(e) => setEditData({...editData, phone: e.target.value})}
                  disabled={!isEditing}
                  className="mt-1"
                  placeholder="Enter phone number"
                />
              </div>
              <div>
                <Label>Address</Label>
                <Input 
                  value={editData.address || ''} 
                  onChange={(e) => setEditData({...editData, address: e.target.value})}
                  disabled={!isEditing}
                  className="mt-1"
                  placeholder="Enter address"
                />
              </div>
              <div>
                <Label>Emergency Contact Name</Label>
                <Input 
                  value={editData.emergency_contact_name || ''} 
                  onChange={(e) => setEditData({...editData, emergency_contact_name: e.target.value})}
                  disabled={!isEditing}
                  className="mt-1"
                  placeholder="Emergency contact name"
                />
              </div>
              <div>
                <Label>Emergency Contact Phone</Label>
                <Input 
                  value={editData.emergency_contact_phone || ''} 
                  onChange={(e) => setEditData({...editData, emergency_contact_phone: e.target.value})}
                  disabled={!isEditing}
                  className="mt-1"
                  placeholder="Emergency contact phone"
                />
              </div>
              <div>
                <Label>Bank Account Number</Label>
                <Input 
                  value={editData.bank_account || ''} 
                  onChange={(e) => setEditData({...editData, bank_account: e.target.value})}
                  disabled={!isEditing}
                  className="mt-1"
                  placeholder="8-digit account number"
                />
              </div>
              <div>
                <Label>Sort Code</Label>
                <Input 
                  value={editData.bank_sort_code || ''} 
                  onChange={(e) => setEditData({...editData, bank_sort_code: e.target.value})}
                  disabled={!isEditing}
                  className="mt-1"
                  placeholder="XX-XX-XX"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
