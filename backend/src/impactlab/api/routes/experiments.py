"""Routes for executing and querying Monte Carlo experiments."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from impactlab.api.schemas import ExperimentCreateRequest, ExperimentResponse
from impactlab.experiments.runner import run_experiment

router = APIRouter(prefix="/experiments", tags=["experiments"])

# In-memory storage for experiment results
_EXPERIMENTS_STORE: dict[str, ExperimentResponse] = {}


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
def create_experiment(req: ExperimentCreateRequest) -> ExperimentResponse:
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
    return exp_response


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(experiment_id: str) -> ExperimentResponse:
    """Retrieve results for an experiment."""
    data = _EXPERIMENTS_STORE.get(experiment_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found",
        )
    return data
