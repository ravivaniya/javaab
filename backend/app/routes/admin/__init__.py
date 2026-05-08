"""
Admin API router — assembled from sub-modules.

All routes are mounted under /admin in main.py.
Auth is handled per-route via Depends(get_current_admin), NOT by a global
middleware, so the login endpoint itself is unauthenticated.

Route map:
    /admin/auth/login           POST  — issue JWT
    /admin/auth/logout          POST  — clear cookie
    /admin/auth/me              GET   — current admin identity

    /admin/clients              GET   — list clients
    /admin/clients              POST  — create client
    /admin/clients/:id          GET   — detail + ledger + usage
    /admin/clients/:id          PUT   — update editable fields
    /admin/clients/:id/rotate-key    POST — rotate API key
    /admin/clients/:id/suspend       POST — deactivate
    /admin/clients/:id/reactivate    POST — reactivate
    /admin/clients/:id/topup         POST — add credits
    /admin/clients/:id/adjust        POST — signed adjustment
    /admin/clients/:id/ledger        GET  — paginated ledger

    /admin/analytics/overview               GET — 30-day platform summary
    /admin/analytics/clients-burning-fast   GET — burn-rate alert list
"""
from fastapi import APIRouter

from app.routes.admin import analytics, auth, clients, credits

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["admin-auth"])
router.include_router(clients.router, prefix="/clients", tags=["admin-clients"])
router.include_router(credits.router, prefix="/clients", tags=["admin-credits"])
router.include_router(analytics.router, prefix="/analytics", tags=["admin-analytics"])
