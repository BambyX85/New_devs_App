# Bugfix Changelog

Date: 2026-02-17

## Summary
This changelog records all critical/major bugs identified during the assignment, with root cause and surgical fix details.

## 1) Cross-tenant dashboard data leakage via cache key collision
- Severity: Critical
- Symptom: Different tenants could see cached revenue from another tenant after refresh.
- Root cause: Revenue cache key did not include tenant context.
- Fix:
  - Updated cache key to include `tenant_id`, `property_id`, and reporting period context.
  - File: `backend/app/services/cache.py`

## 2) Missing tenant ownership validation for dashboard property requests
- Severity: Critical
- Symptom: Authenticated users could request summary for properties not owned by their tenant.
- Root cause: API accepted `property_id` without tenant ownership check.
- Fix:
  - Added DB ownership guard: `properties.id = :property_id AND properties.tenant_id = :tenant_id`.
  - Returns 404 when property does not belong to tenant.
  - File: `backend/app/api/v1/dashboard.py`

## 3) Dashboard property selector leaked cross-tenant property list
- Severity: Major
- Symptom: Frontend selector showed hardcoded/global properties unrelated to current tenant.
- Root cause: Frontend used static property list, not tenant-scoped backend data.
- Fix:
  - Added backend endpoint returning tenant-scoped properties.
  - Wired frontend dashboard selector to this endpoint.
  - Files:
    - `backend/app/api/v1/dashboard.py`
    - `frontend/src/lib/secureApi.ts`
    - `frontend/src/components/Dashboard.tsx`

## 4) Monthly revenue query not accurately aligned to property timezone/month window
- Severity: Major
- Symptom: Reported monthly totals could differ from internal records (especially month boundaries).
- Root cause: Revenue aggregation logic did not consistently enforce property-local month window.
- Fix:
  - Reworked query to use property timezone-aware month windows.
  - Supports explicit `month/year` and latest-month mode.
  - File: `backend/app/services/reservations.py`

## 5) Monetary precision drift in API/UI formatting
- Severity: Major
- Symptom: Finance observed small cents-level mismatches.
- Root cause: Float-style representation/transport could introduce display and rounding drift.
- Fix:
  - Revenue totals now normalized and returned as 2-decimal string.
  - Frontend consumes string and renders normalized currency output.
  - Files:
    - `backend/app/services/reservations.py`
    - `backend/app/api/v1/dashboard.py`
    - `frontend/src/components/RevenueSummary.tsx`

## 6) Hardcoded trend badge ("12%") in dashboard
- Severity: Major
- Symptom: UI always showed 12% increase regardless of real data.
- Root cause: Trend value was static in frontend.
- Fix:
  - Implemented backend trend calculation (current month vs previous month).
  - Frontend renders trend only when computed data is available.
  - Files:
    - `backend/app/services/reservations.py`
    - `backend/app/api/v1/dashboard.py`
    - `frontend/src/components/RevenueSummary.tsx`

## 7) Forged JWT acceptance in challenge-mode auth fallback
- Severity: Critical
- Symptom: Invalid-signed JWT-like tokens could authenticate.
- Root cause:
  - Auth fallback accepted JWT-style tokens after signature failure path.
  - Challenge auth decoded JWT payload with signature verification disabled.
- Fix:
  - Reject JWT-style token fallback when JWT verification fails.
  - Enforce signature+audience verification in challenge auth path.
  - Files:
    - `backend/app/core/auth.py`
    - `backend/app/database.py`

## 8) Password bypass for non-static login path
- Severity: Critical
- Symptom: Some users could log in with wrong password.
- Root cause: Fallback login path issued token after email lookup only.
- Fix:
  - Removed insecure fallback login path; unsupported credentials now fail closed with 401.
  - File: `backend/app/api/v1/login.py`

## 9) Tenant resolver defaulted unknown users to tenant-a
- Severity: Major
- Symptom: Unknown users could be assigned tenant-a implicitly.
- Root cause: Hardcoded default fallback in tenant resolver.
- Fix:
  - Unknown users now resolve to `None` instead of defaulting to tenant-a.
  - File: `backend/app/core/tenant_resolver.py`

## 10) Unauthenticated operational control endpoints
- Severity: Major
- Symptom: Circuit-breaker/fallback control endpoints were callable without authentication.
- Root cause: Missing auth/admin guards.
- Fix:
  - Added authentication + admin checks to operational endpoints.
  - File: `backend/app/main.py`

## 11) Partial date filter ambiguity (`month` without `year` or vice versa)
- Severity: Major
- Symptom: Partial filters silently fell back to latest month, causing confusing results.
- Root cause: API accepted partial period input without validation.
- Fix:
  - Added validation requiring `month` and `year` together.
  - Returns 422 on partial period.
  - File: `backend/app/api/v1/dashboard.py`

---

## Coverage Against Reported Client/Finance Complaints

### Client A (March totals mismatch)
Covered: Yes.
- Primary fixes:
  - Timezone-aware monthly aggregation (`backend/app/services/reservations.py`)
  - Partial filter validation (`backend/app/api/v1/dashboard.py`)
  - Precision normalization (`backend/app/services/reservations.py`, `backend/app/api/v1/dashboard.py`)

### Client B (seeing other company revenue after refresh)
Covered: Yes.
- Primary fixes:
  - Tenant-scoped cache keys (`backend/app/services/cache.py`)
  - Tenant ownership check on summary endpoint (`backend/app/api/v1/dashboard.py`)
  - Tenant-scoped property list in UI (`backend/app/api/v1/dashboard.py`, `frontend/src/components/Dashboard.tsx`)

### Finance (totals off by a few cents)
Covered: Yes.
- Primary fixes:
  - Decimal-based normalization and 2-decimal API serialization
  - Consistent UI rendering from canonical string amounts
  - Files:
    - `backend/app/services/reservations.py`
    - `backend/app/api/v1/dashboard.py`
    - `frontend/src/components/RevenueSummary.tsx`
