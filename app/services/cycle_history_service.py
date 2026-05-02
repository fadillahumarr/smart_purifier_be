from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_decision import AIDecision
from app.models.cycle_result import CycleResult
from app.models.purification_cycle import PurificationCycle
from app.models.water_purifier import WaterPurifier
from app.schemas.cycle_history import CycleHistoryItemOut, CycleHistoryResponseOut


def bool_to_label(value: bool | None) -> str | None:
    if value is None:
        return None
    return "Clean" if value else "Not Clean"


def make_cycle_code(index: int) -> str:
    return f"CYCLE-{index:03d}"


async def get_cycle_history(
    session: AsyncSession,
    purifier_id: UUID,
    limit: int = 20,
) -> CycleHistoryResponseOut:
    purifier = await session.get(WaterPurifier, purifier_id)
    if not purifier:
        raise ValueError("Purifier not found")

    stmt = (
        select(
            PurificationCycle.id,
            PurificationCycle.started_at,
            PurificationCycle.status,
            AIDecision.predicted_is_clean_water,
            CycleResult.is_clean_water,
        )
        .select_from(PurificationCycle)
        .outerjoin(
            AIDecision,
            AIDecision.purification_cycle_id == PurificationCycle.id,
        )
        .outerjoin(
            CycleResult,
            CycleResult.purification_cycle_id == PurificationCycle.id,
        )
        .where(PurificationCycle.water_purifier_id == purifier_id)
        .order_by(desc(PurificationCycle.started_at))
        .limit(limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    items: list[CycleHistoryItemOut] = []
    for idx, row in enumerate(rows, start=1):
        cycle_uuid, started_at, status, predicted_bool, actual_bool = row

        items.append(
            CycleHistoryItemOut(
                cycle_uuid=cycle_uuid,
                cycle_code=make_cycle_code(idx),
                started_at=started_at,
                status=status,
                predicted=bool_to_label(predicted_bool),
                actual=bool_to_label(actual_bool),
            )
        )

    return CycleHistoryResponseOut(
        purifier_id=purifier_id,
        items=items,
    )
