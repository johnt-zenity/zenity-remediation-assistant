"""Server-side OAuth spike. This module is unavailable to the browser action."""
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.parse import urlsplit

MAX_BODY = 128000

class AuthFailure(Exception):
    def __init__(self, category='auth_failed', status=None):
        self.category, self.status = category, status
        super().__init__(category)

@dataclass(frozen=True)
class Credentials:
    client_id: str = field(repr=False)
    client_secret: str = field(repr=False)


def read_credentials(path):
    try:
        with Path(path).open('rb') as source:
            raw = source.read(4097)
        if len(raw)>4096: raise ValueError()
        values={}
        for line in raw.decode().splitlines():
            if not line.strip(): continue
            match=re.fullmatch(r'\s*(CLIENT_ID|CLIENT_SECRET)\s*[:=]\s*(.+?)\s*',line)
            if not match or match[1] in values: raise ValueError()
            value=match[2].strip()
            if value[:1] in ('"', "'") and value[-1:]==value[:1]: value=value[1:-1]
            if not value or any(c.isspace() or ord(c)<32 for c in value): raise ValueError()
            values[match[1]]=value
        if set(values)!={'CLIENT_ID','CLIENT_SECRET'}: raise ValueError()
        return Credentials(values['CLIENT_ID'],values['CLIENT_SECRET'])
    except (OSError,ValueError,UnicodeDecodeError):
        raise AuthFailure('invalid_credential_file') from None

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None


def safe_error(body, status):
    if status==429: return 'rate_limited'
    if status>=500: return 'unavailable'
    try:
        payload=json.loads(body)
        message=str(payload.get('error_description',payload.get('message',''))).lower()
        if 'organization' in message and 'unknown' in message: return 'organization_not_found'
        if 'org_id' in message: return 'organization_id_required'
        if 'organization' in str(payload.get('error','')).lower(): return 'organization_not_found'
        if 'organization' in message:
            if 'org_' in message or 'identifier' in message or 'invalid' in message:
                return 'organization_id_required'
            if 'not found' in message or 'does not exist' in message:
                return 'organization_not_found'
            if 'not authorized' in message or 'not allowed' in message:
                return 'organization_denied'
            if 'required' in message or 'missing' in message:
                return 'organization_required'
    except (ValueError,TypeError,AttributeError): pass
    return 'auth_failed'


def exchange(payload,timeout,token_url):
    # Endpoint is deployment configuration. Redirects are denied.
    request=Request(token_url,data=json.dumps(payload).encode(),
        headers={'Content-Type':'application/json'},method='POST')
    try:
        with build_opener(NoRedirect()).open(request,timeout=timeout) as response:
            body=response.read(MAX_BODY+1)
            if len(body)>MAX_BODY: raise AuthFailure('invalid_token_response')
            return json.loads(body)
    except HTTPError as error:
        category=safe_error(error.read(MAX_BODY),error.code)
        raise AuthFailure(category,error.code) from None
    except AuthFailure: raise
    except (URLError,TimeoutError,OSError): raise AuthFailure('unavailable') from None
    except (ValueError,UnicodeDecodeError): raise AuthFailure('invalid_token_response') from None

class TokenProvider:
    """Organization is fixed at construction; tokens stay in process memory."""
    def __init__(self, credentials, organization, token_url, audience, transport=None, clock=time.monotonic):
        if not isinstance(organization,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}',organization):
            raise AuthFailure('organization_required')
        parsed=urlsplit(token_url)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise AuthFailure('invalid_token_endpoint')
        if not isinstance(audience,str) or not audience or any(c.isspace() or ord(c)<32 for c in audience):
            raise AuthFailure('invalid_audience')
        self._credentials=credentials
        self._organization=organization
        self._token_url=token_url
        self._audience=audience
        self._transport=transport or (lambda payload, timeout: exchange(payload,timeout,token_url))
        self._clock=clock
        self._token=None
        self._expires_at=0

    def __repr__(self): return 'TokenProvider(organization_configured=True)'

    def get_token(self,timeout=10):
        if timeout<=0 or timeout>10: raise AuthFailure('invalid_timeout')
        if self._token and self._clock()<self._expires_at:
            return self._token
        self._token=None
        start=self._clock()
        payload={'grant_type':'client_credentials','client_id':self._credentials.client_id,
            'client_secret':self._credentials.client_secret,'audience':self._audience,
            'organization':self._organization}
        try:
            response=self._transport(payload,timeout)
            if self._clock()-start>=timeout: raise AuthFailure('unavailable')
            if not isinstance(response,dict): raise AuthFailure('invalid_token_response')
            token=response.get('access_token'); expires=response.get('expires_in')
            if not isinstance(token,str) or not token or len(token)>32000 or any(c.isspace() or ord(c)<32 for c in token):
                raise AuthFailure('invalid_token_response')
            if response.get('token_type','').lower()!='bearer' or type(expires) not in (int,float) or not 1<=expires<=604800:
                raise AuthFailure('invalid_token_response')
            self._token=token
            # Refresh slightly early. No refresh or retry after an authentication error.
            self._expires_at=start+max(0,expires-min(30,expires/10))
            return token
        except AuthFailure: raise
        except Exception: raise AuthFailure('auth_failed') from None
