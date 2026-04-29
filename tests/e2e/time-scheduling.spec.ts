import { test, expect } from '@playwright/test';
import { login, waitForAppReady } from '../fixtures/helpers';

test.describe('Time & Scheduling Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('navigates to Time Tracking page from sidebar', async ({ page }) => {
    // Click on Time Tracking in sidebar
    const navLink = page.locator('[data-testid="nav-time tracking"]');
    await navLink.click();
    await page.waitForLoadState('networkidle');
    
    // Verify page loaded
    await expect(page.getByRole('heading', { name: /Time & Scheduling/i })).toBeVisible();
  });

  test('displays clock in/out tab with time clock', async ({ page }) => {
    // Navigate to Time Tracking
    await page.locator('[data-testid="nav-time tracking"]').click();
    await page.waitForLoadState('networkidle');
    
    // Wait for page content to load
    await expect(page.getByText('Time Clock')).toBeVisible();
    await expect(page.getByText('Record your work hours')).toBeVisible();
  });

  test('displays current time and date', async ({ page }) => {
    await page.locator('[data-testid="nav-time tracking"]').click();
    await page.waitForLoadState('networkidle');
    
    // Should show current time (format HH:MM)
    const timeDisplay = page.locator('.font-mono.text-5xl');
    await expect(timeDisplay).toBeVisible();
    
    // Should show current date
    const dateText = page.getByText(/Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday/);
    await expect(dateText.first()).toBeVisible();
  });

  test('shows clock status badge', async ({ page }) => {
    await page.locator('[data-testid="nav-time tracking"]').click();
    await page.waitForLoadState('networkidle');
    
    // Wait for Time Clock to load first
    await expect(page.getByText('Time Clock')).toBeVisible();
    
    // Should show "Not Clocked In" badge (test user has no employee record)
    await expect(page.getByText('Not Clocked In')).toBeVisible();
  });

  test('has working tab navigation', async ({ page }) => {
    await page.locator('[data-testid="nav-time tracking"]').click();
    await page.waitForLoadState('networkidle');
    
    // Wait for page to load
    await expect(page.getByText('Time Clock')).toBeVisible();
    
    // Click Schedule tab
    await page.locator('[data-testid="time-tab-schedule"]').click({ force: true });
    await expect(page.getByText('Weekly Schedule')).toBeVisible();
    
    // Click Timesheets tab
    await page.locator('[data-testid="time-tab-timesheets"]').click({ force: true });
    await expect(page.getByText('My Timesheets')).toBeVisible();
    
    // Click Approvals tab
    await page.locator('[data-testid="time-tab-approvals"]').click({ force: true });
    await expect(page.getByText('Pending Approvals', { exact: true })).toBeVisible();
    
    // Go back to Clock tab
    await page.locator('[data-testid="time-tab-clock"]').click({ force: true });
    await expect(page.getByText('Time Clock')).toBeVisible();
  });

  test('schedule tab shows week navigation', async ({ page }) => {
    await page.locator('[data-testid="nav-time tracking"]').click();
    await page.waitForLoadState('networkidle');
    
    // Wait for page to load
    await expect(page.getByText('Time Clock')).toBeVisible();
    
    // Click Schedule tab
    await page.locator('[data-testid="time-tab-schedule"]').click({ force: true });
    
    // Should show week navigation buttons
    const prevWeekBtn = page.locator('button').filter({ has: page.locator('svg.lucide-chevron-left') });
    const nextWeekBtn = page.locator('button').filter({ has: page.locator('svg.lucide-chevron-right') });
    
    await expect(prevWeekBtn).toBeVisible();
    await expect(nextWeekBtn).toBeVisible();
  });

  test('shows Today Activity section', async ({ page }) => {
    await page.locator('[data-testid="nav-time tracking"]').click();
    await page.waitForLoadState('networkidle');
    
    // Wait for page to load
    await expect(page.getByText('Time Clock')).toBeVisible();
    
    // Should show Today's Activity card
    await expect(page.getByText("Today's Activity")).toBeVisible();
  });
});

test.describe('Dashboard Loads Correctly', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('dashboard displays after login', async ({ page }) => {
    // Should be on dashboard after login
    await expect(page).toHaveURL(/.*dashboard/);
    
    // Dashboard should have welcome message
    await expect(page.getByRole('heading', { name: /Welcome back/i })).toBeVisible();
  });

  test('dashboard shows stat cards', async ({ page }) => {
    // Look for stat cards (Total Employees, On Leave Today, Pending Approvals)
    await expect(page.getByText('Total Employees')).toBeVisible();
    await expect(page.getByText('On Leave Today')).toBeVisible();
    await expect(page.getByText('Pending Approvals')).toBeVisible();
  });

  test('dashboard shows compliance status', async ({ page }) => {
    // Look for compliance status card
    await expect(page.getByText('Compliance Status')).toBeVisible();
  });

  test('sidebar navigation is visible', async ({ page }) => {
    // Verify sidebar navigation items
    await expect(page.locator('[data-testid="nav-dashboard"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-employees"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-time tracking"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-payroll"]')).toBeVisible();
  });
});
