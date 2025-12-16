# MIT Learn Service Architecture Diagram

This document shows all services, components, and infrastructure for the MIT Learn project through a series of focused diagrams.

## 1. High-Level Architecture Overview

```mermaid
graph TB
    Users[Web Users]
    CDN[CDN & DNS Layer<br/>See Diagram 2]
    Gateway[API Gateway & Auth<br/>See Diagram 3]
    Frontend[Frontend Layer<br/>See Diagram 4]
    Application[Application Layer<br/>See Diagram 5]
    Data[Data Storage<br/>See Diagram 6]
    External[External Sources<br/>See Diagram 7]
    CICD[CI/CD Pipeline<br/>See Diagram 8]
    Infrastructure[Infrastructure Mgmt<br/>See Diagram 9]

    Users -->|HTTPS| CDN
    CDN -->|Route| Frontend
    CDN -->|Route| Gateway
    Gateway -->|Auth| Application
    Frontend -->|API Calls| Gateway
    Application -->|Store/Query| Data
    Application -->|Fetch Content| External
    CICD -->|Deploy| Frontend
    CICD -->|Deploy| Application
    Infrastructure -->|Manage| Application
    Infrastructure -->|Manage| Data

    style CDN fill:#f9f,stroke:#333,stroke-width:2px
    style Gateway fill:#9cf,stroke:#333,stroke-width:2px
    style Frontend fill:#9f9,stroke:#333,stroke-width:2px
    style Application fill:#9f9,stroke:#333,stroke-width:2px
    style Data fill:#ff9,stroke:#333,stroke-width:2px
    style External fill:#fcf,stroke:#333,stroke-width:2px
    style CICD fill:#fcc,stroke:#333,stroke-width:2px
    style Infrastructure fill:#cff,stroke:#333,stroke-width:2px
```

---

## 2. CDN & DNS Layer

```mermaid
graph TB
    Users[Web Users]

    subgraph CDN["CDN & DNS"]
        Route53[AWS Route53<br/>DNS Management]
        Fastly[Fastly CDN<br/>TLS 1.3 Termination<br/>Gzip/Brotli Compression]
    end

    NextJS[Next.js Frontend<br/>Port 8062]
    APISIX[APISIX Gateway<br/>Port 8065]

    Users -->|DNS Lookup| Route53
    Users -->|HTTPS| Fastly
    Fastly -->|Frontend Traffic| NextJS
    Fastly -->|API Traffic| APISIX

    Route53 -.->|learn.mit.edu<br/>open.odl.local| Fastly

    style Fastly fill:#f9f,stroke:#333,stroke-width:2px
    style Route53 fill:#f9f,stroke:#333,stroke-width:2px
```

**Infrastructure Links:**
- Route53: [ol-infrastructure/.../mit_learn/__main__.py:949](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/__main__.py#L949)
- Fastly CDN: [ol-infrastructure/.../mit_learn/__main__.py:802](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/__main__.py#L802)

---

## 3. API Gateway & Authentication

```mermaid
graph TB
    Fastly[From Fastly CDN]

    subgraph Gateway["API Gateway & Auth Layer"]
        APISIX[Apache APISIX<br/>API Gateway<br/>Port 8065]
        Keycloak[Keycloak<br/>SSO Provider<br/>OAuth2/OIDC<br/>Realm: olapps]
    end

    Nginx[To Nginx/Django]

    Fastly -->|API Requests| APISIX
    APISIX -->|Authenticate| Keycloak
    APISIX -->|Proxy| Nginx
    Keycloak -.->|JWT Tokens| APISIX

    style APISIX fill:#9cf,stroke:#333,stroke-width:2px
    style Keycloak fill:#9cf,stroke:#333,stroke-width:2px
```

**Infrastructure Links:**
- APISIX: [ol-infrastructure/.../mit_learn/__main__.py:1200](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/__main__.py#L1200)
- Keycloak: [ol-infrastructure/.../mit_learn/__main__.py:1224](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/__main__.py#L1224)
- Local: [docker-compose.services.yml:96](https://github.com/mitodl/mit-learn/blob/main/docker-compose.services.yml#L96)

---

## 4. Frontend Layer (Kubernetes)

```mermaid
graph TB
    Fastly[From Fastly CDN]
    Gateway[From APISIX]

    subgraph Frontend["Frontend - Blue/Green Deployment"]
        Service[Kubernetes Service<br/>mit-learn-nextjs]
        Blue[Next.js Blue<br/>Deployment]
        Green[Next.js Green<br/>Deployment]
        BuildJob[Build Job<br/>yarn build]
        EFS[AWS EFS<br/>Build Cache]
        ConfigMap[ConfigMap<br/>Deployment State]
    end

    Fastly -->|Frontend Requests| Service
    Service -->|Active| Blue
    Service -->|Inactive| Green
    BuildJob -->|Build Assets| EFS
    Blue -->|Read Cache| EFS
    Green -->|Read Cache| EFS
    ConfigMap -.->|Tracks Active| Service
    Blue -->|API Calls| Gateway
    Green -->|API Calls| Gateway

    style Service fill:#9f9,stroke:#333,stroke-width:2px
    style Blue fill:#9f9,stroke:#333,stroke-width:2px
    style Green fill:#9f9,stroke:#333,stroke-width:2px
    style BuildJob fill:#9f9,stroke:#333,stroke-width:2px
    style EFS fill:#fc9,stroke:#333,stroke-width:2px
```

**Details:**
- **Node Version:** 22.21
- **Blue/Green Toggle:** Auto-toggle enabled by default
- **Build Process:** K8s Job runs `yarn build`, stores to EFS
- **Service Routing:** Points to active deployment (blue or green)

**Infrastructure Links:**
- Next.js App: [ol-infrastructure/.../mit_learn_nextjs/__main__.py](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn_nextjs/__main__.py)
- Build Job: [ol-infrastructure/.../mit_learn_nextjs/__main__.py:192](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn_nextjs/__main__.py#L192)
- EFS Storage: [ol-infrastructure/.../mit_learn_nextjs/__main__.py:166](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn_nextjs/__main__.py#L166)
- Local: [docker-compose.apps.yml:30](https://github.com/mitodl/mit-learn/blob/main/docker-compose.apps.yml#L30)

---

## 5. Application Layer (Kubernetes)

```mermaid
graph TB
    APISIX[From APISIX Gateway]

    subgraph Application["Django Application Layer"]
        Nginx[Nginx<br/>Reverse Proxy]
        Web[Django Web<br/>uWSGI/Granian<br/>HPA: 2-10 replicas]

        subgraph Celery["Celery Workers"]
            Beat[Celery Beat<br/>RedBeat Scheduler]
            Default[Default Queue<br/>Max 20 replicas]
            EDX[EDX Content Queue<br/>ETL Tasks]
            Embeddings[Embeddings Queue<br/>Max 30 replicas]
        end
    end

    Redis[To Redis]
    Postgres[To PostgreSQL]
    External[To External Sources]
    AI[To AI Services]

    APISIX -->|HTTP| Nginx
    Nginx -->|WSGI| Web
    Web -->|Cache/Queue| Redis
    Web -->|Store Data| Postgres

    Beat -->|Schedule Tasks| Redis
    Default -->|Process Tasks| Redis
    EDX -->|Process Tasks| Redis
    Embeddings -->|Process Tasks| Redis

    Default -->|Update Data| Postgres
    EDX -->|Fetch Content| External
    EDX -->|Update Data| Postgres
    Embeddings -->|Generate Vectors| AI
    Embeddings -->|Store Vectors| Postgres

    style Nginx fill:#9f9,stroke:#333,stroke-width:2px
    style Web fill:#9f9,stroke:#333,stroke-width:2px
    style Beat fill:#9f9,stroke:#333,stroke-width:2px
    style Default fill:#9f9,stroke:#333,stroke-width:2px
    style EDX fill:#9f9,stroke:#333,stroke-width:2px
    style Embeddings fill:#9f9,stroke:#333,stroke-width:2px
```

**Details:**
- **Python Version:** 3.12
- **Web Server:** uWSGI or Granian (configurable)
- **Autoscaling:** CPU (60%) and Memory (80%) based
- **Celery Queues:**
  - **default:** General background tasks
  - **edx_content:** ETL from external course providers
  - **embeddings:** AI vector generation (120min schedule)

**Infrastructure Links:**
- Django App: [ol-infrastructure/.../mit_learn/__main__.py:1417](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/__main__.py#L1417)
- Celery Workers: [ol-infrastructure/.../mit_learn/__main__.py:1443](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/__main__.py#L1443)
- Local: [docker-compose.apps.yml:5](https://github.com/mitodl/mit-learn/blob/main/docker-compose.apps.yml#L5)

---

## 6. Data Storage Layer

```mermaid
graph TB
    Web[From Django Web]
    Celery[From Celery Workers]

    subgraph Storage["Data Storage Services"]
        RDS[(PostgreSQL 15<br/>Database: mitopen<br/>MD5 Password Encryption)]
        Redis[(ElastiCache Valkey 7.2<br/>3 Replicas<br/>Encrypted)]
        OpenSearch[(OpenSearch 3.1.0<br/>Full-Text Search)]
        Qdrant[(Qdrant<br/>Vector Database<br/>Collection: mitlearn-env)]
        S3Legacy[S3 Legacy Bucket<br/>ol-mitopen-app-storage]
        S3New[S3 New Bucket<br/>ol-mitlearn-app-storage]
    end

    Vault[From Vault<br/>Dynamic Credentials]

    Web -->|Read/Write| RDS
    Web -->|Cache/Queue| Redis
    Web -->|Search| OpenSearch
    Web -->|Vector Search| Qdrant
    Web -->|Store Files| S3Legacy
    Web -->|Store Files| S3New

    Celery -->|Read/Write| RDS
    Celery -->|Messages| Redis
    Celery -->|Index| OpenSearch
    Celery -->|Store Vectors| Qdrant

    Vault -.->|DB Credentials<br/>24hr TTL| RDS

    style RDS fill:#ff9,stroke:#333,stroke-width:2px
    style Redis fill:#ff9,stroke:#333,stroke-width:2px
    style OpenSearch fill:#ff9,stroke:#333,stroke-width:2px
    style Qdrant fill:#ff9,stroke:#333,stroke-width:2px
    style S3Legacy fill:#fc9,stroke:#333,stroke-width:2px
    style S3New fill:#fc9,stroke:#333,stroke-width:2px
```

**Details:**
- **PostgreSQL:** Public access enabled for Hightouch/Airbyte integrations
- **Redis:** Cluster mode disabled, encryption at rest and in transit
- **OpenSearch:** 2 shards, 2 replicas
- **Qdrant:** Hosted externally, uses text-embedding-3-large (3072 dimensions)
- **S3:** Both buckets have public read access

**Infrastructure Links:**
- PostgreSQL: [ol-infrastructure/.../mit_learn/__main__.py:517](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/__main__.py#L517)
- Valkey/Redis: [ol-infrastructure/.../mit_learn/__main__.py:1348](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/__main__.py#L1348)
- OpenSearch: [ol-infrastructure/.../aws/opensearch/__main__.py](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/infrastructure/aws/opensearch/__main__.py)
- S3 Buckets: [ol-infrastructure/.../mit_learn/__main__.py:145](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/__main__.py#L145)
- Local: [docker-compose.services.yml:10](https://github.com/mitodl/mit-learn/blob/main/docker-compose.services.yml#L10)

---

## 7. External Integrations & Services

### 7a. External Content Sources (ETL)

```mermaid
graph TB
    Celery[Celery EDX Content Queue]

    subgraph MIT["MIT Course Sources"]
        XPRO[MIT xPRO<br/>xpro.mit.edu/api]
        XOnline[MIT xOnline<br/>S3: mitx-etl-mitxonline]
        PE[MIT Professional Ed<br/>professional.mit.edu]
        SEE[Sloan Executive Ed<br/>executive.mit.edu]
        CSAIL[MIT CSAIL<br/>cap.csail.mit.edu]
        ProLearn[MIT ProLearn<br/>prolearn.mit.edu/graphql]
    end

    subgraph OpenContent["Open Content Sources"]
        OCW[MIT OCW<br/>ocw.mit.edu<br/>S3: ocw-content-storage]
        EDX[edX Platform<br/>api.edx.org]
        OLL[OpenLearningLibrary<br/>S3: ol-data-lake]
        MicroMasters[MicroMasters<br/>micromasters.mit.edu/api]
        YouTube[YouTube API<br/>Video Content]
    end

    Celery -->|Fetch Courses| XPRO
    Celery -->|Fetch Courses| XOnline
    Celery -->|Fetch Courses| PE
    Celery -->|Fetch Courses| SEE
    Celery -->|Fetch Courses| CSAIL
    Celery -->|Fetch Courses| ProLearn
    Celery -->|Fetch Courses| OCW
    Celery -->|Fetch Courses| EDX
    Celery -->|Fetch Courses| OLL
    Celery -->|Fetch Courses| MicroMasters
    Celery -->|Fetch Videos| YouTube

    style XPRO fill:#fcf,stroke:#333,stroke-width:2px
    style XOnline fill:#fcf,stroke:#333,stroke-width:2px
    style OCW fill:#fcf,stroke:#333,stroke-width:2px
    style EDX fill:#fcf,stroke:#333,stroke-width:2px
```

**ETL Schedule:**
- Most sources: Daily or hourly
- YouTube: Every 14400s (4 hours) for videos, 21600s (6 hours) for transcripts
- Embeddings: Every 120 minutes

### 7b. Supporting External Services

```mermaid
graph TB
    Web[Django Web App]
    Celery[Celery Workers]

    subgraph Support["Supporting Services"]
        Tika[Apache Tika 2.5.0<br/>Text Extraction<br/>Port 9998]
        Mailgun[Mailgun<br/>Email Delivery<br/>mitopen-support@mit.edu]
        Sentry[Sentry<br/>Error Tracking<br/>25% Sample Rate]
        PostHog[PostHog<br/>Analytics<br/>Project: 63497]
        OpenAI[OpenAI API<br/>GPT-4o OCR<br/>text-embedding-3-large]
        LiteLLM[LiteLLM<br/>Token Encoding<br/>cl100k_base]
        VectorProxy[Vector Log Proxy<br/>Log Aggregation]
    end

    Web -->|Extract Text| Tika
    Web -->|Send Emails| Mailgun
    Web -->|Log Errors| Sentry
    Web -->|Track Events| PostHog
    Web -->|Send Logs| VectorProxy

    Celery -->|Extract Text| Tika
    Celery -->|Generate Embeddings| OpenAI
    Celery -->|Encode Tokens| LiteLLM

    style Tika fill:#fcf,stroke:#333,stroke-width:2px
    style Mailgun fill:#fcf,stroke:#333,stroke-width:2px
    style Sentry fill:#fcf,stroke:#333,stroke-width:2px
    style PostHog fill:#fcf,stroke:#333,stroke-width:2px
    style OpenAI fill:#fcf,stroke:#333,stroke-width:2px
```

**Local Service:**
- Tika: [docker-compose.services.yml:67](https://github.com/mitodl/mit-learn/blob/main/docker-compose.services.yml#L67)

---

## 8. CI/CD Pipeline (Concourse)

### 8a. Backend Pipeline: mit-learn

```mermaid
graph TB
    subgraph Source["Source Repository"]
        MainBranch[main branch<br/>GitHub: mitodl/mit-learn]
        RCBranch[release-candidate<br/>branch]
        ReleaseBranch[release branch<br/>Tags: v0.x.x]
    end

    subgraph Build["Concourse Build Jobs"]
        MainBuild[Build Main<br/>Tag: latest + git-ref]
        RCBuild[Build RC<br/>Tag: version from settings.py]
    end

    subgraph Registry["Container Registries"]
        DockerHub[Docker Hub<br/>mitodl/mit-learn-app]
        ECR[AWS ECR<br/>mitodl/mit-learn-app]
    end

    subgraph Deploy["Pulumi Deployments"]
        CI[Deploy CI<br/>Stack: mit_learn.CI]
        QA[Deploy QA<br/>Stack: mit_learn.QA]
        Prod[Deploy Production<br/>Stack: mit_learn.Production]
    end

    MainBranch -->|Trigger| MainBuild
    RCBranch -->|Trigger| RCBuild

    MainBuild -->|Push| DockerHub
    MainBuild -->|Push| ECR
    RCBuild -->|Push| DockerHub
    RCBuild -->|Push| ECR

    MainBuild -->|Deploy| CI
    RCBuild -->|Deploy| QA
    ReleaseBranch -->|Promote RC Image| Prod

    style MainBuild fill:#fcc,stroke:#333,stroke-width:2px
    style RCBuild fill:#fcc,stroke:#333,stroke-width:2px
    style CI fill:#fcc,stroke:#333,stroke-width:2px
    style QA fill:#fcc,stroke:#333,stroke-width:2px
    style Prod fill:#fcc,stroke:#333,stroke-width:2px
```

**Pipeline Details:**
- **Dockerfile:** `./Dockerfile` (root of repository)
- **Version Extraction:** `grep VERSION main/settings.py`
- **Environment Variables:** `MIT_LEARN_DOCKER_TAG` injected into Pulumi

### 8b. Frontend Pipeline: mit-learn-nextjs

```mermaid
graph TB
    subgraph Source["Source Repository"]
        MainBranch[main branch<br/>Same repo: mitodl/mit-learn]
        RCBranch[release-candidate<br/>branch]
        ReleaseBranch[release branch<br/>Tags: v0.x.x]
    end

    subgraph Build["Concourse Build Jobs"]
        MainBuild[Build Main<br/>Target: build_skip_yarn<br/>Tag: latest + git-ref]
        RCBuild[Build RC<br/>Target: build_skip_yarn<br/>Tag: version]
    end

    subgraph Registry["Container Registries"]
        DockerHub[Docker Hub<br/>mitodl/mit-learn-nextjs-app]
        ECR[AWS ECR<br/>mitodl/mit-learn-nextjs-app]
    end

    subgraph Deploy["Pulumi Deployments + CDN"]
        CI[Deploy CI<br/>+ Purge Fastly CI]
        QA[Deploy QA<br/>+ Purge Fastly QA]
        Prod[Deploy Production<br/>+ Purge Fastly Prod]
    end

    MainBranch -->|Trigger| MainBuild
    RCBranch -->|Trigger| RCBuild

    MainBuild -->|Push| DockerHub
    MainBuild -->|Push| ECR
    RCBuild -->|Push| DockerHub
    RCBuild -->|Push| ECR

    MainBuild -->|Deploy| CI
    RCBuild -->|Deploy| QA
    ReleaseBranch -->|Promote RC Image| Prod

    style MainBuild fill:#fcc,stroke:#333,stroke-width:2px
    style RCBuild fill:#fcc,stroke:#333,stroke-width:2px
    style CI fill:#fcc,stroke:#333,stroke-width:2px
    style QA fill:#fcc,stroke:#333,stroke-width:2px
    style Prod fill:#fcc,stroke:#333,stroke-width:2px
```

**Pipeline Details:**
- **Dockerfile:** `frontends/main/Dockerfile.web`
- **Build Target:** `build_skip_yarn`
- **Post-Deploy:** Fastly cache purge for immediate effect
- **Environment Variables:** `MIT_LEARN_NEXTJS_DOCKER_TAG` injected into Pulumi

**Infrastructure Links:**
- Pipeline Definition: [ol-infrastructure/.../k8s_apps/docker_pulumi.py](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_concourse/pipelines/infrastructure/k8s_apps/docker_pulumi.py)
- Meta Pipeline: [ol-infrastructure/.../k8s_apps/meta.py:118](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_concourse/pipelines/infrastructure/k8s_apps/meta.py#L118)

---

## 9. Infrastructure Management

```mermaid
graph TB
    subgraph Apps["Application Services"]
        Django[Django Web<br/>+ Celery Workers]
        NextJS[Next.js Frontend]
    end

    subgraph Infra["Infrastructure Management"]
        Vault[HashiCorp Vault<br/>Secrets Management<br/>Dynamic DB Creds]
        Consul[Consul<br/>Service Discovery<br/>Config Storage]
        EKS[AWS EKS<br/>Kubernetes Cluster<br/>Namespace: mitlearn]
    end

    subgraph Data["Data Layer"]
        RDS[(PostgreSQL)]
        Redis[(Valkey)]
    end

    Django -->|Authenticate| Vault
    NextJS -->|Authenticate| Vault
    Vault -->|Dynamic Creds<br/>24hr TTL| RDS
    Vault -->|Secrets| Django
    Vault -->|Secrets| NextJS

    Django -->|Register Service| Consul
    Consul -->|Config| Django
    Consul -.->|Share Config| XPRO[xPRO Platform]
    Consul -.->|Share Config| XOnline[xOnline Platform]

    EKS -->|Host| Django
    EKS -->|Host| NextJS
    EKS -->|Autoscale| Django
    EKS -->|Blue/Green| NextJS

    style Vault fill:#cff,stroke:#333,stroke-width:2px
    style Consul fill:#cff,stroke:#333,stroke-width:2px
    style EKS fill:#cff,stroke:#333,stroke-width:2px
```

**Details:**
- **Vault:**
  - KV-v2 Mount: `secret-mitlearn`
  - AWS Backend: `aws-mitx`
  - Kubernetes Service Account Authentication
  - Database Roles: `app` (full access), `reverse-etl` (external schema)

- **Consul:**
  - Stores: `learn-api-domain`, `learn-frontend-domain`
  - Integrates with: MIT xPRO, MIT xOnline, MIT edX platforms

- **EKS:**
  - Namespace: `mitlearn`
  - Pod Security Groups enabled
  - HPA for web and celery workers

**Infrastructure Links:**
- Vault: [ol-infrastructure/.../mit_learn/__main__.py:392](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/__main__.py#L392)
- Vault Policy: [ol-infrastructure/.../mit_learn/mitlearn_policy.hcl](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/mitlearn_policy.hcl)
- Consul: [ol-infrastructure/.../mit_learn/__main__.py:1224](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/__main__.py#L1224)
- EKS: [ol-infrastructure/.../mit_learn/__main__.py:95](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/__main__.py#L95)
- K8s Secrets: [ol-infrastructure/.../mit_learn/k8s_secrets.py](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/k8s_secrets.py)

---

## Environment-Specific Deployments

The infrastructure supports three environments:
- **CI:** Development/testing (deployed from `main` branch)
- **QA/RC:** Staging for pre-production testing (deployed from `release-candidate` branch)
- **Production:** Live environment (deployed from `release` branch with version tags)

Each environment has separate:
- Kubernetes deployments
- Database instances (RDS)
- Redis clusters (ElastiCache)
- OpenSearch domains
- S3 buckets (suffixed: `-ci`, `-rc`, `-production`)
- DNS records (production: `learn.mit.edu`, staging: `open.odl.local`)
- Fastly CDN configurations

---

## Key Infrastructure Links

### Primary Infrastructure Definitions
- **MIT Learn Backend (Pulumi)**: [ol-infrastructure/src/ol_infrastructure/applications/mit_learn/__main__.py](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/__main__.py)
- **MIT Learn Next.js (Pulumi)**: [ol-infrastructure/src/ol_infrastructure/applications/mit_learn_nextjs/__main__.py](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn_nextjs/__main__.py)
- **OpenSearch Cluster (Pulumi)**: [ol-infrastructure/src/ol_infrastructure/infrastructure/aws/opensearch/__main__.py](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/infrastructure/aws/opensearch/__main__.py)
- **Kubernetes Secrets**: [ol-infrastructure/src/ol_infrastructure/applications/mit_learn/k8s_secrets.py](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/applications/mit_learn/k8s_secrets.py)
- **Backend Concourse Pipeline**: [ol-infrastructure/src/ol_concourse/pipelines/infrastructure/k8s_apps/docker_pulumi.py](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_concourse/pipelines/infrastructure/k8s_apps/docker_pulumi.py)
- **Pipeline Meta-Configuration**: [ol-infrastructure/src/ol_concourse/pipelines/infrastructure/k8s_apps/meta.py](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_concourse/pipelines/infrastructure/k8s_apps/meta.py)

### Local Development
- **Main Compose**: [docker-compose.yml](https://github.com/mitodl/mit-learn/blob/main/docker-compose.yml)
- **Services**: [docker-compose.services.yml](https://github.com/mitodl/mit-learn/blob/main/docker-compose.services.yml)
- **Applications**: [docker-compose.apps.yml](https://github.com/mitodl/mit-learn/blob/main/docker-compose.apps.yml)
- **OpenSearch**: [docker-compose.opensearch.single-node.yml](https://github.com/mitodl/mit-learn/blob/main/docker-compose.opensearch.single-node.yml)

---

## Traffic Flow Summary

1. **User Request** → Fastly CDN (TLS termination, caching, compression)
2. **Fastly** → Routes to:
   - Next.js Frontend (static/dynamic pages)
   - APISIX API Gateway (API requests)
3. **APISIX** → Authenticates via Keycloak (OIDC/OAuth2)
4. **APISIX** → Proxies to Nginx → Django
5. **Django** → Uses:
   - PostgreSQL (relational data)
   - Redis (caching + Celery message broker)
   - OpenSearch (full-text search)
   - Qdrant (vector similarity search)
   - S3 (file storage)
6. **Celery Workers** → Background processing:
   - **Default Queue:** General tasks (emails, cleanup)
   - **EDX Content Queue:** ETL from external sources
   - **Embeddings Queue:** AI vector generation

---

## Monitoring & Observability

- **Logs:** Vector Log Proxy aggregates from Fastly, APISIX, Nginx, Django
- **Errors:** Sentry (25% trace/profile sampling)
- **Analytics:** PostHog (user behavior tracking)
- **Metrics:** CloudWatch (AWS), Kubernetes metrics (KEDA)
- **Health Checks:**
  - `/health/startup/`: Database migrations, cache, Redis, DB connection
  - `/health/liveness/`: DB heartbeat
  - `/health/readiness/`: Cache, Redis, DB ready
  - `/health/full/`: All checks + Celery ping

---

## Security & Secrets

**Vault Secrets Management:**
- Database credentials (dynamic, 24hr TTL)
- API keys (OpenAI, YouTube, edX, Mailgun, etc.)
- OAuth client secrets
- TLS certificates

**Security Groups:**
- Application pods: K8s pod subnets ingress
- Database: App pods + Vault + Hightouch/Airbyte
- Redis: App pods + KEDA autoscaler

**Authentication:**
- Keycloak SSO (realm: `olapps`)
- OIDC/OAuth2 via APISIX
- JWT token-based API access
