import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from marketplace.wpp_templates.usecases.template_parameter_reconciliation import (
    ReconciliationError,
    TemplateParameterReconciliationUseCase,
)


class Command(BaseCommand):
    help = (
        "Classify already-recorded WhatsApp templates against Meta and write a "
        "reconciliation CSV artifact. Operator-triggered; does not run on a schedule."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--waba-id",
            action="append",
            dest="waba_id",
            help="Restrict to a WABA. Repeatable.",
        )
        parser.add_argument(
            "--app-uuid",
            action="append",
            dest="app_uuid",
            help="Restrict to an app; resolved to its WABA. Repeatable.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop after N WABAs.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Classify and report without writing to the mirror.",
        )
        parser.add_argument(
            "--restart",
            action="store_true",
            help="Discard stored progress and start a new run.",
        )
        parser.add_argument(
            "--output",
            default=None,
            help="Artifact path. Default: reconciliation-<run_id>.csv in the working directory.",
        )
        parser.add_argument(
            "--budget",
            type=int,
            default=None,
            help=(
                "WABAs per minute. Default: "
                f"{settings.META_SYNC_TEMPLATES_DRAIN_BUDGET}."
            ),
        )

    def handle(self, *args, **options):
        output = options.get("output")
        if output:
            self._ensure_output_writable(output)

        budget = options.get("budget")
        if budget is not None and budget < 1:
            raise CommandError("--budget must be a positive integer.")

        limit = options.get("limit")
        if limit is not None and limit < 1:
            raise CommandError("--limit must be a positive integer.")

        use_case = TemplateParameterReconciliationUseCase()
        try:
            result = use_case.execute(
                waba_ids=options.get("waba_id"),
                app_uuids=options.get("app_uuid"),
                dry_run=bool(options.get("dry_run")),
                restart=bool(options.get("restart")),
                limit=limit,
                output=output,
                budget=budget,
            )
        except ReconciliationError as exc:
            raise CommandError(str(exc)) from exc
        except OSError as exc:
            raise CommandError(str(exc)) from exc

        counters = result.counters
        self.stdout.write(
            f"Reconciliation {result.run_id} completed. "
            f"corrected={counters.get('corrected', 0)} "
            f"unchanged={counters.get('unchanged', 0)} "
            f"anomalous={counters.get('anomalous', 0)} "
            f"format_not_yet_known={counters.get('format_not_yet_known', 0)} "
            f"unclassifiable={counters.get('unclassifiable', 0)} "
            f"previously_broken={counters.get('previously_broken', 0)} "
            f"skipped_recent_sync={counters.get('skipped_recent_sync', 0)}"
        )

    def _ensure_output_writable(self, output):
        path = os.path.abspath(output)
        if os.path.isdir(path):
            raise CommandError(f"Output path is a directory: {path}")
        parent = os.path.dirname(path) or os.getcwd()
        if not os.path.isdir(parent):
            raise CommandError(f"Output directory does not exist: {parent}")
        if not os.access(parent, os.W_OK):
            raise CommandError(f"Output directory is not writable: {parent}")
        if os.path.exists(path) and not os.access(path, os.W_OK):
            raise CommandError(f"Output path is not writable: {path}")
