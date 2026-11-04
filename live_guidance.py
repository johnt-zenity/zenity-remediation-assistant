"""Preview proposals from redacted Zenity source text; Copilot performs synthesis."""

def guidance(context):
    source=context['planning_source']
    rule=source.get('rule',{})
    return [
        {'title':'What was detected','text':(rule.get('displayName') or context['rule_id'])+'. '+(rule.get('description') or rule.get('summary') or 'Use the selected evidence to confirm the finding.')+' Observed at '+context['observed_at']+'. Reported status: '+context['observed_status']+'.','source':'record'},
        {'title':'Why it matters','text':rule.get('riskReason') or 'Assess the permissions and data reachable through this resource. The observation alone does not establish exploitation.','source':'record'},
        {'title':'Considerations','text':'The appropriate change depends on the current configuration, business purpose and dependencies. The observation does not establish those details.','source':'record'},
        {'title':'Proposed remediation','steps':['Compare the reported rule condition with the current resource configuration.', 'Consider removing an unnecessary configuration or adjusting it to address the reported condition, where appropriate.', 'Assess dependencies and possible side effects before choosing a change.'],'source':'record'},
        {'title':'How to verify','text':'Compare the resulting configuration with the rule condition and review the next available Zenity observation. This assistant has made no changes and cannot confirm remediation.','source':'record'},
        {'title':'Sources and limits','text':'Rule '+context['rule_id']+' and selected redacted finding evidence from Zenity. This preview provides general guidance; Copilot synthesis is configured separately. No reviewed procedure is required to propose a plan. Proposed steps require validation before execution.','source':'record'}]
