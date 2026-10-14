"""The trust boundary: the only values that ever reach SQL are an allowlisted region, a month that exists in the
data, and an agency name looked up from its id."""
from fastapi import HTTPException

from fairshare import db
from harness import summary
from harness.facts import records


def scope(region: str, month: str) -> tuple[str, str]:
    try:
        return summary._check_scope(region, month)
    except ValueError as e:
        raise HTTPException(422, {"code": "invalid_scope", "message": str(e)})


def agencies() -> list[dict]:
    """Read per call, never cached across viewers: with Unity Catalog row filters each viewer sees their own agencies."""
    return records(db.query("SELECT agency_id, agency_name, agency_type, region, account_manager FROM aa_demo.gold.dim_agency ORDER BY agency_name"), 1000)


def agency(agency_id: int) -> dict:
    for a in agencies():
        if a["agency_id"] == agency_id:
            return a
    raise HTTPException(422, {"code": "unknown_agency", "message": "That agency is not in the data."})
