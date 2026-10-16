import json
import tempfile
import unittest
from pathlib import Path
from zenity_auth import Credentials, TokenProvider, AuthFailure, read_credentials, safe_error

TOKEN_URL = 'https://zenity-prod.eu.auth0.com/oauth/token'
AUDIENCE = 'https://zenity-prod.eu.zenity.io/api/v3'

class AuthTests(unittest.TestCase):
    def test_org_bound_exchange_and_cache(self):
        calls=[]
        def transport(payload,timeout):
            calls.append((payload,timeout)); return {'access_token':'secret-marker','token_type':'Bearer','expires_in':300}
        provider=TokenProvider(Credentials('id','secret'),'org_demo',TOKEN_URL,AUDIENCE,transport,lambda:0)
        self.assertEqual(provider.get_token(),'secret-marker')
        self.assertEqual(provider.get_token(),'secret-marker')
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][0]['organization'],'org_demo')
        self.assertEqual(calls[0][0]['audience'],AUDIENCE)
        self.assertEqual(calls[0][1],10)
        self.assertNotIn('secret',repr(provider))
        self.assertNotIn('secret',repr(Credentials('id','secret')))
        self.assertEqual(TOKEN_URL,'https://zenity-prod.eu.auth0.com/oauth/token')

    def test_expiry_refresh(self):
        now=[0];calls=[]
        def transport(*args):
            calls.append(1);return {'access_token':'marker','token_type':'Bearer','expires_in':100}
        provider=TokenProvider(Credentials('id','secret'),'demo',TOKEN_URL,AUDIENCE,transport,lambda:now[0])
        provider.get_token();now[0]=91;provider.get_token()
        self.assertEqual(len(calls),2)

    def test_unknown_errors_are_safe_and_not_retried(self):
        calls=[]
        def transport(*args): calls.append(1);raise RuntimeError('SECRET_MARKER')
        provider=TokenProvider(Credentials('id','secret'),'demo',TOKEN_URL,AUDIENCE,transport)
        with self.assertRaises(AuthFailure) as exc: provider.get_token()
        self.assertEqual(str(exc.exception),'auth_failed')
        self.assertEqual(len(calls),1)

    def test_organization_required_and_invalid(self):
        for organization in ('','bad\nname',None,'https://other.example'):
            with self.assertRaises(AuthFailure): TokenProvider(Credentials('id','secret'),organization,TOKEN_URL,AUDIENCE)

    def test_bad_token_response(self):
        for response in (None,{}, {'access_token':'secret\nmarker','token_type':'Bearer','expires_in':300}, {'access_token':'marker','token_type':'Bearer','expires_in':float('nan')}):
            provider=TokenProvider(Credentials('id','secret'),'demo',TOKEN_URL,AUDIENCE,lambda *args:response)
            with self.assertRaises(AuthFailure) as exc: provider.get_token()
            self.assertEqual(str(exc.exception),'invalid_token_response')

    def test_parser_and_safe_error(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'credentials'
            p.write_text('CLIENT_ID = "test-id"\nCLIENT_SECRET: test-secret\n')
            credentials=read_credentials(p)
            self.assertEqual(credentials.client_id,'test-id')
            self.assertEqual(credentials.client_secret,'test-secret')
            p.write_text('CLIENT_ID=test\nCLIENT_ID=duplicate\nCLIENT_SECRET=secret\n')
            with self.assertRaises(AuthFailure): read_credentials(p)
        body=json.dumps({'error_description':'The organization parameter is required. SECRET_MARKER'}).encode()
        self.assertEqual(safe_error(body,400),'organization_required')
        self.assertEqual(safe_error(b'SECRET_MARKER',401),'auth_failed')
        self.assertEqual(safe_error(b'SECRET_MARKER',429),'rate_limited')
