import os
import tempfile
import uuid
from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase

from marketplace.wpp_templates.usecases.template_parameter_reconciliation import (
    ReconciliationResult,
)

USE_CASE_PATH = (
    "marketplace.wpp_templates.management.commands."
    "reconcile_template_parameters.TemplateParameterReconciliationUseCase"
)


def _result(**overrides):
    payload = {
        "run_id": "2026-09-17T18:04:11Z",
        "rows": [],
        "counters": {
            "corrected": 0,
            "unchanged": 0,
            "anomalous": 0,
            "format_not_yet_known": 0,
            "unclassifiable": 3,
            "previously_broken": 0,
            "skipped_recent_sync": 0,
        },
        "resumed": False,
    }
    payload.update(overrides)
    return ReconciliationResult(**payload)


class ReconcileTemplateParametersCommandTestCase(SimpleTestCase):
    def setUp(self):
        self.output_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.output_dir.cleanup)
        self.output_path = os.path.join(self.output_dir.name, "out.csv")

    def _patch_use_case(self, result=None, side_effect=None):
        patcher = patch(USE_CASE_PATH)
        mock_cls = patcher.start()
        self.addCleanup(patcher.stop)
        instance = mock_cls.return_value
        if side_effect is not None:
            instance.execute.side_effect = side_effect
        else:
            instance.execute.return_value = result or _result()
        return instance

    def test_forwards_repeatable_waba_ids_and_output(self):
        instance = self._patch_use_case()
        stdout = StringIO()
        call_command(
            "reconcile_template_parameters",
            "--waba-id",
            "waba-1",
            "--waba-id",
            "waba-2",
            "--app-uuid",
            str(uuid.uuid4()),
            "--limit",
            "20",
            "--dry-run",
            "--restart",
            "--output",
            self.output_path,
            "--budget",
            "15",
            stdout=stdout,
        )
        instance.execute.assert_called_once()
        kwargs = instance.execute.call_args.kwargs
        self.assertEqual(kwargs["waba_ids"], ["waba-1", "waba-2"])
        self.assertEqual(len(kwargs["app_uuids"]), 1)
        self.assertEqual(kwargs["limit"], 20)
        self.assertTrue(kwargs["dry_run"])
        self.assertTrue(kwargs["restart"])
        self.assertEqual(kwargs["output"], self.output_path)
        self.assertEqual(kwargs["budget"], 15)
        self.assertIn("completed", stdout.getvalue())

    def test_exit_zero_when_unclassifiable_count_is_nonzero(self):
        self._patch_use_case(
            _result(
                counters={
                    "corrected": 1,
                    "unchanged": 0,
                    "anomalous": 0,
                    "format_not_yet_known": 0,
                    "unclassifiable": 12,
                    "previously_broken": 1,
                    "skipped_recent_sync": 0,
                }
            )
        )
        call_command(
            "reconcile_template_parameters",
            "--output",
            self.output_path,
        )

    def test_exit_one_when_output_path_is_a_directory(self):
        self._patch_use_case()
        with self.assertRaises(CommandError):
            call_command(
                "reconcile_template_parameters",
                "--output",
                self.output_dir.name,
            )

    def test_exit_one_when_output_directory_missing(self):
        self._patch_use_case()
        missing = os.path.join(self.output_dir.name, "missing", "out.csv")
        with self.assertRaises(CommandError):
            call_command(
                "reconcile_template_parameters",
                "--output",
                missing,
            )

    def test_exit_one_when_use_case_cannot_write(self):
        from marketplace.wpp_templates.usecases.template_parameter_reconciliation import (
            ReconciliationCannotWriteError,
        )

        self._patch_use_case(side_effect=ReconciliationCannotWriteError("disk full"))
        with self.assertRaises(CommandError):
            call_command(
                "reconcile_template_parameters",
                "--output",
                self.output_path,
            )
