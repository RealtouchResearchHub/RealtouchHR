import os
import re
import time
import logging
import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory cache: key -> (timestamp, data)
_cache: dict = {}
CACHE_TTL = 3600  # 1 hour

INACTIVE_STATUSES = {
    "dissolved", "liquidation", "administration",
    "voluntary-arrangement", "converted-closed",
    "insolvency-proceedings", "receivership",
}

_COMPANY_NUMBER_RE = re.compile(r'^[A-Z0-9]{6,8}$')


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, data):
    _cache[key] = (time.time(), data)
    # Evict entries if cache grows too large
    if len(_cache) > 2000:
        cutoff = time.time() - CACHE_TTL
        stale = [k for k, v in _cache.items() if v[0] < cutoff]
        for k in stale:
            _cache.pop(k, None)


def _get_api_key() -> str:
    return os.environ.get("COMPANIES_HOUSE_API_KEY", "")


def _extract_fields(item: dict) -> dict:
    """Normalise a Companies House API item into the required field set.

    Search results and profile endpoints use different field names:
    - Search: 'title' for company name, 'address' for address object
    - Profile: 'company_name', 'registered_office_address'
    """
    # Company name: search uses 'title', profile uses 'company_name'
    company_name = item.get("company_name") or item.get("title", "")

    # Address object: search uses 'address', profile uses 'registered_office_address'
    addr_raw = item.get("registered_office_address") or item.get("address") or {}

    # Build a readable address string (include premises if present)
    addr_parts = [
        addr_raw.get("premises", ""),
        addr_raw.get("address_line_1", ""),
        addr_raw.get("address_line_2", ""),
        addr_raw.get("locality", ""),
        addr_raw.get("region", ""),
        addr_raw.get("postal_code", ""),
        addr_raw.get("country", ""),
    ]
    address_str = ", ".join(p for p in addr_parts if p)

    # accounts_next_due may be nested differently between search and profile
    accounts_next_due = ""
    if "accounts" in item and isinstance(item["accounts"], dict):
        accounts_next_due = item["accounts"].get("next_due", "") or item["accounts"].get("next_made_up_to", "")
    elif "accounts_next_made_up_to" in item:
        accounts_next_due = item.get("accounts_next_made_up_to", "")

    conf_next_due = ""
    if "confirmation_statement" in item and isinstance(item["confirmation_statement"], dict):
        conf_next_due = item["confirmation_statement"].get("next_due", "")
    elif "confirmation_statement_next_made_up_to" in item:
        conf_next_due = item.get("confirmation_statement_next_made_up_to", "")

    return {
        "company_name": company_name,
        "company_number": item.get("company_number", ""),
        "company_status": item.get("company_status", ""),
        "company_type": item.get("company_type", ""),
        "date_of_creation": item.get("date_of_creation", ""),
        "registered_office_address": addr_raw,
        "registered_office_address_str": address_str,
        "sic_codes": item.get("sic_codes", []),
        "jurisdiction": item.get("jurisdiction", ""),
        "accounts_next_due": accounts_next_due,
        "confirmation_statement_next_due": conf_next_due,
    }


def _status_warning(status: str) -> str | None:
    s = (status or "").lower().replace(" ", "-")
    if s in INACTIVE_STATUSES:
        return (
            f"This company has a status of '{status}'. "
            "Please verify this is the correct company before proceeding."
        )
    return None


@router.get("/company-lookup/search")
async def company_lookup_search(query: str = Query(..., min_length=1)):
    """
    Search Companies House by company name or number.
    No authentication required — used during registration.
    """
    api_key = _get_api_key()
    if not api_key:
        return {"items": [], "exact_match": False, "message": "Companies House lookup not available"}

    query = query.strip()
    query_upper = query.upper()

    # If the query looks like a company number, do a direct lookup first
    if _COMPANY_NUMBER_RE.match(query_upper):
        cached = _cache_get(f"profile:{query_upper}")
        if cached:
            item = _extract_fields(cached)
            item["warning"] = _status_warning(item["company_status"])
            return {"items": [item], "exact_match": True}

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(
                    f"https://api.companieshouse.gov.uk/company/{query_upper}",
                    auth=(api_key, ""),
                )
                if r.status_code == 200:
                    data = r.json()
                    _cache_set(f"profile:{query_upper}", data)
                    item = _extract_fields(data)
                    item["warning"] = _status_warning(item["company_status"])
                    return {"items": [item], "exact_match": True}
                if r.status_code == 404:
                    return {"items": [], "exact_match": False}
        except Exception as exc:
            logger.error("CH direct lookup error: %s", type(exc).__name__)
            # Fall through to name search

    # Name-based search
    cache_key = f"search:{query.lower()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                "https://api.companieshouse.gov.uk/search/companies",
                params={"q": query, "items_per_page": 10},
                auth=(api_key, ""),
            )
            r.raise_for_status()
            raw = r.json()
            items = []
            for raw_item in raw.get("items", []):
                item = _extract_fields(raw_item)
                item["warning"] = _status_warning(item["company_status"])
                items.append(item)
            result = {"items": items, "exact_match": False}
            _cache_set(cache_key, result)
            return result
    except httpx.HTTPStatusError as exc:
        logger.error("CH search HTTP %d", exc.response.status_code)
        return {"items": [], "exact_match": False, "error": "Search temporarily unavailable"}
    except Exception as exc:
        logger.error("CH search error: %s", type(exc).__name__)
        return {"items": [], "exact_match": False, "error": "Search temporarily unavailable"}


@router.get("/company-lookup/profile/{company_number}")
async def company_lookup_profile(company_number: str):
    """
    Fetch full company profile from Companies House by company number.
    No authentication required — used during registration.
    """
    api_key = _get_api_key()
    if not api_key:
        raise HTTPException(status_code=503, detail="Companies House lookup not available")

    company_number = company_number.upper().strip()

    cached = _cache_get(f"profile:{company_number}")
    if cached:
        item = _extract_fields(cached)
        item["warning"] = _status_warning(item["company_status"])
        return item

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                f"https://api.companieshouse.gov.uk/company/{company_number}",
                auth=(api_key, ""),
            )
            if r.status_code == 404:
                raise HTTPException(status_code=404, detail="Company not found")
            r.raise_for_status()
            data = r.json()
            _cache_set(f"profile:{company_number}", data)
            item = _extract_fields(data)
            item["warning"] = _status_warning(item["company_status"])
            return item
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        logger.error("CH profile HTTP %d", exc.response.status_code)
        raise HTTPException(status_code=502, detail="Companies House lookup temporarily unavailable")
    except Exception as exc:
        logger.error("CH profile error: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Companies House lookup temporarily unavailable")
