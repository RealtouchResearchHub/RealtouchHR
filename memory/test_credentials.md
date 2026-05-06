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

## Placeholder credentials (do NOT change in .env)
- `RESEND_API_KEY` is empty by design — emails run in MOCK mode and are logged to backend stdout.
- `HMRC_GATEWAY_ID` / `HMRC_GATEWAY_PASSWORD` placeholder values for sandbox SOAP — RTI submissions run in test mode.
- `STRIPE_API_KEY=sk_test_emergent` is the pod test key — already configured.
