import unittest
from backend.language import ensure_turkish_response


class LanguageTests(unittest.TestCase):
    def test_english_generation_falls_back_to_exact_source_quotes(self):
        evidence=[{'citation_id':'S1','text':'The source sentence. Another source sentence.'}]
        answer,ids=ensure_turkish_response('The tumor is a rare tumor of the bone.',['S1'],evidence)
        self.assertIn('Türkçe',answer)
        self.assertIn(evidence[0]['text'],answer)
        self.assertNotIn('rare tumor',answer)
        self.assertEqual(ids,['S1'])

    def test_turkish_response_keeps_citations_unchanged(self):
        answer='Bu bir kemik tümörü olarak tanımlanır. [S1]'
        self.assertEqual(ensure_turkish_response(answer,['S1'],[]),(answer,['S1']))
