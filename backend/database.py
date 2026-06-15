"""
Async Supabase adapter — provides MongoDB-compatible async API via supabase-py.
Set SUPABASE_URL and SUPABASE_SERVICE_KEY in backend/.env.
"""
import os
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent

logger = logging.getLogger(__name__)

_client = None
_executor = ThreadPoolExecutor(max_workers=20)


def _is_missing_relation_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "relation" in msg and "does not exist" in msg
    ) or "could not find the table" in msg or "schema cache" in msg and "not found" in msg


def _get_client():
    global _client
    if _client is None:
        # Load fresh from .env so changes are picked up without restarting
        load_dotenv(ROOT_DIR / ".env", override=True)
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env")
        _client = create_client(url, key)
    return _client


async def _run(fn):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, fn)


# ---------------------------------------------------------------------------
# Filter translator: MongoDB dict → PostgREST query builder
# ---------------------------------------------------------------------------

def _apply_filter(q, filt: dict):
    for key, value in (filt or {}).items():
        if key == "$or":
            parts = []
            for cond in value:
                for k, v in cond.items():
                    if isinstance(v, dict):
                        for op, val in v.items():
                            if op == "$eq":   parts.append(f"{k}.eq.{val}")
                            elif op == "$ne": parts.append(f"{k}.neq.{val}")
                            elif op == "$gt": parts.append(f"{k}.gt.{val}")
                            elif op == "$gte": parts.append(f"{k}.gte.{val}")
                            elif op == "$lt": parts.append(f"{k}.lt.{val}")
                            elif op == "$lte": parts.append(f"{k}.lte.{val}")
                            elif op == "$in":
                                vals = ",".join(str(x) for x in val)
                                parts.append(f"{k}.in.({vals})")
                    elif v is None:
                        parts.append(f"{k}.is.null")
                    else:
                        parts.append(f"{k}.eq.{v}")
            if parts:
                q = q.or_(",".join(parts))
        elif key == "$and":
            for cond in value:
                q = _apply_filter(q, cond)
        elif isinstance(value, dict):
            for op, val in value.items():
                if op == "$eq":    q = q.eq(key, val)
                elif op == "$ne":  q = q.neq(key, val)
                elif op == "$gt":  q = q.gt(key, val)
                elif op == "$gte": q = q.gte(key, val)
                elif op == "$lt":  q = q.lt(key, val)
                elif op == "$lte": q = q.lte(key, val)
                elif op == "$in":  q = q.in_(key, list(val))
                elif op == "$nin": q = q.not_.in_(key, list(val))
                elif op == "$exists":
                    q = q.not_.is_(key, "null") if val else q.is_(key, "null")
                elif op == "$regex": q = q.ilike(key, f"%{val}%")
                elif op == "$options": pass  # ilike is already case-insensitive
        elif value is None:
            q = q.is_(key, "null")
        else:
            q = q.eq(key, value)
    return q


# ---------------------------------------------------------------------------
# Cursor  (mimics Motor's chainable find() cursor)
# ---------------------------------------------------------------------------

class Cursor:
    def __init__(self, table: str, filt: dict):
        self._table = table
        self._filt = filt or {}
        self._sort_key: Optional[str] = None
        self._sort_asc: bool = True
        self._limit_n: Optional[int] = None
        self._skip_n: int = 0

    def sort(self, key_or_list, direction=None):
        if isinstance(key_or_list, list):
            self._sort_key, dir_val = key_or_list[0]
            self._sort_asc = dir_val != -1
        else:
            self._sort_key = key_or_list
            self._sort_asc = direction != -1
        return self

    def limit(self, n: int):
        self._limit_n = n
        return self

    def skip(self, n: int):
        self._skip_n = n
        return self

    async def to_list(self, length: int = None) -> List[dict]:
        table = self._table
        filt = self._filt
        sort_key = self._sort_key
        sort_asc = self._sort_asc
        lim = self._limit_n or length
        skip = self._skip_n

        def _fetch():
            client = _get_client()
            q = client.table(table).select("*")
            q = _apply_filter(q, filt)
            if sort_key:
                q = q.order(sort_key, desc=not sort_asc)
            if skip and lim:
                q = q.range(skip, skip + lim - 1)
            elif lim:
                q = q.limit(lim)
            elif skip:
                q = q.range(skip, skip + 9999)
            try:
                return q.execute().data or []
            except Exception as exc:
                if _is_missing_relation_error(exc):
                    logger.debug("Missing table for cursor fetch: %s", table)
                    return []
                # Supabase HTTP/2 connection drops — return empty rather than 500
                exc_str = str(exc)
                if "RemoteProtocolError" in exc_str or "ConnectionTerminated" in exc_str or "h2" in exc_str.lower():
                    logger.warning("Supabase connection dropped on %s fetch, returning []", table)
                    return []
                raise

        return await _run(_fetch)

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for row in await self.to_list():
            yield row


# ---------------------------------------------------------------------------
# AggregateCursor  (Python-side aggregation for simple pipelines)
# ---------------------------------------------------------------------------

class AggregateCursor:
    def __init__(self, table: str, pipeline: List[dict]):
        self._table = table
        self._pipeline = pipeline

    async def to_list(self, length: int = None) -> List[dict]:
        match_filt: dict = {}
        group_spec = None
        sort_spec: dict = {}
        limit_n = length

        for stage in self._pipeline:
            if "$match" in stage:
                match_filt = stage["$match"]
            elif "$group" in stage:
                group_spec = stage["$group"]
            elif "$sort" in stage:
                sort_spec = stage["$sort"]
            elif "$limit" in stage:
                limit_n = stage["$limit"]

        rows = await Cursor(self._table, match_filt).to_list(10000)
        if group_spec is None:
            return rows[:limit_n] if limit_n else rows

        group_id_expr = group_spec.get("_id")
        groups: Dict[Any, dict] = {}

        for row in rows:
            if group_id_expr is None:
                gid = None
            elif isinstance(group_id_expr, str) and group_id_expr.startswith("$"):
                gid = row.get(group_id_expr[1:])
            else:
                gid = group_id_expr
            groups.setdefault(gid, {"_id": gid, "_rows": []})["_rows"].append(row)

        results = []
        for gid, gdata in groups.items():
            result: dict = {"_id": gid}
            for field, spec in group_spec.items():
                if field == "_id":
                    continue
                if isinstance(spec, dict):
                    op, val = next(iter(spec.items()))
                    col = val[1:] if isinstance(val, str) and val.startswith("$") else None
                    if op == "$sum":
                        result[field] = sum(r.get(col) or 0 for r in gdata["_rows"]) if col else (val or 1) * len(gdata["_rows"])
                    elif op == "$first":
                        result[field] = gdata["_rows"][0].get(col) if gdata["_rows"] and col else None
                    elif op == "$last":
                        result[field] = gdata["_rows"][-1].get(col) if gdata["_rows"] and col else None
                    elif op == "$avg":
                        vals = [r.get(col) or 0 for r in gdata["_rows"] if col]
                        result[field] = sum(vals) / len(vals) if vals else 0
            results.append(result)

        if sort_spec:
            for sk, sd in reversed(list(sort_spec.items())):
                results.sort(key=lambda r: (r.get(sk) is None, r.get(sk)), reverse=(sd == -1))

        return results[:limit_n] if limit_n else results


# ---------------------------------------------------------------------------
# Primary-key detection
# ---------------------------------------------------------------------------

_PK_COLUMNS = [
    "user_id", "employee_id", "session_token", "payrun_id", "payslip_id",
    "transaction_id", "leave_request_id", "leave_id", "document_id",
    "record_id", "entry_id", "policy_id", "training_id", "review_id",
    "absence_id", "cos_id", "rtw_id", "pension_id", "tax_doc_id",
    "invite_token", "pass_id", "audit_id", "company_id", "id",
]


def _pk_filter(row: dict) -> Optional[dict]:
    for col in _PK_COLUMNS:
        if col in row and row[col] is not None:
            return {col: row[col]}
    return None


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

class Collection:
    def __init__(self, table_name: str):
        self._table = table_name

    # ---- find ----------------------------------------------------------------

    async def find_one(self, filt: dict = None, projection: dict = None) -> Optional[dict]:
        table = self._table

        def _fetch():
            client = _get_client()
            q = client.table(table).select("*")
            q = _apply_filter(q, filt or {})
            try:
                result = q.limit(1).execute()
                return result.data[0] if result.data else None
            except Exception as exc:
                if _is_missing_relation_error(exc):
                    logger.debug("Missing table for find_one: %s", table)
                    return None
                raise

        return await _run(_fetch)

    def find(self, filt: dict = None, projection: dict = None) -> Cursor:
        return Cursor(self._table, filt or {})

    # ---- insert --------------------------------------------------------------

    async def insert_one(self, doc: dict) -> Any:
        clean = {k: v for k, v in doc.items() if k != "_id"}
        if not clean:
            return None

        table = self._table

        def _insert():
            import re
            client = _get_client()
            data = clean.copy()
            for _ in range(30):  # max 30 retries for unknown columns
                try:
                    client.table(table).insert(data).execute()
                    return
                except Exception as e:
                    msg = str(e)
                    msg_lower = msg.lower()
                    if _is_missing_relation_error(e):
                        logger.debug("Missing table for insert_one: %s", table)
                        return
                    if "duplicate" in msg_lower or "unique" in msg_lower or "23505" in msg_lower:
                        return  # ignore duplicates
                    # Strip the offending column and retry
                    m = re.search(
                        r"could not find the [\"'](\w+)[\"'] column"
                        r"|column [\"']?(\w+)[\"']? of relation"
                        r"|column (\w+) does not exist",
                        msg, re.IGNORECASE
                    )
                    if m:
                        bad = m.group(1) or m.group(2) or m.group(3)
                        if bad and bad in data:
                            data.pop(bad)
                            continue
                    raise

        await _run(_insert)

        class _R:
            inserted_id = clean.get("id")
        return _R()

    async def insert_many(self, docs: List[dict]) -> Any:
        for doc in docs:
            await self.insert_one(doc)
        return docs

    # ---- update --------------------------------------------------------------

    async def update_one(self, filt: dict, update: dict, upsert: bool = False) -> Any:
        await self._do_update(filt, update, upsert=upsert)

        class _R:
            matched_count = 1
            modified_count = 1
            upserted_id = None
        return _R()

    async def update_many(self, filt: dict, update: dict) -> Any:
        await self._do_update(filt, update, upsert=False)

        class _R:
            matched_count = 1
            modified_count = 1
        return _R()

    async def replace_one(self, filt: dict, replacement: dict, upsert: bool = False) -> Any:
        clean = {k: v for k, v in replacement.items() if k != "_id"}
        existing = await self.find_one(filt)
        if existing:
            await self._do_update(_pk_filter(existing) or filt, {"$set": clean}, upsert=False)
        elif upsert:
            await self.insert_one(clean)

        class _R:
            matched_count = 1 if existing else 0
            modified_count = 1 if existing else 0
        return _R()

    async def _do_update(self, filt: dict, update: dict, upsert: bool):
        set_data: dict = {}

        if "$set" in update:
            set_data.update(update["$set"])

        if "$unset" in update:
            for k in update["$unset"]:
                set_data[k] = None

        if "$inc" in update:
            row = await self.find_one(filt)
            if row:
                for k, amount in update["$inc"].items():
                    set_data[k] = (row.get(k) or 0) + amount

        if any(op in update for op in ("$push", "$addToSet", "$pull")):
            row = await self.find_one(filt)
            if row:
                for op in ("$push", "$addToSet", "$pull"):
                    if op not in update:
                        continue
                    for field, val in update[op].items():
                        raw = row.get(field) or []
                        if isinstance(raw, str):
                            try:
                                raw = json.loads(raw)
                            except Exception:
                                raw = []
                        if not isinstance(raw, list):
                            raw = []
                        if op == "$push":
                            raw = raw + [val]
                        elif op == "$addToSet":
                            if val not in raw:
                                raw = raw + [val]
                        elif op == "$pull":
                            raw = [x for x in raw if x != val]
                        set_data[field] = raw

        if not set_data:
            return

        table = self._table

        def _update():
            import re
            client = _get_client()
            data = set_data.copy()
            for _ in range(30):
                try:
                    q = client.table(table).update(data)
                    q = _apply_filter(q, filt)
                    q.execute()
                    return
                except Exception as e:
                    msg = str(e)
                    if _is_missing_relation_error(e):
                        logger.debug("Missing table for update on %s", table)
                        return
                    m = re.search(
                        r"could not find the [\"'](\w+)[\"'] column"
                        r"|column [\"']?(\w+)[\"']? of relation"
                        r"|column (\w+) does not exist",
                        msg, re.IGNORECASE
                    )
                    if m:
                        bad = m.group(1) or m.group(2) or m.group(3)
                        if bad and bad in data:
                            data.pop(bad)
                            continue
                    raise

        await _run(_update)

    # ---- delete --------------------------------------------------------------

    async def delete_one(self, filt: dict) -> Any:
        row = await self.find_one(filt)
        deleted = 0
        if row:
            pk = _pk_filter(row) or filt
            table = self._table

            def _delete():
                client = _get_client()
                q = client.table(table).delete()
                q = _apply_filter(q, pk)
                try:
                    q.execute()
                except Exception as exc:
                    if _is_missing_relation_error(exc):
                        logger.debug("Missing table for delete_one: %s", table)
                        return
                    raise

            await _run(_delete)
            deleted = 1

        class _R:
            deleted_count = deleted
        return _R()

    async def delete_many(self, filt: dict) -> Any:
        if not filt:
            class _R:
                deleted_count = 0
            return _R()

        table = self._table

        def _delete():
            client = _get_client()
            q = client.table(table).delete()
            q = _apply_filter(q, filt)
            try:
                q.execute()
            except Exception as exc:
                if _is_missing_relation_error(exc):
                    logger.debug("Missing table for delete_many: %s", table)
                    return
                raise

        await _run(_delete)

        class _R:
            deleted_count = -1
        return _R()

    # ---- misc ----------------------------------------------------------------

    async def count_documents(self, filt: dict = None) -> int:
        table = self._table

        def _count():
            client = _get_client()
            q = client.table(table).select("*", count="exact")
            q = _apply_filter(q, filt or {})
            try:
                result = q.limit(0).execute()
                return result.count or 0
            except Exception as exc:
                if _is_missing_relation_error(exc):
                    logger.debug("Missing table for count_documents: %s", table)
                    return 0
                raise

        return await _run(_count)

    async def estimated_document_count(self) -> int:
        return await self.count_documents()

    def aggregate(self, pipeline: List[dict]) -> AggregateCursor:
        return AggregateCursor(self._table, pipeline)

    async def create_index(self, *args, **kwargs):
        pass

    async def drop(self):
        logger.debug("drop() called on %s - ignored", self._table)


# ---------------------------------------------------------------------------
# Database  (attribute access → Collection)
# ---------------------------------------------------------------------------

class Database:
    def __getattr__(self, name: str) -> Collection:
        return Collection(name)

    def __getitem__(self, name: str) -> Collection:
        return Collection(name)


# Single shared instance — import this everywhere
db = Database()
