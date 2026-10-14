"""JSON shapes shared by the routes and the stream."""
from harness.facts import records  # noqa: F401  (re-exported for the routes)


def calls_json(calls) -> list[dict]:
    return [c.to_json(i + 1) for i, c in enumerate(calls)]


def sentences_json(badges) -> list[dict]:
    return [{"text": b["sentence"], "status": b["status"], "numbers": b.get("numbers", [])} for b in badges]


def brief_json(res: dict, status: str = "draft", writer: str | None = None) -> dict:
    return {"run_id": res["run_id"], "region": res["region"], "month": res["month"], "created_at": res["created_at"],
            "status": status, "model": res["model"], "writer": writer, "sentences": sentences_json(res.get("badges", [])),
            "removed": res.get("flagged", []), "verified_text": res["verified_text"], "draft": res["draft"],
            "calls": calls_json(res.get("calls", []))}
