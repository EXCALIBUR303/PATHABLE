"""Defined physical-edge/report aggregates; never join evidence into report counts."""

from datetime import timedelta

from sqlalchemy import func, select

from app.core.errors import Problem
from app.models.entities import Campus, Infrastructure, PathEdge
from app.models.reporting import EdgeRestriction, ObstacleReport
from app.services import graph


def analytics(db, campus_id, from_time, to_time):
    if (
        not from_time.tzinfo
        or not to_time.tzinfo
        or not timedelta(0) < to_time - from_time <= timedelta(days=366)
    ):
        raise Problem(
            422, "INVALID_WINDOW", "Use a UTC-aware increasing window of at most 366 days"
        )
    campus = graph.require_row(db, Campus, campus_id)
    graph.expire_observations(db, campus_id)
    now = db.scalar(select(func.clock_timestamp()))
    current = (
        (PathEdge.verification == "verified")
        & (PathEdge.verified_at <= now)
        & (PathEdge.verified_until > now)
    )
    edge_counts = db.execute(
        select(
            func.count(),
            func.count().filter((PathEdge.accessibility == "accessible") & current),
            func.count().filter(PathEdge.accessibility == "unknown"),
            func.count().filter(PathEdge.verification == "needs_review"),
            func.count().filter(PathEdge.verification == "unverified"),
            func.coalesce(func.sum(PathEdge.distance_m), 0),
            func.coalesce(
                func.sum(PathEdge.distance_m).filter(
                    (PathEdge.accessibility != "unknown") & current
                ),
                0,
            ),
        )
        .select_from(PathEdge)
        .where(PathEdge.campus_id == campus_id, PathEdge.active)
    ).one()
    infrastructure = db.scalar(
        select(func.count())
        .select_from(Infrastructure)
        .where(Infrastructure.campus_id == campus_id, Infrastructure.active)
    )
    active_reports = db.scalar(
        select(func.count())
        .select_from(ObstacleReport)
        .where(
            ObstacleReport.campus_id == campus_id,
            ObstacleReport.status == "verified",
            select(EdgeRestriction.id)
            .where(
                EdgeRestriction.report_id == ObstacleReport.id,
                EdgeRestriction.released_at.is_(None),
            )
            .exists(),
        )
    )
    pending = db.scalar(
        select(func.count())
        .select_from(ObstacleReport)
        .where(ObstacleReport.campus_id == campus_id, ObstacleReport.status == "pending_review")
    )
    categories = db.execute(
        select(ObstacleReport.category, func.count())
        .where(
            ObstacleReport.campus_id == campus_id,
            ObstacleReport.created_at >= from_time,
            ObstacleReport.created_at < to_time,
        )
        .group_by(ObstacleReport.category)
        .order_by(ObstacleReport.category)
    ).all()
    resolved = (
        (ObstacleReport.campus_id == campus_id)
        & (ObstacleReport.status == "resolved")
        & (ObstacleReport.resolved_at >= from_time)
        & (ObstacleReport.resolved_at < to_time)
    )
    count, average = db.execute(
        select(
            func.count(),
            func.avg(func.extract("epoch", ObstacleReport.resolved_at - ObstacleReport.created_at)),
        )
        .select_from(ObstacleReport)
        .where(resolved)
    ).one()
    day = func.to_char(func.timezone("UTC", ObstacleReport.resolved_at), "YYYY-MM-DD")
    trend = db.execute(select(day, func.count()).where(resolved).group_by(day).order_by(day)).all()
    return {
        "campus_id": campus_id,
        "data_origin": campus.data_origin,
        "as_of": now,
        "from_time": from_time,
        "to_time": to_time,
        "mapped_infrastructure_count": infrastructure,
        "active_physical_pathways": edge_counts[0],
        "verified_accessible_pathways": edge_counts[1],
        "unknown_accessibility_pathways": edge_counts[2],
        "needs_review_pathways": edge_counts[3],
        "unverified_pathways": edge_counts[4],
        "active_verified_obstacles": active_reports,
        "pending_reports": pending,
        "category_distribution": [
            {"category": category, "count": total} for category, total in categories
        ],
        "submitted_report_count": sum(total for _, total in categories),
        "resolution_trend": [{"day": date, "count": total} for date, total in trend],
        "resolved_report_count": count,
        "average_resolution_seconds": float(average) if average is not None else None,
        "mapping_known_current_length_m": edge_counts[6],
        "mapping_total_length_m": edge_counts[5],
        "accessibility_mapping_coverage": edge_counts[6] / edge_counts[5]
        if edge_counts[5]
        else None,
    }
