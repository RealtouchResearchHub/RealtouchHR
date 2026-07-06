import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { ShieldOff, Shield, ArrowRight } from 'lucide-react';

export default function LegacyRTINotice() {
  return (
    <div className="max-w-2xl mx-auto py-12">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldOff className="h-6 w-6 text-muted-foreground" />
            Legacy RTI Dashboard Disabled
          </CardTitle>
          <CardDescription>
            This legacy RTI dashboard has been disabled. Please use RTI Sync for sandbox/test workflow and payroll readiness.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert className="bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800">
            <AlertTitle className="text-amber-800 dark:text-amber-200">Why this page is disabled</AlertTitle>
            <AlertDescription className="text-amber-700 dark:text-amber-300">
              This dashboard could previously suggest that HMRC RTI submissions were live when they were only
              sandbox simulations. RTI behaviour is now consolidated around the RTI Sync engine, which clearly
              labels sandbox/simulated activity and requires explicit approval before any submission.
            </AlertDescription>
          </Alert>
          <Link to="/rti-sync">
            <Button className="w-full">
              <Shield className="h-4 w-4 mr-2" />
              Go to RTI Sync
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
