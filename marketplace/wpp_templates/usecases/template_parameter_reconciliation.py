import csv
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from typing import Dict, List, Optional

from django.conf import settings
from django.db.models import Q
from django_redis import get_redis_connection

from marketplace.applications.models import App
from marketplace.core.pacing.constants import TTL_WHATSAPP_TEMPLATES
from marketplace.core.pacing.ttl import is_recently_synced, mark_synced
from marketplace.wpp_templates.models import TemplateTranslation
from marketplace.wpp_templates.parameters import (
    PARAMETER_FORMAT_NAMED,
    build_translation_parameters,
    extract_named_placeholders,
)
from marketplace.wpp_templates.tasks import (
    TEMPLATE_SYNC_APP_CODES,
    _apps_for_waba,
    _resolve_waba_id,
)
from marketplace.wpp_templates.usecases.template_sync import TemplateSyncUseCase


PROGRESS_KEY = "template_param_reconcile:progress"
PROGRESS_TTL_SECONDS = 60 * 60 * 24

CSV_FIELDS = [
    "run_id",
    "project_uuid",
    "app_uuid",
    "app_code",
    "waba_id",
    "template_name",
    "template_uuid",
    "translation_uuid",
    "language",
    "message_template_id",
    "category",
    "previously_broken",
    "format_before",
    "format_after",
    "param_names_before",
    "param_names_after",
    "anomaly_type",
    "anomaly_body_names",
    "anomaly_example_names",
    "reason",
]

EMPTY_COUNTERS = {
    "corrected": 0,
    "unchanged": 0,
    "anomalous": 0,
    "format_not_yet_known": 0,
    "unclassifiable": 0,
    "previously_broken": 0,
    "skipped_recent_sync": 0,
}

CLASSIFIED_CATEGORIES = frozenset({"corrected", "unchanged", "anomalous"})


class ReconciliationError(Exception):
    """Raised when a reconciliation run cannot start or cannot write its artifact."""


class ReconciliationCannotStartError(ReconciliationError):
    pass


class ReconciliationCannotWriteError(ReconciliationError):
    pass


@dataclass(frozen=True)
class ReconciliationResult:
    run_id: str
    rows: List[dict]
    counters: Dict[str, int]
    resumed: bool

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "rows": self.rows,
            "counters": dict(self.counters),
            "resumed": self.resumed,
        }


@dataclass(frozen=True)
class _TranslationSnapshot:
    translation_pk: int
    project_uuid: str
    app_uuid: str
    app_code: str
    waba_id: str
    template_name: str
    template_uuid: str
    translation_uuid: str
    language: str
    message_template_id: str
    body: str
    parameter_format: Optional[str]
    body_named_params: List[dict]
    variable_count: Optional[int]
    sync_disabled: bool


@dataclass(frozen=True)
class _PostState:
    parameter_format: Optional[str]
    body_named_params: List[dict]
    parameter_anomaly: Optional[dict]


class TemplateParameterReconciliationUseCase:
    def __init__(
        self,
        redis_conn=None,
        sync_use_case_factory=None,
        apps_for_waba=None,
        sleep=time.sleep,
        logger=None,
    ):
        self.redis_conn = (
            redis_conn if redis_conn is not None else get_redis_connection()
        )
        self.sync_use_case_factory = sync_use_case_factory or TemplateSyncUseCase
        self.apps_for_waba = apps_for_waba or _apps_for_waba
        self.sleep = sleep
        self.logger = logger or logging.getLogger(__name__)

    def execute(
        self,
        waba_ids: Optional[List[str]] = None,
        app_uuids: Optional[List[str]] = None,
        dry_run: bool = False,
        restart: bool = False,
        limit: Optional[int] = None,
        output: Optional[str] = None,
        budget: Optional[int] = None,
    ) -> ReconciliationResult:
        started = time.monotonic()
        budget = self._resolve_budget(budget)
        pace_seconds = 60 / budget

        progress, run_id, resumed = self._load_or_start_progress(restart)
        output_path = output or f"reconciliation-{run_id}.csv"

        target_wabas = self._resolve_target_wabas(waba_ids, app_uuids)
        remaining = [
            waba_id
            for waba_id in target_wabas
            if waba_id not in progress["done_waba_ids"]
        ]
        if limit is not None:
            remaining = remaining[:limit]

        self.logger.info(
            f"Template parameter reconciliation start run_id={run_id} "
            f"target_waba_count={len(target_wabas)} remaining={len(remaining)} "
            f"dry_run={dry_run} resumed={resumed}"
        )

        rows: List[dict] = []
        if not remaining:
            if not resumed:
                self._write_header_only(output_path)
            self._log_run_end(
                run_id, progress["counters"], output_path, time.monotonic() - started
            )
            return ReconciliationResult(
                run_id=run_id,
                rows=rows,
                counters=progress["counters"],
                resumed=resumed,
            )

        writer_file, writer = self._open_artifact(
            output_path,
            write_header=not (
                resumed and os.path.exists(output_path) and progress.get("rows_written")
            ),
        )
        try:
            total = len(remaining)
            for position, waba_id in enumerate(remaining, start=1):
                self._process_waba(
                    waba_id=waba_id,
                    position=position,
                    total=total,
                    dry_run=dry_run,
                    run_id=run_id,
                    progress=progress,
                    rows=rows,
                    writer=writer,
                    writer_file=writer_file,
                )
                self.sleep(pace_seconds)
        except ReconciliationCannotWriteError:
            raise
        except OSError as exc:
            raise ReconciliationCannotWriteError(
                f"Unable to write reconciliation artifact {output_path}: {exc}"
            ) from exc
        finally:
            writer_file.close()

        self._log_run_end(
            run_id, progress["counters"], output_path, time.monotonic() - started
        )
        return ReconciliationResult(
            run_id=run_id,
            rows=rows,
            counters=progress["counters"],
            resumed=resumed,
        )

    def _resolve_budget(self, budget: Optional[int]) -> int:
        resolved = (
            budget if budget is not None else settings.META_SYNC_TEMPLATES_DRAIN_BUDGET
        )
        if not resolved or resolved < 1:
            raise ReconciliationCannotStartError(
                f"Reconciliation budget must be a positive integer, got {resolved}"
            )
        return resolved

    def _load_or_start_progress(self, restart: bool):
        try:
            if restart:
                self.redis_conn.delete(PROGRESS_KEY)
                progress = None
            else:
                progress = self._read_progress()
        except ReconciliationError:
            raise
        except Exception as exc:
            raise ReconciliationCannotStartError(
                f"Unable to read reconciliation progress: {exc}"
            ) from exc

        if progress:
            return progress, progress["run_id"], True

        run_id = self._new_run_id()
        progress = {
            "run_id": run_id,
            "started_at": run_id,
            "done_waba_ids": [],
            "counters": dict(EMPTY_COUNTERS),
            "rows_written": 0,
        }
        self._write_progress(progress)
        return progress, run_id, False

    def _read_progress(self) -> Optional[dict]:
        raw = self.redis_conn.get(PROGRESS_KEY)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        document = json.loads(raw)
        document.setdefault("done_waba_ids", [])
        counters = dict(EMPTY_COUNTERS)
        counters.update(document.get("counters") or {})
        document["counters"] = counters
        document.setdefault("rows_written", 0)
        return document

    def _write_progress(self, progress: dict) -> None:
        self.redis_conn.set(PROGRESS_KEY, json.dumps(progress), ex=PROGRESS_TTL_SECONDS)

    @staticmethod
    def _new_run_id() -> str:
        return datetime.now(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _resolve_target_wabas(
        self, waba_ids: Optional[List[str]], app_uuids: Optional[List[str]]
    ) -> List[str]:
        from_wabas = list(dict.fromkeys(waba_ids)) if waba_ids else None
        from_apps = self._wabas_for_app_uuids(app_uuids) if app_uuids else None
        if from_wabas is not None and from_apps is not None:
            allowed = set(from_apps)
            return [waba_id for waba_id in from_wabas if waba_id in allowed]
        if from_wabas is not None:
            return from_wabas
        if from_apps is not None:
            return from_apps
        return self._all_wabas()

    def _wabas_for_app_uuids(self, app_uuids: List[str]) -> List[str]:
        seen = []
        known = set()
        apps = App.objects.filter(code__in=TEMPLATE_SYNC_APP_CODES, uuid__in=app_uuids)
        for app in apps:
            waba_id = _resolve_waba_id(app)
            if waba_id and waba_id not in known:
                known.add(waba_id)
                seen.append(waba_id)
        return seen

    def _all_wabas(self) -> List[str]:
        seen = []
        known = set()
        for app in App.objects.filter(code__in=TEMPLATE_SYNC_APP_CODES):
            waba_id = _resolve_waba_id(app)
            if waba_id and waba_id not in known:
                known.add(waba_id)
                seen.append(waba_id)
        return seen

    def _apps_on_waba(self, waba_id: str) -> List[App]:
        return list(
            App.objects.filter(code__in=TEMPLATE_SYNC_APP_CODES).filter(
                Q(config__wa_waba_id=waba_id) | Q(config__waba__id=waba_id)
            )
        )

    def _process_waba(
        self,
        waba_id,
        position,
        total,
        dry_run,
        run_id,
        progress,
        rows,
        writer,
        writer_file,
    ):
        ttl_key = TTL_WHATSAPP_TEMPLATES.format(waba_id=waba_id)
        if is_recently_synced(ttl_key, redis=self.redis_conn):
            progress["counters"]["skipped_recent_sync"] += 1
            self.logger.info(
                f"WABA skipped_recent_sync waba_id={waba_id} "
                f"not marked done, no translation rows"
            )
            self._write_progress(progress)
            return

        all_apps = self._apps_on_waba(waba_id)
        eligible = list(self.apps_for_waba(waba_id))
        eligible_pks = {app.pk for app in eligible}
        self.logger.info(
            f"WABA start waba_id={waba_id} app_count={len(all_apps)} "
            f"position={position}/{total}"
        )

        snapshots = self._snapshot_translations(all_apps, waba_id, eligible_pks)
        templates = None
        meta_error = None
        failed_app_uuids = set()
        meta_index = ({}, {})
        if eligible:
            templates, meta_error = self._fetch_meta_templates(eligible[0], waba_id)
            if meta_error:
                self.logger.error(
                    f"WABA unclassifiable waba_id={waba_id} reason={meta_error} "
                    f"affected_app_uuids={[str(app.uuid) for app in eligible]}"
                )
            else:
                if not dry_run:
                    failed_app_uuids = self._apply_templates(eligible, templates)
                meta_index = self._index_meta_templates(templates)

        waba_rows = [
            self._classify_snapshot(
                run_id, snapshot, meta_error, failed_app_uuids, meta_index, dry_run
            )
            for snapshot in snapshots
        ]
        self._emit_waba_rows(waba_rows, progress, rows, writer, writer_file)
        if not dry_run and templates is not None and meta_error is None:
            mark_synced(
                ttl_key,
                settings.WHATSAPP_TIME_BETWEEN_SYNC_TEMPLATES_IN_HOURS,
                redis=self.redis_conn,
            )
        progress["done_waba_ids"].append(waba_id)
        self._write_progress(progress)

    def _classify_snapshot(
        self, run_id, snapshot, meta_error, failed_app_uuids, meta_index, dry_run
    ):
        if snapshot.sync_disabled:
            return self._row_for(
                run_id,
                snapshot,
                category="unclassifiable",
                post=None,
                reason="sync_disabled",
            )
        if meta_error:
            return self._row_for(
                run_id,
                snapshot,
                category="unclassifiable",
                post=None,
                reason=meta_error,
            )
        if snapshot.app_uuid in failed_app_uuids:
            return self._row_for(
                run_id,
                snapshot,
                category="unclassifiable",
                post=None,
                reason="apply_failed",
            )
        post = self._post_state(snapshot, meta_index, dry_run)
        return self._row_for(run_id, snapshot, self._classify(snapshot, post), post, "")

    def _snapshot_translations(
        self, apps, waba_id, eligible_pks
    ) -> List[_TranslationSnapshot]:
        if not apps:
            return []
        translations = (
            TemplateTranslation.objects.filter(template__app__in=apps)
            .select_related("template", "template__app")
            .order_by("template__app__uuid", "template__name", "language", "uuid")
        )
        snapshots = []
        for translation in translations:
            app = translation.template.app
            snapshots.append(
                _TranslationSnapshot(
                    translation_pk=translation.pk,
                    project_uuid=str(app.project_uuid),
                    app_uuid=str(app.uuid),
                    app_code=app.code,
                    waba_id=waba_id,
                    template_name=translation.template.name,
                    template_uuid=str(translation.template.uuid),
                    translation_uuid=str(translation.uuid),
                    language=translation.language or "",
                    message_template_id=str(translation.message_template_id or ""),
                    body=translation.body or "",
                    parameter_format=translation.parameter_format,
                    body_named_params=list(translation.body_named_params or []),
                    variable_count=translation.variable_count,
                    sync_disabled=app.pk not in eligible_pks,
                )
            )
        return snapshots

    def _fetch_meta_templates(self, representative, waba_id):
        try:
            use_case = self.sync_use_case_factory(representative)
            response = use_case.template_service.list_template_messages(waba_id)
        except Exception as exc:
            return None, self._exception_reason(exc)

        if not isinstance(response, dict):
            return None, "invalid_meta_response"
        error = response.get("error")
        if error:
            return None, self._meta_error_reason(error)
        return response.get("data") or [], None

    def _apply_templates(self, apps, templates) -> set:
        failed = set()
        for app in apps:
            try:
                self.sync_use_case_factory(app).sync_templates(templates=templates)
            except Exception as exc:
                self.logger.error(
                    f"Failed applying templates app={app.uuid} "
                    f"project={app.project_uuid}: {exc}"
                )
                failed.add(str(app.uuid))
        return failed

    def _post_state(self, snapshot, meta_index, dry_run) -> Optional[_PostState]:
        meta_template = self._match_meta_template(snapshot, meta_index)
        if dry_run:
            if meta_template is None:
                return _PostState(
                    parameter_format=None,
                    body_named_params=[],
                    parameter_anomaly=None,
                )
            parameters = build_translation_parameters(meta_template)
            return _PostState(
                parameter_format=parameters.parameter_format,
                body_named_params=parameters.body_named_params,
                parameter_anomaly=parameters.anomaly,
            )
        try:
            translation = TemplateTranslation.objects.get(pk=snapshot.translation_pk)
        except TemplateTranslation.DoesNotExist:
            return _PostState(
                parameter_format=None,
                body_named_params=[],
                parameter_anomaly=None,
            )
        return _PostState(
            parameter_format=translation.parameter_format,
            body_named_params=list(translation.body_named_params or []),
            parameter_anomaly=translation.parameter_anomaly,
        )

    def _match_meta_template(self, snapshot, meta_index):
        by_id, by_name_lang = meta_index
        if snapshot.message_template_id:
            matched = by_id.get(snapshot.message_template_id)
            if matched is not None:
                return matched
        return by_name_lang.get((snapshot.template_name, snapshot.language))

    @staticmethod
    def _index_meta_templates(templates):
        by_id = {}
        by_name_lang = {}
        for template in templates or []:
            template_id = str(template.get("id") or "")
            if template_id:
                by_id[template_id] = template
            name = template.get("name")
            language = template.get("language")
            if name and language:
                by_name_lang[(name, language)] = template
        return by_id, by_name_lang

    def _classify(
        self, snapshot: _TranslationSnapshot, post: Optional[_PostState]
    ) -> str:
        if post is None:
            return "unclassifiable"
        if post.parameter_format is None:
            return "format_not_yet_known"
        if post.parameter_anomaly:
            return "anomalous"
        if self._format_or_names_changed(snapshot, post):
            return "corrected"
        return "unchanged"

    @staticmethod
    def _format_or_names_changed(snapshot, post) -> bool:
        if snapshot.parameter_format != post.parameter_format:
            return True
        return _param_name_list(snapshot.body_named_params) != _param_name_list(
            post.body_named_params
        )

    def _row_for(self, run_id, snapshot, category, post, reason):
        previously_broken = _is_previously_broken(snapshot)
        format_after = "" if post is None else (post.parameter_format or "")
        names_after = "" if post is None else _semicolon_names(post.body_named_params)
        anomaly = None if post is None else post.parameter_anomaly
        row = {
            "run_id": run_id,
            "project_uuid": snapshot.project_uuid,
            "app_uuid": snapshot.app_uuid,
            "app_code": snapshot.app_code,
            "waba_id": snapshot.waba_id,
            "template_name": snapshot.template_name,
            "template_uuid": snapshot.template_uuid,
            "translation_uuid": snapshot.translation_uuid,
            "language": snapshot.language,
            "message_template_id": snapshot.message_template_id,
            "category": category,
            "previously_broken": "true" if previously_broken else "false",
            "format_before": snapshot.parameter_format or "",
            "format_after": format_after,
            "param_names_before": _semicolon_names(snapshot.body_named_params),
            "param_names_after": names_after,
            "anomaly_type": (anomaly or {}).get("type", "") if anomaly else "",
            "anomaly_body_names": _semicolon_list(
                (anomaly or {}).get("body_param_names")
            ),
            "anomaly_example_names": _semicolon_list(
                (anomaly or {}).get("example_param_names")
            ),
            "reason": reason or "",
            "_previously_broken": previously_broken,
        }
        self._log_translation(
            snapshot, category, previously_broken, format_after, anomaly
        )
        return row

    def _log_translation(
        self, snapshot, category, previously_broken, format_after, anomaly
    ):
        self.logger.info(
            f"Translation classified project={snapshot.project_uuid} "
            f"app={snapshot.app_uuid} template={snapshot.template_name} "
            f"language={snapshot.language} "
            f"message_template_id={snapshot.message_template_id} "
            f"category={category} previously_broken={previously_broken} "
            f"format={snapshot.parameter_format or ''}->{format_after}"
        )
        if anomaly:
            self.logger.warning(
                f"Anomaly observed project={snapshot.project_uuid} "
                f"app={snapshot.app_uuid} template={snapshot.template_name} "
                f"language={snapshot.language} "
                f"message_template_id={snapshot.message_template_id} "
                f"anomaly_type={anomaly.get('type')} "
                f"anomaly_body_names={_semicolon_list(anomaly.get('body_param_names'))} "
                f"anomaly_example_names={_semicolon_list(anomaly.get('example_param_names'))}"
            )

    def _emit_waba_rows(self, waba_rows, progress, rows, writer, writer_file):
        counters = progress["counters"]
        for row in waba_rows:
            category = row["category"]
            counters[category] = counters.get(category, 0) + 1
            if row.pop("_previously_broken") and category in CLASSIFIED_CATEGORIES:
                counters["previously_broken"] += 1
            csv_row = {field: row.get(field, "") for field in CSV_FIELDS}
            try:
                writer.writerow(csv_row)
            except OSError as exc:
                raise ReconciliationCannotWriteError(
                    f"Unable to write reconciliation artifact: {exc}"
                ) from exc
            rows.append(csv_row)
        try:
            writer_file.flush()
        except OSError as exc:
            raise ReconciliationCannotWriteError(
                f"Unable to write reconciliation artifact: {exc}"
            ) from exc
        progress["rows_written"] = progress.get("rows_written", 0) + len(waba_rows)

    def _write_header_only(self, output_path):
        try:
            with open(output_path, "w", newline="", encoding="utf-8") as handle:
                csv.DictWriter(handle, fieldnames=CSV_FIELDS).writeheader()
        except OSError as exc:
            raise ReconciliationCannotWriteError(
                f"Unable to write reconciliation artifact {output_path}: {exc}"
            ) from exc

    def _open_artifact(self, output_path, write_header):
        try:
            handle = open(
                output_path,
                "w" if write_header else "a",
                newline="",
                encoding="utf-8",
            )
        except OSError as exc:
            raise ReconciliationCannotWriteError(
                f"Unable to write reconciliation artifact {output_path}: {exc}"
            ) from exc
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        return handle, writer

    def _log_run_end(self, run_id, counters, output_path, elapsed):
        self.logger.info(
            f"Template parameter reconciliation end run_id={run_id} "
            f"corrected={counters.get('corrected', 0)} "
            f"unchanged={counters.get('unchanged', 0)} "
            f"anomalous={counters.get('anomalous', 0)} "
            f"format_not_yet_known={counters.get('format_not_yet_known', 0)} "
            f"unclassifiable={counters.get('unclassifiable', 0)} "
            f"previously_broken={counters.get('previously_broken', 0)} "
            f"skipped_recent_sync={counters.get('skipped_recent_sync', 0)} "
            f"artifact={output_path} elapsed_seconds={elapsed:.3f}"
        )

    @staticmethod
    def _meta_error_reason(error) -> str:
        if isinstance(error, dict):
            code = error.get("code")
            message = error.get("message") or error.get("type")
            if code in (100, 33) or (
                isinstance(message, str) and "does not exist" in message.lower()
            ):
                return "waba_gone"
            if "token" in str(message).lower() or "oauth" in str(message).lower():
                return "invalid_token"
            return str(message or code or "meta_error")
        return str(error)

    @staticmethod
    def _exception_reason(exc) -> str:
        message = str(exc).lower()
        if "token" in message:
            return "invalid_token"
        return str(exc) or exc.__class__.__name__


def _param_name_list(body_named_params) -> List[str]:
    names = []
    for entry in body_named_params or []:
        if isinstance(entry, dict) and entry.get("param_name") is not None:
            names.append(entry["param_name"])
    return names


def _semicolon_names(body_named_params) -> str:
    return ";".join(_param_name_list(body_named_params))


def _semicolon_list(values) -> str:
    if not values:
        return ""
    return ";".join(str(value) for value in values)


def _is_previously_broken(snapshot: _TranslationSnapshot) -> bool:
    if not extract_named_placeholders(snapshot.body or ""):
        return False
    if snapshot.body_named_params:
        return False
    if snapshot.parameter_format == PARAMETER_FORMAT_NAMED:
        return False
    return (snapshot.variable_count or 0) == 0
