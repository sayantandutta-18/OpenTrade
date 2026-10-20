"""SQLAlchemy database models for ImpactLab.

Follows the schema specified in context.md Section 12:
- stock_profiles(id, name, params_json, created_at)
- sessions(id, user_id nullable, profile_id, seed, config_json, status, created_at)
- events(session_id, seq, ts, kind, payload_json, PRIMARY KEY(session_id, seq))
- experiments(id, user_id nullable, type, params_json, seed, status, created_at, finished_at)
- experiment_runs(id, experiment_id, run_index, seed, metrics_json)
- experiment_results(experiment_id, summary_json, charts_json)
- users(id, email, created_at)
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for all ImpactLab tables."""

    pass


class UserModel(Base):
    """User account model (v1)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    sessions: Mapped[list[SessionModel]] = relationship("SessionModel", back_populates="user")


class StockProfileModel(Base):
    """Stock profile parameters model."""

    __tablename__ = "stock_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    params_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class SessionModel(Base):
    """Simulation session model."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.id"), nullable=True, index=True
    )
    profile_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    user: Mapped[UserModel | None] = relationship("UserModel", back_populates="sessions")
    events: Mapped[list[EventModel]] = relationship(
        "EventModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="EventModel.seq",
    )


class EventModel(Base):
    """Engine event log model for deterministic replay.

    Primary key is composite (session_id, seq).
    """

    __tablename__ = "events"

    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)

    session: Mapped[SessionModel] = relationship("SessionModel", back_populates="events")

    __table_args__ = (Index("ix_events_session_seq", "session_id", "seq"),)


class ExperimentModel(Base):
    """Monte Carlo experiment metadata model."""

    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    params_json: Mapped[str] = mapped_column(Text, nullable=False)
    seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    runs: Mapped[list[ExperimentRunModel]] = relationship(
        "ExperimentRunModel",
        back_populates="experiment",
        cascade="all, delete-orphan",
    )
    result: Mapped[ExperimentResultModel | None] = relationship(
        "ExperimentResultModel",
        back_populates="experiment",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ExperimentRunModel(Base):
    """Individual Monte Carlo run within an experiment."""

    __tablename__ = "experiment_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_index: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)

    experiment: Mapped[ExperimentModel] = relationship("ExperimentModel", back_populates="runs")


class ExperimentResultModel(Base):
    """Aggregated experiment outcome and charts."""

    __tablename__ = "experiment_results"

    experiment_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("experiments.id", ondelete="CASCADE"), primary_key=True
    )
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    charts_json: Mapped[str] = mapped_column(Text, nullable=False)

    experiment: Mapped[ExperimentModel] = relationship("ExperimentModel", back_populates="result")
