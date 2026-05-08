import csv
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from io import BytesIO, StringIO

from openpyxl import Workbook

from app.core.config import settings
from app.repositories import export_job_repository, emotion_event_repository
from app.services.minio_service import MinioService
from app.services.monitoring_service import _fetch_supervisor_agents


PERU_TZ = timezone(timedelta(hours=-5))
UTC_TZ = timezone.utc

EMOTION_ORDER = [
    "neutral",
    "happy",
    "sad",
    "surprise",
    "fear",
    "disgust",
    "anger",
]


class ExportDomainError(ValueError):
    pass


def _local_date_range_to_utc(start_date, end_date):
    start_local = datetime.combine(start_date, time.min).replace(tzinfo=PERU_TZ)
    end_local = datetime.combine(end_date, time.max).replace(tzinfo=PERU_TZ)

    return start_local.astimezone(UTC_TZ), end_local.astimezone(UTC_TZ)


def _to_peru(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(PERU_TZ)


def _build_period_key(dt: datetime, group_by: str) -> str:
    dt_peru = _to_peru(dt)

    if group_by == "day":
        return dt_peru.strftime("%Y-%m-%d")

    if group_by == "week":
        year, week, _ = dt_peru.isocalendar()
        return f"{year}-W{week:02d}"

    if group_by == "month":
        return dt_peru.strftime("%Y-%m")

    raise ExportDomainError("invalid_group_by")


def _build_csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b"Sin datos\n"

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def _build_xlsx_bytes(rows: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte"

    if not rows:
        ws.append(["Sin datos"])
    else:
        headers = list(rows[0].keys())
        ws.append(headers)

        for row in rows:
            ws.append([row.get(header) for header in headers])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def _aggregate_records(records: list[dict], group_by: str, aggregates: list[str]) -> list[dict]:
    buckets = defaultdict(
        lambda: {
            "total_records": 0,
            "emotion_counts": {emotion: 0 for emotion in EMOTION_ORDER},
        }
    )

    for record in records:
        period = _build_period_key(record["timestamp"], group_by)
        emotion = record["emotion"]

        buckets[period]["total_records"] += 1

        if emotion in buckets[period]["emotion_counts"]:
            buckets[period]["emotion_counts"][emotion] += 1

    rows = []

    for period in sorted(buckets.keys()):
        bucket = buckets[period]
        total_records = bucket["total_records"]
        emotion_counts = bucket["emotion_counts"]

        row = {
            "period": period,
        }

        if "emotion_count" in aggregates:
            for emotion in EMOTION_ORDER:
                row[f"{emotion}_count"] = emotion_counts[emotion]

        if "emotion_percentage" in aggregates:
            for emotion in EMOTION_ORDER:
                percentage = (emotion_counts[emotion] / total_records * 100) if total_records else 0
                row[f"{emotion}_percentage"] = round(percentage, 2)

        if "dominant_emotion" in aggregates:
            dominant_emotion = max(
                EMOTION_ORDER,
                key=lambda emotion: emotion_counts[emotion],
            )
            row["dominant_emotion"] = dominant_emotion

        rows.append(row)

    return rows


def _build_current_rows(snapshot: list[dict]) -> list[dict]:
    return [
        {
            "name": row["name"],
            "emotion_label": row["emotion_label"],
            "updated_at": row["updated_at"],
        }
        for row in snapshot
    ]


async def _resolve_supervisor_agent_ids(supervisor_id: str) -> list[str]:
    agents = await _fetch_supervisor_agents(supervisor_id)
    return [str(agent["id"]) for agent in agents]


async def create_export_job(supervisor_id: str, payload) -> str:
    params: dict = {}

    if payload.type == "current":
        params = {
            "snapshot": [item.model_dump() for item in payload.snapshot],
        }

    elif payload.type == "team":
        params = {
            "start_date": payload.start_date.isoformat(),
            "end_date": payload.end_date.isoformat(),
            "group_by": payload.group_by,
            "aggregates": payload.aggregates,
        }

    elif payload.type == "agent":
        params = {
            "agent_id": payload.agent_id,
            "start_date": payload.start_date.isoformat(),
            "end_date": payload.end_date.isoformat(),
            "group_by": payload.group_by,
            "aggregates": payload.aggregates,
        }

    document = {
        "requested_by": supervisor_id,
        "requested_at": datetime.now(timezone.utc),
        "status": "processing",
        "type": payload.type,
        "format": payload.format,
        "params": params,
        "file": None,
        "error": None,
        "completed_at": None,
    }

    return await export_job_repository.create_export_job(document)


async def process_export_job(job_id: str):
    minio_service = MinioService()

    try:
        minio_service.ensure_bucket()

        job = await export_job_repository.get_export_job_by_id(job_id)
        if not job:
            return

        export_type = job["type"]
        export_format = job["format"]
        params = job["params"]
        requested_by = job["requested_by"]

        rows: list[dict] = []
        file_name = ""

        if export_type == "current":
            rows = _build_current_rows(params["snapshot"])
            file_name = f"current_export_{job_id}.{export_format}"

        elif export_type == "team":
            supervisor_agent_ids = await _resolve_supervisor_agent_ids(requested_by)

            start_utc, end_utc = _local_date_range_to_utc(
                datetime.fromisoformat(params["start_date"]).date(),
                datetime.fromisoformat(params["end_date"]).date(),
            )

            events = await emotion_event_repository.get_emotion_events_between(
                start=start_utc,
                end=end_utc,
                agent_ids=supervisor_agent_ids,
            )

            rows = _aggregate_records(
                records=events,
                group_by=params["group_by"],
                aggregates=params["aggregates"],
            )

            file_name = (
                f"team_emotions_{params['start_date']}_{params['end_date']}.{export_format}"
            )

        elif export_type == "agent":
            start_utc, end_utc = _local_date_range_to_utc(
                datetime.fromisoformat(params["start_date"]).date(),
                datetime.fromisoformat(params["end_date"]).date(),
            )

            events = await emotion_event_repository.get_emotion_events_between(
                start=start_utc,
                end=end_utc,
                agent_ids=[params["agent_id"]],
            )

            rows = _aggregate_records(
                records=events,
                group_by=params["group_by"],
                aggregates=params["aggregates"],
            )

            file_name = (
                f"agent_emotions_{params['agent_id']}_{params['start_date']}_{params['end_date']}.{export_format}"
            )

        else:
            raise ExportDomainError("invalid_export_type")

        if export_format == "csv":
            file_bytes = _build_csv_bytes(rows)
            content_type = "text/csv"
        elif export_format == "xlsx":
            file_bytes = _build_xlsx_bytes(rows)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            raise ExportDomainError("invalid_export_format")

        object_key = f"jobs/{job_id}/{file_name}"

        minio_service.upload_bytes(
            object_key=object_key,
            payload=file_bytes,
            content_type=content_type,
        )

        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.EXPORT_FILE_TTL_MINUTES
        )

        await export_job_repository.mark_export_job_completed(
            job_id=job_id,
            file_data={
                "bucket": settings.MINIO_BUCKET,
                "object_key": object_key,
                "file_name": file_name,
                "content_type": content_type,
                "expires_at": expires_at,
            },
        )

    except Exception as e:
        await export_job_repository.mark_export_job_failed(job_id, str(e))


async def get_export_job(job_id: str):
    return await export_job_repository.get_export_job_by_id(job_id)