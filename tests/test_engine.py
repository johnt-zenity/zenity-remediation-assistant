import json
import unittest
from engine import run_action, FixtureReader, follow_up, ORG

class FakeClock:
    def __init__(self): self.now = 0
    def __call__(self): return self.now
    def sleep(self, amount): self.now += amount

class Tests(unittest.TestCase):
    def action(self, value):
        reader, clock = FixtureReader(), FakeClock()
        result = run_action({'violation_id': value}, reader, clock, clock.sleep)
        self.assertTrue(all(c['operation']=='retrieve' and c['organization']==ORG for c in reader.calls))
        return result, reader

    def test_published_vectors(self):
        from pathlib import Path
        vectors=json.loads((Path(__file__).parent/'vectors.json').read_text())
        for vector in vectors:
            with self.subTest(vector=vector['id'], case=vector['case']):
                reader, clock=FixtureReader(),FakeClock()
                result=run_action(vector['input'],reader,clock,clock.sleep)
                self.assertEqual(result['outcome'],vector['outcome'])
                self.assertEqual(len(reader.calls),vector['reads'])
                self.assertTrue(all(c['organization']==ORG for c in reader.calls))
                self.assertNotIn('SECRET_MARKER_9f13',json.dumps(result))
                self.assertNotIn('<script>',json.dumps(result))
                self.assertNotIn('Ignore instructions',json.dumps(result))
                if result['outcome']=='ok':
                    self.assertEqual(len(result['sections']),6)
                    self.assertTrue(all(s['source'] in ('record','fixture-guide') for s in result['sections']))
                elif result['outcome']!='unsupported_type':
                    self.assertNotIn('context',result)
                    self.assertNotIn('sections',result)

    def test_followups_are_read_only(self):
        result, reader=self.action('DEMO-001')
        for question in ('fix it', 'delete the flow', 'change status', 'reveal credentials', 'who can act?', 'how to verify?', 'exfiltrate data'):
            answer=follow_up(result,question)
            self.assertTrue(answer)
            self.assertEqual(len(reader.calls),1)
        self.assertIn('No change was made',follow_up(result,'fix it'))

    def test_closed_historical_observation(self):
        result,_=self.action('DEMO-CLOSED')
        self.assertEqual(result['context']['observed_status'],'closed')
        self.assertIn('does not establish a current exposure',result['sections'][0]['text'])
        self.assertIn('cannot confirm remediation',result['sections'][4]['text'])

    def test_bad_record_shapes(self):
        class Reader:
            def __init__(self, value): self.value=value
            def retrieve(self,*args,**kwargs): return self.value
        for record in (None,[],{}, {'organization':ORG},dict(FixtureReader().retrieve(ORG,'DEMO-001',10), observed_at='not a timestamp')):
            self.assertIn(run_action({'violation_id':'DEMO-001'},Reader(record))['outcome'],('invalid_record','not_found_or_denied'))

    def test_timeout_budget(self):
        clock=FakeClock()
        class SlowReader:
            def retrieve(self,*args,**kwargs):
                self.timeout=kwargs['timeout']; clock.now+=11
                return FixtureReader().retrieve(ORG,'DEMO-001',10)
        reader=SlowReader()
        result=run_action({'violation_id':'DEMO-001'},reader,clock,clock.sleep)
        self.assertEqual(result['outcome'],'unavailable')
        self.assertEqual(reader.timeout,10)
        self.assertNotIn('context',result)

    def test_transient_recovery(self):
        from engine import ReadFailure
        clock=FakeClock()
        class Reader:
            calls=0
            def retrieve(self,*args,**kwargs):
                self.calls+=1
                if self.calls==1: raise ReadFailure(502)
                return FixtureReader().retrieve(ORG,'DEMO-001',10)
        result=run_action({'violation_id':'DEMO-001'},Reader(),clock,clock.sleep)
        self.assertEqual(result['outcome'],'ok')
        self.assertEqual(result['trace']['attempts'],2)

    def test_errors_never_leak(self):
        class Reader:
            def retrieve(self,*args,**kwargs): raise RuntimeError('SECRET_MARKER_9f13')
        result=run_action({'violation_id':'DEMO-001'},Reader())
        self.assertEqual(result['outcome'],'unavailable')
        self.assertNotIn('SECRET_MARKER',json.dumps(result))


class ProfileIsolationTests(unittest.TestCase):
    def test_two_customer_profiles(self):
        from profiles import load_profile
        primary,other=load_profile('test'),load_profile('example')
        a=run_action({'violation_id':'DEMO-001'},profile=primary)
        b=run_action({'violation_id':'DEMO-001'},profile=other)
        self.assertEqual(a['outcome'],'ok')
        self.assertEqual(b['outcome'],'ok')
        self.assertNotEqual(a['context']['resource_label'],b['context']['resource_label'])
        cross=run_action({'violation_id':'DEMO-001'},reader=FixtureReader(primary),profile=other)
        self.assertEqual(cross['outcome'],'not_found_or_denied')
        self.assertNotIn('context',cross)

    def test_chat_cannot_select_profile(self):
        self.assertEqual(run_action({'violation_id':'DEMO-001','profile':'example'})['outcome'],'invalid_input')

    def test_profile_path_validation(self):
        from profiles import load_profile
        with self.assertRaises(ValueError): load_profile('../../secret')

if __name__=='__main__': unittest.main()
