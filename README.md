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
- [Local Multi-Tenant Testing (`/etc/hosts`)](#-local-multi-tenant-testing-etchosts)
- [License](#-license)

---

## 📁 Target Monorepo Structure

Based on the `FashionOS` architecture blueprint, below is the implementation file structure:

FashionOS/
├── package.json                 # Root npm workspace
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
│   └── rls-policies/           # PostgreSQL RLS Isolation Scripts
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

---

## 🧱 Backend Module Pattern

Every major business domain in `apps/api/app/modules/<module>/` follows a standardized internal pattern:

apps/api/app/modules//
├── router.py         # API endpoints
├── schemas.py        # Request/response validation
├── service.py        # Core business logic
├── repository.py     # Database operations
├── models.py         # SQLAlchemy models
├── events.py         # Domain/integration events
└── init.py

---

## 📦 Shared Packages

* **`packages/ui`:** Reusable React design-system components (Button, Input, Modal, Card, Table, Drawer, Toast, Form controls)[cite: 5].
* **`packages/shared-types`:** Shared TypeScript types, generated OpenAPI types, and Zod validation schemas[cite: 5].
* **`packages/config`:** Shared ESLint, TypeScript, and Tailwind configurations across all apps[cite: 5].

---

## 🏗 Recommended Build Order

| Phase | Task | Deliverable |
| :--- | :--- | :--- |
| **01** | **Workspace setup** | Root `package.json` + `pnpm-workspace.yaml` + shared config[cite: 5] |
| **02** | **Web foundation** | `apps/web` package.json + Vite + TypeScript + React + Routing[cite: 5] |
| **03** | **Design system** | `packages/ui` + Tailwind + Common UI components[cite: 5] |
| **04** | **API foundation** | FastAPI core + DB session + Auth + Tenancy + Error handling[cite: 5] |
| **05** | **First business modules** | `shops` → `catalog` → `customers` → `inventory` → `orders`[cite: 5] |
| **06** | **Frontend features** | `catalog` → `cart` → `checkout` → `orders` → `owner dashboard`[cite: 5] |
| **07** | **Payments & Khata** | Razorpay, Payment state, Customer credit/Khata[cite: 5] |
| **08** | **AI + worker** | AI service + Celery + Redis + Scheduled jobs[cite: 5] |
| **09** | **Tally cloud** | Tally module + Windows `tally-bridge`[cite: 5] |
| **10** | **Hardening** | RLS policies, Tenant isolation, Contract tests, E2E & Load tests[cite: 5] |

---

## 🔒 Multi-Tenant Data Isolation

Data isolation is guaranteed at the database level using **PostgreSQL Row-Level Security (RLS)**.

```sql
-- PostgreSQL RLS Policy Enforcement
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON products
    FOR ALL
    USING (shop_id = current_setting('app.current_shop_id')::uuid);

🛠 Tech StackLayerTechnologyMonorepo Managementpnpm Workspaces   Frontend AppReact 18, Vite, TypeScript, Tailwind CSS   Core API BackendFastAPI, Python 3.12, SQLAlchemy 2.0 Async   DatabasePostgreSQL 16 with RLS policies   Background TasksCelery & Redis   Ingress & SSLCaddy Server 2   


⚡ Quick Start & Local Setup
Prerequisites
Node.js >= 20.x

Python >= 3.12

pnpm >= 8.x

Docker Desktop

1. Setup Monorepo Workspace

# Install root & workspace dependencies
pnpm install

2. Configure Environment
Bash
cp .env.example .env

3. Launch Local Services
Bash
docker-compose up -d

4. Run Monorepo Apps
Bash
pnpm dev

🌐 Local Multi-Tenant Testing (/etc/hosts)
Map test domains in your /etc/hosts file:

Code snippet
127.0.0.1   platform.local
127.0.0.1   sethifashion.local
127.0.0.1   sharmasarees.local

Access local storefronts:

Sethi Fashion: http://sethifashion.local:3000

Sharma Sarees: http://sharmasarees.local:3000

📜 License
Internal Proprietary Commercial Software — All Rights Reserved.