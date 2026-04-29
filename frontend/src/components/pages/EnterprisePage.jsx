import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { 
  Building2, 
  Users, 
  Shield, 
  Key,
  Settings,
  Plus,
  ChevronRight,
  RefreshCw,
  Check,
  X,
  Lock,
  Globe,
  Layers,
  FileKey
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function EnterprisePage() {
  const [activeTab, setActiveTab] = useState('roles');
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState({});
  const [ssoConfig, setSsoConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCreateRole, setShowCreateRole] = useState(false);
  const [newRole, setNewRole] = useState({ name: '', description: '', permissions: [] });

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [rolesRes, permsRes, ssoRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/enterprise/roles`, { headers }),
        fetch(`${BACKEND_URL}/api/enterprise/permissions`, { headers }),
        fetch(`${BACKEND_URL}/api/enterprise/sso/config`, { headers })
      ]);

      if (rolesRes.ok) {
        const data = await rolesRes.json();
        setRoles(data.roles || []);
      }
      if (permsRes.ok) {
        const data = await permsRes.json();
        setPermissions(data.permissions || {});
      }
      if (ssoRes.ok) {
        setSsoConfig(await ssoRes.json());
      }
    } catch (error) {
      console.error('Error fetching enterprise data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateRole = async () => {
    if (!newRole.name || !newRole.description || newRole.permissions.length === 0) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${BACKEND_URL}/api/enterprise/roles`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newRole)
      });

      if (response.ok) {
        setShowCreateRole(false);
        setNewRole({ name: '', description: '', permissions: [] });
        fetchData();
      }
    } catch (error) {
      console.error('Error creating role:', error);
    }
  };

  const togglePermission = (permCode) => {
    setNewRole(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permCode)
        ? prev.permissions.filter(p => p !== permCode)
        : [...prev.permissions, permCode]
    }));
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
          <h1 className="text-3xl font-bold tracking-tight">Enterprise Settings</h1>
          <p className="text-muted-foreground mt-1">
            Advanced RBAC, multi-entity management, and SSO configuration
          </p>
        </div>
        <Badge variant="outline" className="text-primary border-primary">
          Enterprise
        </Badge>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b pb-2">
        {[
          { id: 'roles', label: 'Roles & Permissions', icon: Shield },
          { id: 'entities', label: 'Multi-Entity', icon: Building2 },
          { id: 'sso', label: 'SSO Configuration', icon: Key }
        ].map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab(tab.id)}
            className="gap-2"
            data-testid={`enterprise-tab-${tab.id}`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </Button>
        ))}
      </div>

      {/* Roles & Permissions Tab */}
      {activeTab === 'roles' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold">Role Management</h2>
              <p className="text-sm text-muted-foreground">Configure roles and granular permissions</p>
            </div>
            <Button onClick={() => setShowCreateRole(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Create Custom Role
            </Button>
          </div>

          {/* Role List */}
          <div className="grid gap-4">
            {roles.map((role) => (
              <Card key={role.role_id}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        role.is_system_role ? 'bg-primary/10' : 'bg-purple-100 dark:bg-purple-900/30'
                      }`}>
                        {role.is_system_role ? (
                          <Lock className="w-5 h-5 text-primary" />
                        ) : (
                          <Shield className="w-5 h-5 text-purple-600" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium">{role.name}</h3>
                          {role.is_system_role && (
                            <Badge variant="secondary" className="text-xs">System</Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">{role.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-muted-foreground">
                        {role.permissions?.length || 0} permissions
                      </span>
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Create Role Modal */}
          {showCreateRole && (
            <Card className="border-primary">
              <CardHeader>
                <CardTitle>Create Custom Role</CardTitle>
                <CardDescription>Define a new role with specific permissions</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="roleName">Role Name</Label>
                    <Input
                      id="roleName"
                      value={newRole.name}
                      onChange={(e) => setNewRole(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="e.g., Finance Manager"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="roleDesc">Description</Label>
                    <Input
                      id="roleDesc"
                      value={newRole.description}
                      onChange={(e) => setNewRole(prev => ({ ...prev, description: e.target.value }))}
                      placeholder="Role description..."
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Permissions</Label>
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {Object.entries(permissions).map(([category, perms]) => (
                      <div key={category} className="p-3 rounded-lg border">
                        <h4 className="font-medium capitalize mb-2">{category}</h4>
                        <div className="space-y-2">
                          {perms.map((perm) => (
                            <label key={perm.code} className="flex items-center gap-2 text-sm cursor-pointer">
                              <input
                                type="checkbox"
                                checked={newRole.permissions.includes(perm.code)}
                                onChange={() => togglePermission(perm.code)}
                                className="rounded"
                              />
                              {perm.name}
                            </label>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setShowCreateRole(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateRole}>
                    Create Role
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Multi-Entity Tab */}
      {activeTab === 'entities' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layers className="w-5 h-5" />
                Multi-Entity Management
              </CardTitle>
              <CardDescription>
                Manage multiple legal entities under one organization
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <Building2 className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
                <h3 className="text-lg font-medium mb-2">Multi-Entity Not Configured</h3>
                <p className="text-sm text-muted-foreground mb-4 max-w-md mx-auto">
                  Set up multi-entity management to handle payroll and compliance
                  across multiple legal entities in your organization.
                </p>
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Organization
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Consolidated Reporting</CardTitle>
              <CardDescription>View aggregated payroll data across all entities</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground">Total Employees</p>
                  <p className="text-2xl font-bold">-</p>
                </div>
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground">Total Payroll</p>
                  <p className="text-2xl font-bold">-</p>
                </div>
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground">Active Entities</p>
                  <p className="text-2xl font-bold">-</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* SSO Tab */}
      {activeTab === 'sso' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileKey className="w-5 h-5" />
                SAML SSO Configuration
              </CardTitle>
              <CardDescription>
                Configure Single Sign-On with your Identity Provider
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {ssoConfig?.configured ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-lg bg-emerald-50 dark:bg-emerald-900/20">
                    <div className="flex items-center gap-3">
                      <Check className="w-5 h-5 text-emerald-600" />
                      <span className="font-medium">SSO Enabled</span>
                    </div>
                    <Switch defaultChecked />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label>SP Entity ID</Label>
                      <Input value={ssoConfig.config?.sp_entity_id || ''} readOnly />
                    </div>
                    <div className="space-y-2">
                      <Label>SP ACS URL</Label>
                      <Input value={ssoConfig.config?.sp_acs_url || ''} readOnly />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Key className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
                  <h3 className="text-lg font-medium mb-2">SSO Not Configured</h3>
                  <p className="text-sm text-muted-foreground mb-4 max-w-md mx-auto">
                    Configure SAML SSO to allow employees to sign in with your 
                    organization's Identity Provider (Okta, Azure AD, etc.)
                  </p>
                  <Button>
                    <Settings className="w-4 h-4 mr-2" />
                    Configure SAML SSO
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="w-5 h-5" />
                SCIM Provisioning
              </CardTitle>
              <CardDescription>
                Automated user provisioning and deprovisioning
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between p-4 rounded-lg border">
                <div>
                  <p className="font-medium">SCIM 2.0 Endpoint</p>
                  <p className="text-sm text-muted-foreground">
                    Automatically sync users from your Identity Provider
                  </p>
                </div>
                <Badge variant="outline">Available</Badge>
              </div>
              <div className="mt-4 p-4 rounded-lg bg-muted/50">
                <p className="text-sm font-medium mb-2">SCIM Base URL</p>
                <code className="text-xs bg-background px-2 py-1 rounded">
                  {BACKEND_URL}/api/enterprise/scim
                </code>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
