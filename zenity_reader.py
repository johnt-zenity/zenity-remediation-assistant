"""Fixed-scope Zenity reads. No mutation or generic query interface."""
import base64
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener
from engine import ReadFailure
from profiles import Profile
from evidence import project_evidence
from zenity_auth import TokenProvider, read_credentials, AuthFailure, NoRedirect

MAX_BODY=1000000

@dataclass(frozen=True)
class Connection:
    organization_id: str
    integration_id: str
    credential_file: str = field(repr=False)
    organization_name: str = 'demo'
    api_base: str = ''
    token_url: str = ''
    audience: str = ''
    issuer: str = ''
    region: str = 'customer-configured'
    sample_violation_id: str = ''

    def __post_init__(self):
        if not re.fullmatch(r'org_[A-Za-z0-9]{1,100}',self.organization_id): raise ValueError('Invalid organization ID')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',self.integration_id): raise ValueError('Invalid integration ID')
        if not isinstance(self.credential_file,str) or not self.credential_file: raise ValueError('Credential path required')
        for field_name, value in (('api_base',self.api_base),('token_url',self.token_url),('issuer',self.issuer)):
            parsed=urlsplit(value)
            if (parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or
                    parsed.query or parsed.fragment or any(ord(c)<33 for c in value)):
                raise ValueError(f'Invalid HTTPS Zenity {field_name} URL')
        if not self.api_base.endswith('/'):
            raise ValueError('Zenity api_base must end with /')
        if not isinstance(self.audience,str) or not self.audience or any(c.isspace() or ord(c)<32 for c in self.audience):
            raise ValueError('Zenity audience is required')

    @property
    def profile(self):
        return Profile('live-demo',self.organization_name,self.organization_id,'unreviewed','Authorized resource')


def load_connection(path):
    data=json.loads(Path(path).read_text())
    return Connection(**data)


def bound_token(token,organization_id,expected_audience,expected_issuer):
    # Inspect a token returned directly by the configured TLS-authenticated OAuth endpoint.
    # This is an issuer-response consistency check; it is not general JWT verification.
    try:
        encoded=token.split('.')[1]
        claims=json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
        audience=claims.get('aud')
        valid_audience=audience==expected_audience or isinstance(audience,list) and expected_audience in audience
        return (claims.get('org_id')==organization_id and
            claims.get('iss')==expected_issuer and valid_audience and
            type(claims.get('exp')) in (int,float) and claims['exp']>time.time())
    except Exception: return False


def fetch_record(api_base,path,token,timeout):
    if not re.fullmatch(r'/v1/assessment/integrations/[A-Za-z0-9_-]+/violations/(?:[A-Za-z0-9_.~-]|%[A-Fa-f0-9]{2})+',path):
        raise ReadFailure(422)
    request=Request(api_base.rstrip('/')+path,headers={'Authorization':'Bearer '+token,
        'Accept':'application/json','x-correlation-id':str(uuid.uuid4())},method='GET')
    try:
        with build_opener(NoRedirect()).open(request,timeout=timeout) as response:
            data=response.read(MAX_BODY+1)
            if len(data)>MAX_BODY: raise ReadFailure(422)
            return json.loads(data)
    except HTTPError as error:
        # Do not read or disclose the raw response body.
        retry=0
        try: retry=max(0,float(error.headers.get('Retry-After','0')))
        except (ValueError,TypeError): pass
        raise ReadFailure(error.code,retry) from None
    except ReadFailure: raise
    except (URLError,TimeoutError,OSError): raise TimeoutError() from None
    except (ValueError,UnicodeDecodeError): raise ReadFailure(422) from None

class ZenityReader:
    mode='live'
    def __init__(self,connection,provider=None,transport=fetch_record,clock=time.monotonic,credentials=None):
        self.connection=connection
        credentials=(credentials or read_credentials(connection.credential_file)) if provider is None else None
        self.redactions=(credentials.client_id,credentials.client_secret) if credentials else ()
        self.provider=provider or TokenProvider(credentials,connection.organization_id,
            connection.token_url,connection.audience)
        self.transport=transport or fetch_record
        self.clock=clock

    def retrieve(self,organization,violation_id,timeout):
        if organization!=self.connection.organization_id: raise ReadFailure(404)
        # Identifiers cannot select a path, query, organization or integration.
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',violation_id): raise ReadFailure(404)
        start=self.clock()
        try: token=self.provider.get_token(timeout=min(10,timeout))
        except AuthFailure as failure:
            if failure.category=='rate_limited': raise ReadFailure(429) from None
            if failure.category=='unavailable': raise ReadFailure(503) from None
            raise ReadFailure(401) from None
        if not bound_token(token,organization,self.connection.audience,self.connection.issuer): raise ReadFailure(401)
        remaining=timeout-(self.clock()-start)
        if remaining<=0: raise TimeoutError()
        path=f'/v1/assessment/integrations/{self.connection.integration_id}/violations/{quote(violation_id,safe="")}'
        if self.transport is fetch_record:
            record=self.transport(self.connection.api_base,path,token,remaining)
        else:
            record=self.transport(path,token,remaining)
        if not isinstance(record,dict): return None
        if record.get('zenityAccountId')!=organization: raise ReadFailure(404)
        integration=record.get('integration')
        if not isinstance(integration,dict): return None
        if integration.get('id')!=self.connection.integration_id: raise ReadFailure(404)
        resource=record.get('resource')
        rule=record.get('rule')
        if not isinstance(resource,dict) or not isinstance(rule,dict): return None
        if record.get('id')!=violation_id: return None
        rule_id=rule.get('id')
        if not isinstance(rule_id,str) or not re.fullmatch(r'ZN_[A-Z0-9]{1,30}',rule_id): return None
        resource_id=resource.get('id')
        if not isinstance(resource_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',resource_id): return None
        # Project bounded source material only after all identity checks pass.
        return {'id':record['id'],'organization':organization,'violation_type':'unreviewed_live_rule',
            'rule_id':rule_id,'resource_type':resource.get('resourceType') if isinstance(resource.get('resourceType'),str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',resource['resourceType']) else 'unknown',
            'resource_id':resource_id,'status':record.get('status'),'observed_at':record.get('lastSeen'),
            'severity':rule.get('severity'),'planning_source':project_evidence(record,self.redactions+(token,resource.get('displayName') if isinstance(resource.get('displayName'),str) else '',resource_id))}
