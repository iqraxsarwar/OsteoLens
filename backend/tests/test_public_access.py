import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import public_access, report_store
from backend.main import app


class PublicAccessTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.patches = [patch.object(public_access,'PUBLIC_MODE',True),
            patch.object(public_access,'PUBLIC_ORIGIN','https://demo.test'),
            patch.object(public_access,'SESSION_SECRET','testing-only-secret-with-at-least-32-chars'),
            patch.object(report_store,'REPORT_DATA_DIR',Path(self.directory.name)),
            patch.object(report_store,'DATABASE_PATH',Path(self.directory.name)/'reports.sqlite3')]
        for item in self.patches: item.start()
        self.a=TestClient(app,base_url='https://demo.test',headers={'origin':'https://demo.test'})
        self.b=TestClient(app,base_url='https://demo.test',headers={'origin':'https://demo.test'})

    def tearDown(self):
        for item in reversed(self.patches): item.stop()
        self.directory.cleanup()

    def upload(self):
        response=self.a.post('/api/reports/analyze',files={'file':('synthetic.txt',b'SYNTHETIC. A distal femur lesion is reported. MRI follow-up is recommended.','text/plain')})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['report_id']

    def test_sessions_cannot_read_ask_associate_delete_other_uploads(self):
        report_id=self.upload()
        self.assertEqual(len(self.a.get('/api/reports').json()['reports']),1)
        self.assertEqual(self.b.get('/api/reports').json()['reports'],[])
        self.assertEqual(self.b.get(f'/api/reports/item/{report_id}').status_code,404)
        self.assertEqual(self.b.post('/api/reports/ask',json={'report_id':report_id,'question':'What lesion?'}).status_code,404)
        self.assertEqual(self.b.patch(f'/api/reports/{report_id}/association',json={'case_id':None}).status_code,422)
        self.assertEqual(self.b.delete(f'/api/reports/{report_id}').status_code,404)
        self.assertEqual(self.a.get(f'/api/reports/item/{report_id}').status_code,200)
        self.assertEqual(self.a.delete(f'/api/reports/{report_id}').status_code,200)

    def test_cookie_is_secure_and_tampering_does_not_reveal_reports(self):
        response=self.a.get('/api/reports')
        cookie=response.headers['set-cookie']
        for required in ('HttpOnly','Secure','SameSite=Lax'): self.assertIn(required,cookie)
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.upload()
        forged=self.a.cookies.get('osteolens_session').split('.')[0]+'.invalid'
        self.b.cookies.set('osteolens_session',forged)
        self.assertEqual(self.b.get('/api/reports').json()['reports'],[])

    def test_cross_origin_mutation_is_rejected(self):
        response=self.a.post('/api/reports/ask',headers={'origin':'https://other.test'},json={'report_id':'0'*32,'question':'What?'})
        self.assertEqual(response.status_code,403)

    def test_expiry_preserves_local_reports(self):
        report_id=self.upload()
        with report_store._database() as connection:
            connection.execute("UPDATE reports SET uploaded_at = '2000-01-01T00:00:00+00:00'")
        report_store.purge_expired_reports()
        self.assertFalse((Path(self.directory.name)/report_id).exists())
        self.assertEqual(self.a.get('/api/reports').json()['reports'],[])

    def test_turkish_case_and_heatmap_answers_preserve_citations(self):
        for question in ['BTXRD-IMG001868 için mevcut bilgileri açıkla.','Isı haritası ne gösteriyor?']:
            result=self.a.post('/api/assistant/chat',json={'question':question,'case_id':'BTXRD-IMG001868','language':'tr'})
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(result.json()['status'],'answered')
            self.assertIn('BTXRD-IMG001868',result.json()['answer'])
            self.assertIn('CASE',[x['citation_id'] for x in result.json()['citations']])


if __name__=='__main__': unittest.main()
