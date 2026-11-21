"""Test legacy persistence for controlled erasure; uploads are no longer exposed."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from backend import report_store
from backend.public_access import report_owner
from backend.report_analyzer import process_report


class ReportStoreTests(unittest.TestCase):
    def test_legacy_storage_owner_isolation_and_deletion(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(report_store,'REPORT_DATA_DIR',Path(directory)), \
             patch.object(report_store,'DATABASE_PATH',Path(directory)/'reports.sqlite3'):
            first=report_owner.set('owner-one')
            try:
                result=process_report('synthetic.txt',b'SYNTHETIC. A distal femur lesion is reported.')
                report_store.save_report(result,b'SYNTHETIC.')
                report_id=result['report_id']
                self.assertEqual(len(report_store.list_reports()),1)
                second=report_owner.set('owner-two')
                try:
                    self.assertEqual(report_store.list_reports(),[])
                    for operation in [lambda:report_store.get_report(report_id),lambda:report_store.delete_report(report_id),lambda:report_store.update_case_association(report_id,None)]:
                        with self.assertRaises(report_store.ReportStoreError):operation()
                finally:report_owner.reset(second)
                report_store.delete_report(report_id)
                self.assertEqual(report_store.list_reports(),[])
            finally:report_owner.reset(first)
