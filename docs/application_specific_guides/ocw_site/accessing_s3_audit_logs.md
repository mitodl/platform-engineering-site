# Accessing OCW Site S3 Bucket Audit Logs

S3 audit logs for OCW Site are stored in dedicated buckets for each environment:

| Environment | Bucket |
|---|---|
| Production | `ocw-site-audit-logs-production` |
| QA | `ocw-site-audit-logs-qa` |

---

## Using the AWS CLI

### Prerequisites

- The [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed and configured with appropriate credentials.
- Sufficient IAM permissions to read from the audit log buckets.

### Listing Available Log Files

```bash
# Production
aws s3 ls s3://ocw-site-audit-logs-production/ --recursive

# QA
aws s3 ls s3://ocw-site-audit-logs-qa/ --recursive
```

Log files are organized by date prefix, e.g. `2026/04/15/`.

### Downloading Log Files

**Download a single log file:**

```bash
aws s3 cp s3://ocw-site-audit-logs-production/<prefix>/<logfile> ./logfile.gz
```

**Download all logs for a specific date:**

```bash
# Replace YYYY/MM/DD with the date you want
aws s3 cp s3://ocw-site-audit-logs-production/YYYY/MM/DD/ . --recursive
```

**Download all logs to a local directory:**

```bash
aws s3 sync s3://ocw-site-audit-logs-production/ ./ocw-audit-logs-production/
aws s3 sync s3://ocw-site-audit-logs-qa/ ./ocw-audit-logs-qa/
```

### Reading Log Files

S3 server access logs are delivered as gzip-compressed files. You can read them without fully decompressing:

**View a single log file:**

```bash
gunzip -c logfile.gz | less
```

**Search logs for a specific IP address or path:**

```bash
gunzip -c logfile.gz | grep "192.0.2.1"
gunzip -c logfile.gz | grep "GET /some/path"
```

**Process multiple log files at once:**

```bash
# Search all downloaded logs for a keyword
gunzip -c *.gz | grep "ERROR"

# Count requests by HTTP status code
gunzip -c *.gz | awk '{print $9}' | sort | uniq -c | sort -rn
```

S3 access log format is documented in the [AWS S3 Server Access Log Format reference](https://docs.aws.amazon.com/AmazonS3/latest/userguide/LogFormat.html).

---

## Using the AWS Console

### Navigating to the Audit Log Bucket

1. Sign in to the [AWS Console](https://console.aws.amazon.com/).
2. Navigate to **S3** (search for "S3" in the top search bar).
3. In the bucket list, search for and select the appropriate bucket:
    - **Production:** `ocw-site-audit-logs-production`
    - **QA:** `ocw-site-audit-logs-qa`

### Browsing and Downloading Log Files

1. Inside the bucket, browse through the date-based folder hierarchy to find the logs you need.
2. Click on a log file to open its detail page.
3. Click **Download** to save the file locally.

To download multiple files:

1. Check the boxes next to the files or folders you want.
2. Click **Download** from the **Actions** dropdown.

### Reading Log Files in the Console

The AWS Console does not have a built-in log viewer for S3 access logs. After downloading, open the `.gz` file with any tool that supports gzip (e.g., `gunzip`, 7-Zip, macOS Archive Utility) and read the resulting plain-text log.

### Querying Logs with Amazon Athena (Optional)

For large-scale analysis without downloading files, you can query the logs directly using [Amazon Athena](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-s3-access-logs-to-identify-requests.html):

1. In the AWS Console, navigate to **Athena**.
2. Create a table pointed at the audit log bucket using the S3 access log DDL from the [AWS documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-s3-access-logs-to-identify-requests.html#querying-s3-access-logs-for-requests).
3. Run SQL queries directly against the log data in S3.
