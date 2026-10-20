"""Routes for executing, querying, and persisting Monte Carlo experiments."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from impactlab.api.schemas import ExperimentCreateRequest, ExperimentResponse
from impactlab.db import repository
from impactlab.db.session import get_db
from impactlab.experiments.runner import run_experiment

router = APIRouter(prefix="/experiments", tags=["experiments"])

# In-memory fast cache
_EXPERIMENTS_STORE: dict[str, ExperimentResponse] = {}


@router.get("", response_model=list[dict[str, Any]])
def list_experiments_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """List recent Monte Carlo experiments."""
    return repository.list_experiments(db, limit=limit)


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
def create_experiment(
    req: ExperimentCreateRequest,
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """Trigger a Monte Carlo experiment across N runs."""
    try:
        res = run_experiment(
            experiment_type=req.type,
            params=req.params,
            master_seed=req.seed,
            runs=req.runs,
            max_workers=4,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Experiment failed: {e}",
        ) from e

    exp_response = ExperimentResponse(
        experiment_id=res.experiment_id,
        experiment_type=res.experiment_type,
        status="COMPLETED",
        master_seed=res.master_seed,
        runs=res.runs,
        summary=res.summary,
        chart_data=res.chart_data,
    )
    _EXPERIMENTS_STORE[res.experiment_id] = exp_response

    # Persist to database
    repository.save_experiment(
        db,
        experiment_id=res.experiment_id,
        experiment_type=res.experiment_type,
        params=req.params,
        master_seed=res.master_seed,
        runs=res.runs,
        summary=res.summary,
        chart_data=res.chart_data,
        status="COMPLETED",
    )

    return exp_response


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """Retrieve results for an experiment from cache or database."""
    data = _EXPERIMENTS_STORE.get(experiment_id)
    if data:
        return data

    db_data = repository.get_experiment(db, experiment_id)
    if not db_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found",
        )

    return ExperimentResponse(
        experiment_id=db_data["experiment_id"],
        experiment_type=db_data["experiment_type"],
        status=db_data["status"],
        master_seed=db_data["master_seed"],
        runs=db_data["runs"],
        summary=db_data["summary"],
        chart_data=db_data["chart_data"],
    )
