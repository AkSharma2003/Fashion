# FashionOS — Multi-Tenant AI Fashion E-Commerce Platform

[![Architecture](https://img.shields.io/badge/Architecture-Multi--Tenant%20SaaS-blue.svg)](#-multi-tenant-data-isolation)
[![Frontend](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite%20%7C%20TypeScript-blue.svg)](#-tech-stack)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python-green.svg)](#-tech-stack)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%2B%20RLS-blueviolet.svg)](#-multi-tenant-data-isolation)

An enterprise-grade, multi-tenant white-label fashion e-commerce platform built for clothing retailers. Built on a **Single Codebase + Dynamic Domain Routing + Row-Level Security (RLS)** architecture with native TallyPrime ERP synchronization and AI microservices.

---

## 📋 Table of Contents

- [Target Monorepo Structure](#-target-monorepo-structure)
- [Backend Module Pattern](#-backend-module-pattern)
- [Shared Packages](#-shared-packages)
- [Recommended Build Order](#-recommended-build-order)
- [Multi-Tenant Data Isolation](#-multi-tenant-data-isolation)
- [Tech Stack](#-tech-stack)
- [Quick Start & Local Setup](#-quick-start--local-setup)
- [Local Multi-Tenant Testing](#-local-multi-tenant-testing-etchosts)
- [Running Tests](#-running-tests)
- [License](#-license)

---

## 📁 Target Monorepo Structure

Based on the `FashionOS` architecture blueprint, below is the implementation file structure:

```text
FashionOS/
├── package.json                 # Root pnpm workspace
├── pnpm-workspace.yaml          # Workspace package discovery
├── .gitignore
├── .env.example
├── docker-compose.yml
├── README.md
│
├── apps/
│   ├── web/                     # React + Vite + TypeScript Storefront & Admin
│   │   ├── package.json
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   ├── tsconfig.app.json
│   │   ├── tsconfig.node.json
│   │   ├── public/
│   │   └── src/
│   │       ├── main.tsx
│   │       ├── index.css
│   │       ├── app/
│   │       │   ├── App.tsx
│   │       │   ├── router.tsx
│   │       │   ├── providers.tsx
│   │       │   ├── tenant/
│   │       │   └── theme/
│   │       ├── routes/
│   │       │   ├── storefront/
│   │       │   ├── owner/
│   │       │   └── admin/
│   │       ├── features/
│   │       │   ├── catalog/
│   │       │   ├── cart/
│   │       │   ├── checkout/
│   │       │   ├── orders/
│   │       │   ├── khata/
│   │       │   ├── requests/
│   │       │   ├── employees/
│   │       │   ├── inventory/
│   │       │   ├── crm/
│   │       │   ├── ai-insights/
│   │       │   ├── banners/
│   │       │   └── tally/
│   │       ├── components/
│   │       └── lib/
│   │           ├── api/
│   │           ├── auth/
│   │           ├── permissions/
│   │           └── i18n/
│   │
│   ├── api/                     # FastAPI Core Engine
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   │   ├── core/
│   │   │   ├── modules/
│   │   │   │   ├── auth/
│   │   │   │   ├── shops/
│   │   │   │   ├── domains/
│   │   │   │   ├── catalog/
│   │   │   │   ├── inventory/
│   │   │   │   ├── customers/
│   │   │   │   ├── orders/
│   │   │   │   ├── payments/
│   │   │   │   ├── khata/
│   │   │   │   ├── employees/
│   │   │   │   ├── requests/
│   │   │   │   ├── notifications/
│   │   │   │   ├── tally/
│   │   │   │   ├── analytics/
│   │   │   │   └── admin/
│   │   │   ├── integrations/
│   │   │   └── main.py
│   │   └── tests/
│   │
│   ├── ai-service/              # AI / ML Microservice
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── api/
│   │       ├── recommend/
│   │       ├── demand/
│   │       ├── embeddings/
│   │       ├── banners/
│   │       ├── vision/
│   │       └── evals/
│   │
│   ├── worker/                  # Celery Background Tasks
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── celery_app.py
│   │       └── tasks/
│   │
│   └── tally-bridge/            # Windows ↔ Tally Desktop Agent
│       ├── README.md
│       ├── config/
│       ├── src/
│       └── installer/
│
├── packages/
│   ├── ui/                      # Shared UI Design System
│   │   ├── package.json
│   │   └── src/
│   ├── shared-types/            # Shared TypeScript Interfaces & DTOs
│   │   ├── package.json
│   │   └── src/
│   └── config/                  # Shared Workspace Configs
│       ├── eslint/
│       ├── typescript/
│       └── tailwind/
│
├── database/
│   ├── migrations/              # Alembic Database Migrations
│   ├── schemas/
│   ├── seeds/
│   └── rls-policies/            # PostgreSQL RLS Isolation Scripts
│
├── docs/
│   ├── architecture/
│   ├── adr/
│   ├── api/
│   └── runbooks/
│
├── infrastructure/
│   ├── docker/
│   ├── caddy/                   # Dynamic SSL & Reverse Proxy
│   ├── terraform/
│   ├── deployment/
│   └── monitoring/
│
├── tests/
│   ├── e2e/
│   ├── tenant-isolation/
│   ├── load/
│   └── contracts/
│
└── scripts/
```

---

## 🧱 Backend Module Pattern

Every major business domain in `apps/api/app/modules/<module>/` follows a standardized internal pattern:

```text
apps/api/app/modules/<module>/
├── router.py         # API endpoints
├── schemas.py        # Request/response validation
├── service.py        # Core business logic
├── repository.py     # Database operations
├── models.py         # SQLAlchemy models
├── events.py         # Domain/integration events
└── __init__.py
```

---

## 📦 Shared Packages

- **`packages/ui`:** Reusable React design-system components (Button, Input, Modal, Card, Table, Drawer, Toast, Form controls).
- **`packages/shared-types`:** Shared TypeScript types, generated OpenAPI types, and Zod validation schemas.
- **`packages/config`:** Shared ESLint, TypeScript, and Tailwind configurations across all apps.

---

## 🏗 Recommended Build Order

| Phase | Task | Deliverable |
| :--- | :--- | :--- |
| **01** | **Workspace setup** | Root `package.json` + `pnpm-workspace.yaml` + shared config |
| **02** | **Web foundation** | `apps/web` package.json + Vite + TypeScript + React + Routing |
| **03** | **Design system** | `packages/ui` + Tailwind + Common UI components |
| **04** | **API foundation** | FastAPI core + DB session + Auth + Tenancy + Error handling |
| **05** | **First business modules** | `shops` → `catalog` → `customers` → `inventory` → `orders` |
| **06** | **Frontend features** | `catalog` → `cart` → `checkout` → `orders` → `owner dashboard` |
| **07** | **Payments & Khata** | Razorpay, Payment state, Customer credit/Khata |
| **08** | **AI + worker** | AI service + Celery + Redis + Scheduled jobs |
| **09** | **Tally cloud** | Tally module + Windows `tally-bridge` |
| **10** | **Hardening** | RLS policies, Tenant isolation, Contract tests, E2E & Load tests |

---

## 🔐 Multi-Tenant Data Isolation

FashionOS uses a **shared database, shared schema** model. Every tenant-owned table carries a `shop_id` column, and PostgreSQL **Row-Level Security (RLS)** policies guarantee that one shop can never read or write another shop's data.

- The tenant is resolved from the incoming domain (e.g. `sethifashion.local`) by the API.
- The resolved `shop_id` is set on the database session before any query runs.
- RLS policies in `database/rls-policies/` enforce isolation at the database level, independent of application code.
- Isolation is verified by the test suite in `tests/tenant-isolation/`.

---

## 🛠 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Monorepo Management** | pnpm Workspaces |
| **Frontend App** | React 18, Vite, TypeScript, Tailwind CSS |
| **Core API Backend** | FastAPI, Python 3.12, SQLAlchemy 2.0 Async |
| **Database** | PostgreSQL 16 with RLS policies |
| **Background Tasks** | Celery & Redis |
| **AI / ML Service** | FastAPI microservice (recommendations, demand forecasting, embeddings, vision) |
| **ERP Integration** | TallyPrime via Windows `tally-bridge` agent |
| **Ingress & SSL** | Caddy Server 2 |

---

## ⚡ Quick Start & Local Setup

### Prerequisites

- **Node.js** >= 20.x
- **Python** >= 3.12
- **pnpm** >= 8.x
- **Docker Desktop**

### Getting Started

#### 1. Setup Monorepo Workspace
```bash
# Install root & workspace dependencies
pnpm install
```

#### 2. Configure Environment
```bash
cp .env.example .env
```

#### 3. Launch Local Services
```bash
docker-compose up -d
```

#### 4. Run Database Migrations
```bash
# Apply schema migrations and RLS policies
cd apps/api && alembic upgrade head
```

#### 5. Run Monorepo Apps
```bash
pnpm dev
```

---

## 🌐 Local Multi-Tenant Testing (`/etc/hosts`)

### 1. Map Test Domains

Add these entries to your hosts file:

```bash
# Linux / macOS: sudo nano /etc/hosts
# Windows: C:\Windows\System32\drivers\etc\hosts (edit as Administrator)

127.0.0.1   platform.local
127.0.0.1   sethifashion.local
127.0.0.1   sharmasarees.local
```

### 2. Access Local Storefronts

- Sethi Fashion: http://sethifashion.local:3000
- Sharma Sarees: http://sharmasarees.local:3000

---

## 🧪 Running Tests

```bash
# Frontend & shared packages
pnpm test

# Backend API tests
cd apps/api && pytest
```

Tenant isolation, contract, E2E, and load tests live in the top-level `tests/` directory.

---

## 📜 License

Internal Proprietary Commercial Software — All Rights Reserved.