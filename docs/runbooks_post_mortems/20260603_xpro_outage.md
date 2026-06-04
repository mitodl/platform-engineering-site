# **MIX XPro Outage \#7**

## **Overview**

Author: Christoper Patti  
Severity:   SEV1  
Types:    Customer Facing

#### **🕐 Timestamps**

Started At: June 3 3:38 PM EDT  
Mitigated At: June 3 4:38 PM EDT  
Resolved At: June 3 4:38 PM EDT

#### **🔗 Links**

[Incident Page](https://rootly.com/account/incidents/7-https-xpro-mit-edu-outage)  |  [Slack channel](https://slack.com/app_redirect?channel=C0B821X9N3G&team=T04JRPJF6)

#### ---

**Summary**

503 certificate renewal error

## ---

**📝 Retrospective**

### **2026-06-03 \- XPro Production Outage**

### **Leadup**

We received an alert at 3:38 PM first that the XPro Production CMS and then the main XPro app were vending 503 errors to customers.

[CMS Alert](https://rootly.com/account/alerts/MIBSZ8)
[Main XPro Site Alert](https://rootly.com/account/alerts/B6RY2m)

### **Fault**

The SSL certificate for [https://xpro.mit.edu](https://xpro.mit.edu) failed to renew

### **Detection**

Tobias asked Claude to scan the logs and diagnose the issue at 4:27 PM  
Sequence diagnosis from Claude:  
Root Cause: xpro-cert — Certificate Expired, ACME Order Gone Stale

 \#\#\# Timeline

 ┌──────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  
 │ Date                 │ Event                                                                                                                                 │  
 ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤  
 │ 2026-03-05           │ Certificate issued (revision 1), valid for 90 days                                                                                    │  
 ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤  
 │ 2026-05-04           │ Renewal triggered (30-day window) — xpro-cert-2 CertificateRequest \+ Order xpro-cert-2-1040610603 created                             │  
 ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤  
 │ 2026-05-04 → \+7 days │ DNS-01 challenge xpro-cert-2-…-3359721776 for xpro-web.odl.mit.edu never completed → Let's Encrypt deactivated the ACME authorization │  
 ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤  
 │ \~30 days later       │ Challenge state: expired; LE garbage-collected order 507326254665 from their side                                                     │  
 ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤  
 │ 2026-06-03 19:29 UTC │ Certificate expired                                                                                                                   │  
 ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤  
 │ 2026-06-03 20:16 UTC │ cert-manager pod restarted (was at 3m59s age) — re-evaluated the order                                                                │  
 ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤  
 │ 2026-06-03 20:18 UTC │ cert-manager hit LE API → 404: No order for ID 507326254665 → marked issuance Failed                                                  │  
 └──────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

 \#\#\# Current State

   
   Certificate xpro-cert:       READY=False, Reason=Expired+Failed  
   CertificateRequest xpro-cert-2: APPROVED but READY=False (Failed)  
   Order xpro-cert-2-1040610603:   state=errored (LE returned 404\)  
   Challenge xpro-cert-2-…:        state=expired

 \#\#\# Why did the DNS-01 challenge fail 30 days ago?

 The ClusterIssuer correctly selects dns01.route53: {} for \*.odl.mit.edu. The challenge expired — meaning cert-manager either:  
 1\. Created the \_acme-challenge.xpro-web.odl.mit.edu TXT record in Route53 but Let's Encrypt's validation never succeeded (IAM permissions, DNS propagation issue, or the cert-manager pod was unstable), or  
 2\. cert-manager crashed before it could place the record (that cert-manager pod restart at 20:16 today suggests instability — worth checking if this was a recurring pattern over the past 30 days)

 ────────────────────────────────────────────────────────────────────────────────

 Immediate Fix

 cert-manager is stuck because it sees FailedIssuanceAttempts=1 and its backoff hasn't elapsed yet. Delete the failed CertificateRequest — cert-manager will immediately create a new one and retry:

 ```bash  
   \# Delete the stale CertificateRequest (the Order is owned by it and will be GC'd)  
   kubectl \--context applications-production delete certificaterequest xpro-cert-2 \-n xpro

   \# Also clean up the stale first request  
   kubectl \--context applications-production delete certificaterequest xpro-cert-1 \-n xpro

   \# Watch the new attempt  
   kubectl \--context applications-production get certificaterequests,orders,challenges \-n xpro \-w  
 

 cert-manager will create xpro-cert-3, a new Order, and a new DNS-01 challenge for \_acme-challenge.xpro-web.odl.mit.edu in Route53.

 Investigate the cert-manager Restart

 Check whether this pod has been crashing repeatedly over the past 30 days (which would explain the challenge never completing):

bash  
   \# Check restart count and previous logs  
   kubectl \--context applications-production get pod \-n operations cert-manager-79db76488d-zxscj \-o jsonpath='{.status.containerStatuses\[0\].restartCount}'

   \# Previous terminated container logs  
   kubectl \--context applications-production logs \-n operations cert-manager-79db76488d-zxscj \--previous 2\>&1 | tail \-50  
 

 Relevant Code Reference

 In src/ol\_infrastructure/applications/xpro/\_main\_.py (line \~\`cert\_manager\_certificate\`), the cert is configured as:

python  
   OLCertManagerCertConfig(  
       application\_name="xpro",  
       k8s\_namespace="xpro",  
       create\_apisixtls\_resource=True,  
       dest\_secret\_name="xpro-tls-pair",  
       dns\_names=\[app\_domain\],   \# → "xpro-web.odl.mit.edu"  
   )  
 

 xpro-web.odl.mit.edu correctly matches the .odl.mit.edu selector in the ClusterIssuer, so it uses DNS-01 via Route53. The Pulumi code itself is correct — this is a runtime cert-manager/ACME issue, not a code defect.  
```

### **Root causes**

- **Why was the XPro production site vending 503 cert invalid errors to customers?**  
  **\- Because the Kubernetes CertManager renewal attempt had failed and its backoff period had not expired.**  
- **Why did the Kubernetes ACME CertManager renewal fail?**  
  **\- Because 30 days prior a bug in our Pulumi fastly code errantly instructed Fastly to generate a certificate for the XPro back-end in addition to the front-end which it properly controls.**   
- **Why did the Pulumi fastly code fail?**  
  **\- Because a for loop omitted a necessary conditional to skip the back-end domain**


### **Mitigation and resolution**

As Claude suggested Tobias deleted and re-created the certificate object manually which resolved the immediate issue.

### **Lessons learnt**

We prevented this problem from recurring [with this pull request](https://github.com/mitodl/ol-infrastructure/pull/4713). We welcome feedback on how we might test for this kind of edge case in a generalized way. Trying to test the subtle interactions of 3 cloud services is highly problematic.

## ---

**⌛ Timeline**

[View on Rootly](https://rootly.com/account/incidents/7-https-xpro-mit-edu-outage?tab=timeline)

| Date | Source | User | Event |
| :---- | :---- | :---- | :---- |
| June 3 4:08 PM EDT | web | Christoper Patti |  Christoper Patti created this incident  |
| June 3 3:38 PM EDT | web |  | Initial alert received |
| June 3 4:08 PM EDT | web | Christoper Patti |  Started date has been set to June 3 4:08 PM EDT    |
| June 3 4:08 PM EDT | web | Rootly |    [Slack Channel](https://slack.com/app_redirect?channel=C0B821X9N3G&team=T04JRPJF6) has been created  |
| June 3 4:38 PM EDT | web | Tobias Macey |  Incident has been resolved  |
| June 3 4:38 PM EDT | web | Tobias Macey |  Mitigated date has been set to June 3 4:38 PM EDT    |
| June 3 4:38 PM EDT | web | Tobias Macey |  Resolved date has been set to June 3 4:38 PM EDT    |

---

