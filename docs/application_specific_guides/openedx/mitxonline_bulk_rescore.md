# MITx Online Bulk Rescore

The one-liner for the bulk rescore is:
```
kubectl exec -it $(kubectl get pods --context applications-production -n mitxonline-openedx --selector=[ol.mit.edu/component=edxapp-lms-webapp](http://ol.mit.edu/component=edxapp-lms-webapp) -o json | jq -r '.items[0].metadata.name') -n mitxonline-openedx --context applications-production -- python manage.py lms shell < scripts/openedx/bulk_rescore_courses.py
```
First step is to modify that [bulk_rescore_courses](https://github.com/mitodl/ol-infrastructure/blob/main/scripts/openedx/bulk_rescore_courses.py#L296)
file to include the list of course IDs that you want to run the rescore on.

For example:

```
"course-v1:MITxT+10.50.CH01x+1T2025",
```
