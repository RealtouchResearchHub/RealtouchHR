import { test, expect } from '@playwright/test';
import { login, dismissToasts, waitForAppReady } from '../fixtures/helpers';

test.describe('UKVI Compliance Page', () => {
  test.beforeEach(async ({ page }) => {
    await dismissToasts(page);
    await login(page);
  });

  test('navigates to UKVI Compliance page from sidebar', async ({ page }) => {
    // Navigate directly to UKVI page
    await page.goto('/ukvi');
    await waitForAppReady(page);
    
    // Verify URL
    await expect(page).toHaveURL(/.*\/ukvi/);
    
    // Verify page title
    await expect(page.locator('h1')).toContainText('UKVI Compliance');
  });

  test('displays UKVI compliance dashboard with key metrics', async ({ page }) => {
    await page.goto('/ukvi');
    await waitForAppReady(page);
    
    // Wait for data to load
    await page.waitForSelector('text=Overall Score', { timeout: 10000 });
    
    // Verify key metrics are displayed using more specific selectors
    await expect(page.getByText('Overall Score', { exact: true })).toBeVisible();
    await expect(page.getByText('Sponsored Employees', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Active Alerts', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Pending Reports', { exact: true }).first()).toBeVisible();
  });

  test('displays UKVI compliance disclaimer', async ({ page }) => {
    await page.goto('/ukvi');
    await waitForAppReady(page);
    
    // Verify disclaimer is visible
    const disclaimer = page.locator('text=does not constitute legal advice');
    await expect(disclaimer).toBeVisible();
  });

  test('has working tab navigation (overview, reporting, alerts)', async ({ page }) => {
    await page.goto('/ukvi');
    await waitForAppReady(page);
    
    // Wait for tabs to load
    await page.waitForSelector('button:has-text("Overview")', { timeout: 10000 });
    
    // Click on Reporting tab (exact match)
    await page.getByRole('button', { name: 'reporting', exact: true }).click();
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText('UKVI Reporting Checklist', { exact: true })).toBeVisible();
    
    // Click on Alerts tab (exact match to avoid "Check Alerts" button)
    await page.getByRole('button', { name: 'alerts', exact: true }).click();
    await page.waitForLoadState('domcontentloaded');
    // Wait for Alerts tab content - "No active alerts" message
    await expect(page.getByText('No active alerts')).toBeVisible();
    
    // Click back to Overview tab
    await page.getByRole('button', { name: 'overview', exact: true }).click();
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText('Overall Score', { exact: true })).toBeVisible();
  });

  test('displays Check Alerts and Refresh buttons', async ({ page }) => {
    await page.goto('/ukvi');
    await waitForAppReady(page);
    
    // Verify action buttons
    await expect(page.locator('button:has-text("Check Alerts")')).toBeVisible();
    await expect(page.locator('button:has-text("Refresh")')).toBeVisible();
  });
});

test.describe('Enterprise Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await dismissToasts(page);
    await login(page);
  });

  test('navigates to Enterprise page from sidebar', async ({ page }) => {
    // Navigate directly to Enterprise page
    await page.goto('/enterprise');
    await waitForAppReady(page);
    
    // Verify URL
    await expect(page).toHaveURL(/.*\/enterprise/);
    
    // Verify page title
    await expect(page.locator('h1')).toContainText('Enterprise Settings');
  });

  test('displays Enterprise badge and description', async ({ page }) => {
    await page.goto('/enterprise');
    await waitForAppReady(page);
    
    // Verify Enterprise badge
    await expect(page.locator('text=Enterprise').first()).toBeVisible();
    
    // Verify description
    await expect(page.locator('text=Advanced RBAC')).toBeVisible();
  });

  test('has working tab navigation (Roles, Multi-Entity, SSO)', async ({ page }) => {
    await page.goto('/enterprise');
    await waitForAppReady(page);
    
    // Wait for tabs to load
    await page.waitForSelector('button:has-text("Roles & Permissions")', { timeout: 10000 });
    
    // Verify Roles tab is active by default
    await expect(page.getByText('Role Management', { exact: true })).toBeVisible();
    
    // Click on Multi-Entity tab
    await page.click('button:has-text("Multi-Entity")');
    await page.waitForLoadState('domcontentloaded');
    // Use CardTitle selector for Multi-Entity Management
    await expect(page.getByText('Multi-Entity Not Configured')).toBeVisible();
    
    // Click on SSO tab
    await page.click('button:has-text("SSO Configuration")');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText('SSO Not Configured')).toBeVisible();
  });

  test('displays Create Custom Role button', async ({ page }) => {
    await page.goto('/enterprise');
    await waitForAppReady(page);
    
    // Verify Create Custom Role button
    await expect(page.locator('button:has-text("Create Custom Role")')).toBeVisible();
  });

  test('displays SCIM provisioning section in SSO tab', async ({ page }) => {
    await page.goto('/enterprise');
    await waitForAppReady(page);
    
    // Navigate to SSO tab
    await page.click('button:has-text("SSO Configuration")');
    await page.waitForLoadState('domcontentloaded');
    
    // Verify SCIM section
    await expect(page.getByText('SCIM Provisioning')).toBeVisible();
    await expect(page.getByText('SCIM 2.0 Endpoint', { exact: true })).toBeVisible();
  });
});

test.describe('Dashboard Compliance Score', () => {
  test.beforeEach(async ({ page }) => {
    await dismissToasts(page);
    await login(page);
  });

  test('displays compliance score card on dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    await waitForAppReady(page);
    
    // Wait for dashboard to load
    await page.waitForSelector('[data-testid="compliance-score-card"]', { timeout: 10000 });
    
    // Verify compliance score card is visible
    const complianceCard = page.locator('[data-testid="compliance-score-card"]');
    await expect(complianceCard).toBeVisible();
    
    // Verify it contains "Compliance Status" text
    await expect(complianceCard.locator('text=Compliance Status')).toBeVisible();
  });

  test('displays stat cards on dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    await waitForAppReady(page);
    
    // Verify stat cards are visible
    await expect(page.locator('[data-testid="stat-card-total-employees"]')).toBeVisible();
    await expect(page.locator('[data-testid="stat-card-on-leave-today"]')).toBeVisible();
    await expect(page.locator('[data-testid="stat-card-pending-approvals"]')).toBeVisible();
  });

  test('displays quick action cards on dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    await waitForAppReady(page);
    
    // Verify quick action cards
    await expect(page.locator('[data-testid="quick-add-employee"]')).toBeVisible();
    await expect(page.locator('[data-testid="quick-run-payroll"]')).toBeVisible();
    await expect(page.locator('[data-testid="quick-scheduling"]')).toBeVisible();
    await expect(page.locator('[data-testid="quick-documents"]')).toBeVisible();
  });
});
