# Test Credentials

## Existing Test Account (already created)
- **Email:** test@example.com
- **Password:** Test123!
- **Note:** Created during prior test runs. If login fails, register a new account using the API or UI.

## Account Creation API (fresh user)
```
POST /api/auth/register
{
  "email": "newuser@example.com",
  "password": "Test123!",
  "name": "Test User",
  "company_name": "Test Company"
}
```
Use the returned `token` as `Authorization: Bearer <token>` for subsequent requests.

## Test Cards (Stripe - test mode)
- Success: `4242 4242 4242 4242` (any future expiry, any CVC, any postcode)
- Decline: `4000 0000 0000 0002`
- 3DS required: `4000 0025 0000 3155` (triggers authentication challenge)

## Placeholder credentials (do NOT change in .env)
- `RESEND_API_KEY` is empty by design — emails run in MOCK mode and are logged to backend stdout.
- `HMRC_GATEWAY_ID` / `HMRC_GATEWAY_PASSWORD` placeholder values for sandbox SOAP — RTI submissions run in test mode.

## Live Stripe Test Keys (May 23, 2026)
- Account: **Realtouch Global Ventures Ltd**
- `STRIPE_API_KEY=sk_test_51Sgsqa4GoxwhVGQ6Lzdk...` (in backend/.env)
- `STRIPE_PUBLISHABLE_KEY=pk_test_51Sgsqa4GoxwhVGQ6OJnzVeq...` (in backend/.env + REACT_APP_STRIPE_PUBLISHABLE_KEY in frontend/.env)
- Stripe Link (one-click wallet) auto-enabled
- Google Pay / Apple Pay show automatically in supported browsers
- To swap to LIVE mode: replace `sk_test_*` with `sk_live_*` and `pk_test_*` with `pk_live_*`, then restart backend
