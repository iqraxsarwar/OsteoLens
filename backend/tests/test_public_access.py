import asyncio
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import public_access, report_store, main
from backend.main import app
from backend.privacy import PrivacyGuardMiddleware, release_issues
from backend.report_analyzer import process_report, _REPORT_SESSIONS


class PublicAccessTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.patches=[patch.object(public_access,'PUBLIC_MODE',True),patch.object(main,'PUBLIC_MODE',True),
            patch.object(public_access,'PUBLIC_ORIGIN','https://demo.test'),
            patch.object(public_access,'SESSION_SECRET','testing-only-secret-with-at-least-32-chars'),
            patch.object(report_store,'REPORT_DATA_DIR',Path(self.directory.name)),
            patch.object(report_store,'DATABASE_PATH',Path(self.directory.name)/'reports.sqlite3')]
        for item in self.patches:item.start()
        self.a=TestClient(app,base_url='https://demo.test',headers={'origin':'https://demo.test'})
        self.b=TestClient(app,base_url='https://demo.test',headers={'origin':'https://demo.test'})

    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        self.directory.cleanup()

    def test_upload_rejected_before_any_body_read(self):
        async def check():
            async def unexpected(*args):raise AssertionError('Body/parser/application was reached')
            responses=[]
            async def send(message):responses.append(message)
            guard=PrivacyGuardMiddleware(unexpected)
            for path in ['/api/reports/analyze','/api/reports/analyze/','/api/assistant/chat']:
                await guard({'type':'http','path':path,'method':'POST','headers':[]},unexpected,send)
                self.assertEqual(responses[-2]['status'],403)
        asyncio.run(check())

    def test_new_examples_are_not_saved_or_cached_as_user_reports(self):
        before=set(_REPORT_SESSIONS)
        result=self.a.post('/api/reports/examples/PMC12981788')
        self.assertEqual(result.status_code,200,result.text)
        self.assertNotIn('report_id',result.json())
        self.assertFalse(result.json()['persistence']['saved'])
        self.assertEqual(set(_REPORT_SESSIONS),before)
        self.assertEqual(report_store.list_reports(),[])
        self.assertEqual(self.a.post('/api/reports/examples/unknown').status_code,404)

    def test_no_new_cookie_and_protective_headers(self):
        response=self.a.get('/api/privacy')
        self.assertNotIn('set-cookie',response.headers)
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertEqual(response.headers['referrer-policy'],'no-referrer')
        self.assertIn("connect-src 'self'",response.headers['content-security-policy'])
        self.assertFalse(response.json()['personal_uploads_enabled'])

    def test_arbitrary_chat_never_reaches_generator_or_echoes_input(self):
        with patch('backend.rag_assistant.answer_question',side_effect=AssertionError('Unexpected generation')):
            response=self.a.post('/api/assistant/research',json={'question_id':'imaging','question':'SYNTHETIC PRIVATE MARKER'})
            self.assertEqual(response.status_code,422)
            self.assertNotIn('PRIVATE MARKER',response.text)
            self.assertEqual(self.a.post('/api/assistant/chat',json={'question':'SYNTHETIC PRIVATE MARKER'}).status_code,403)
            self.assertEqual(self.a.post('/api/reports/examples/PMC12981788',content=b'SYNTHETIC PRIVATE MARKER').status_code,413)

    def test_cross_origin_mutation_is_rejected(self):
        self.assertEqual(self.a.post('/api/reports/examples/PMC12981788',headers={'origin':'https://other.test'}).status_code,403)

    def test_turkish_guided_case_and_heatmap_preserve_citations(self):
        for question_id in ['case_summary','heatmap']:
            result=self.a.post('/api/assistant/research',json={'question_id':question_id,'case_id':'BTXRD-IMG001868','language':'tr'})
            self.assertEqual(result.status_code,200,result.text)
            self.assertIn('CASE',[x['citation_id'] for x in result.json()['citations']])

    def test_legacy_erasure_is_limited_to_verified_cookie_owner(self):
        owner='a'*64
        token=public_access.report_owner.set(owner)
        try:
            report=process_report('synthetic.txt',b'SYNTHETIC TEST DOCUMENT. A femur lesion is described.')
            report_store.save_report(report,b'SYNTHETIC TEST DOCUMENT.')
        finally:public_access.report_owner.reset(token)
        self.b.cookies.set('osteolens_session',owner+'.forged',domain='demo.test',path='/api')
        self.assertEqual(self.b.post('/api/privacy/erase-session').json()['deleted_reports'],0)
        self.a.cookies.set('osteolens_session',owner+'.'+public_access.PublicAccessMiddleware.sign(owner),domain='demo.test',path='/api')
        result=self.a.post('/api/privacy/erase-session')
        self.assertEqual(result.json()['deleted_reports'],1,result.text)
        self.assertIn('Max-Age=0',result.headers['set-cookie'])
        self.assertFalse((Path(self.directory.name)/report['report_id']).exists())

    def test_public_release_requires_operator_review(self):
        self.assertIn('controller_name',release_issues({}))
        self.assertIn('operator_review',release_issues({'approved_for_research_demo':False}))


if __name__=='__main__':unittest.main()
