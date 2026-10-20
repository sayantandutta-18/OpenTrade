"""Database repository functions for persistence and replay."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from impactlab.db.models import (
    EventModel,
    ExperimentModel,
    ExperimentResultModel,
    SessionModel,
)
from impactlab.engine.models import Event


def save_session(
    db: Session,
    session_id: str,
    profile_name: str,
    seed: int,
    config: dict[str, Any] | None = None,
    status: str = "active",
    user_id: str | None = None,
) -> SessionModel:
    """Create or update a simulation session record."""
    config_json = json.dumps(config or {})
    sess = SessionModel(
        id=session_id,
        user_id=user_id,
        profile_id=profile_name,
        seed=seed,
        config_json=config_json,
        status=status,
    )
    db.merge(sess)
    db.commit()
    return sess


def save_events(db: Session, session_id: str, events: list[Event]) -> int:
    """Save a batch of engine events for a session, skipping already existing sequences."""
    if not events:
        return 0

    # Determine highest seq already saved
    existing_max = (
        db.scalar(
            select(func.coalesce(func.max(EventModel.seq), 0)).where(
                EventModel.session_id == session_id
            )
        )
        or 0
    )

    new_models: list[EventModel] = []
    for ev in events:
        if ev.seq > existing_max:
            new_models.append(
                EventModel(
                    session_id=session_id,
                    seq=ev.seq,
                    ts=ev.ts,
                    kind=ev.kind,
                    payload_json=json.dumps(ev.payload),
                )
            )

    if new_models:
        db.bulk_save_objects(new_models)
        db.commit()

    return len(new_models)


def get_session(db: Session, session_id: str) -> SessionModel | None:
    """Retrieve a session by ID."""
    return db.scalar(select(SessionModel).where(SessionModel.id == session_id))


def list_sessions(db: Session, limit: int = 50) -> list[dict[str, Any]]:
    """List recent sessions along with event counts and timestamps."""
    stmt = (
        select(
            SessionModel.id,
            SessionModel.profile_id,
            SessionModel.seed,
            SessionModel.status,
            SessionModel.created_at,
            func.count(EventModel.seq).label("event_count"),
        )
        .outerjoin(EventModel, SessionModel.id == EventModel.session_id)
        .group_by(
            SessionModel.id,
            SessionModel.profile_id,
            SessionModel.seed,
            SessionModel.status,
            SessionModel.created_at,
        )
        .order_by(SessionModel.created_at.desc())
        .limit(limit)
    )

    rows = db.execute(stmt).all()
    return [
        {
            "id": row.id,
            "profile": row.profile_id,
            "seed": row.seed,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else "",
            "event_count": row.event_count,
        }
        for row in rows
    ]


def get_session_events(
    db: Session, session_id: str, from_seq: int = 1
) -> list[dict[str, Any]]:
    """Retrieve sequential events for a session starting from a sequence number."""
    stmt = (
        select(EventModel)
        .where(EventModel.session_id == session_id, EventModel.seq >= from_seq)
        .order_by(EventModel.seq.asc())
    )
    models = db.scalars(stmt).all()
    return [
        {
            "seq": m.seq,
            "ts": m.ts,
            "kind": m.kind,
            "payload": json.loads(m.payload_json),
        }
        for m in models
    ]


def save_experiment(
    db: Session,
    experiment_id: str,
    experiment_type: str,
    params: dict[str, Any],
    master_seed: int,
    runs: int,
    summary: dict[str, Any],
    chart_data: list[dict[str, Any]],
    status: str = "COMPLETED",
    user_id: str | None = None,
) -> ExperimentModel:
    """Persist an experiment result and summary statistics."""
    now = datetime.now(UTC)
    exp = ExperimentModel(
        id=experiment_id,
        user_id=user_id,
        type=experiment_type,
        params_json=json.dumps({**params, "runs": runs}),
        seed=master_seed,
        status=status,
        created_at=now,
        finished_at=now,
    )
    result = ExperimentResultModel(
        experiment_id=experiment_id,
        summary_json=json.dumps(summary),
        charts_json=json.dumps(chart_data),
    )
    db.merge(exp)
    db.merge(result)
    db.commit()
    return exp


def get_experiment(db: Session, experiment_id: str) -> dict[str, Any] | None:
    """Retrieve an experiment result from the database."""
    stmt = (
        select(ExperimentModel, ExperimentResultModel)
        .outerjoin(ExperimentResultModel, ExperimentModel.id == ExperimentResultModel.experiment_id)
        .where(ExperimentModel.id == experiment_id)
    )
    row = db.execute(stmt).first()
    if not row:
        return None
    exp, res = row
    params = json.loads(exp.params_json) if exp.params_json else {}
    return {
        "experiment_id": exp.id,
        "experiment_type": exp.type,
        "status": exp.status,
        "master_seed": exp.seed,
        "runs": params.get("runs", 50),
        "summary": json.loads(res.summary_json) if res and res.summary_json else {},
        "chart_data": json.loads(res.charts_json) if res and res.charts_json else [],
    }


def list_experiments(db: Session, limit: int = 20) -> list[dict[str, Any]]:
    """List recent Monte Carlo experiments."""
    stmt = select(ExperimentModel).order_by(ExperimentModel.created_at.desc()).limit(limit)
    rows = db.scalars(stmt).all()
    return [
        {
            "experiment_id": r.id,
            "experiment_type": r.type,
            "status": r.status,
            "master_seed": r.seed,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]
