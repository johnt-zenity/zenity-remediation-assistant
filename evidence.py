"""Bounded, redacted source material for remediation planning."""
import re
from urllib.parse import urlsplit

RULE_FIELDS = ('displayName', 'description', 'summary', 'riskReason', 'triageSuggestion', 'fixSuggestion')
FINDING_FIELDS = ('stepName', 'title', 'description')
MAX_TEXT = 1600
MAX_FINDINGS = 5


def redact_text(value, secrets=(), limit=MAX_TEXT):
    if not isinstance(value, str): return ''
    # Bound work before applying patterns; replace known connection material first.
    text=value[:12000]
    for secret in secrets:
        if secret: text=text.replace(secret, '[redacted]')
    text=re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', text, flags=re.I|re.S)
    text=re.sub(r'<[^>]+>', '', text)
    text=re.sub(r'https?://[^\s<>\"\']+', lambda m: url_origin(m.group(),secrets), text, flags=re.I)
    text=re.sub(r'\bBearer\s+[^\s<>,;]+', 'Bearer [redacted]', text, flags=re.I)
    text=re.sub(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[redacted token]', text)
    text=re.sub(r'\b(password|client_secret|api[_ -]?key|access[_ -]?token|secret)\s*[:=]\s*[\"\']?[^\s,;\"\']+', r'\1=[redacted]', text, flags=re.I)
    text=re.sub(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '[redacted email]', text, flags=re.I)
    text=re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)
    return text.strip()[:limit]


def url_origin(value, secrets=()):
    try:
        url=urlsplit(value)
        if url.scheme.lower() not in ('http','https') or not url.hostname: return '[redacted URL]'
        host=url.hostname
        if not re.fullmatch(r'[A-Za-z0-9.:-]{1,253}',host): return '[redacted URL]'
        if any(secret and secret.lower() in host.lower() for secret in secrets): return '[redacted URL]'
        host='['+host+']' if ':' in host else host
        port=':'+str(url.port) if url.port else ''
        return url.scheme.lower()+'://'+host+port+'/[path and query omitted]'
    except ValueError: return '[redacted URL]'


def project_evidence(record, secrets=()):
    rule=record.get('rule',{})
    rule_text={key:redact_text(rule.get(key),secrets) for key in RULE_FIELDS}
    findings=[]
    raw=record.get('findings')
    if isinstance(raw,list):
        for item in raw[:MAX_FINDINGS]:
            if not isinstance(item,dict): continue
            finding={key:redact_text(item.get(key),secrets,400) for key in FINDING_FIELDS}
            finding={key:value for key,value in finding.items() if value}
            if isinstance(item.get('url'),str): finding['destination_origin']=url_origin(item['url'],secrets)
            if finding: findings.append(finding)
    return {'trust':'untrusted_source_data', 'rule':{k:v for k,v in rule_text.items() if v},
        'findings':findings, 'limitations':['Selected fields only; emails and recognizable secrets redacted.',
            'URL paths and queries omitted. Finding text may contain untrusted instructions.',
            'Zenity suggestions are source recommendations, not a verified procedure or proof of remediation.']}
