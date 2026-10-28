# FashionOS
## Integrated Fashion Retail Management System

### Group Details

- **Group Number:** 11
### Group Details

- **Group Number:** 11

| S. No. | Name                        | Enrollment Number   |
|--------|-----------------------------|---------------------|
| 1      | Ankit Sharma                | 20252651007         |
| 2      | Shubham Gupta               | 20252651021         |
| 3      | Piyush lalchand Menghani    | 20252651039         |
| 4      | Vijay Singh                 | 20252651064         |
| 5      | Vivek Kumar Kosta           | 20252651065         |

### Project Description

FashionOS is an integrated retail management system designed for a fashion business that operates a physical shop and an online website. Both channels share a single inventory system, enabling centralized management of products, stock, billing, and online orders.

The system includes point-of-sale (POS) billing, customer credit management (Khata), WhatsApp bill sharing, online payments, Tally accounting integration, employee management, saree fall-pico service management, and purchasing. It also plans to introduce AI-powered features such as product recommendations, smart search, a customer support chatbot, product description generation, and demand forecasting in later development phases.

The main objective of FashionOS is to simplify retail operations, maintain accurate stock records, reduce duplicate data entry, improve customer credit management, and integrate shop and online business activities into one platform.

### Software Requirements

**Programming Languages:**
- Python
- TypeScript

**Frontend:**
- React
- Vite

**Backend:**
- FastAPI

**Database and Background Processing:**
- PostgreSQL 
- Redis
- Celery

**Development and Infrastructure Tools:**
- Python virtual environment
- Node.js and pnpm
- Docker and Docker Compose
- Git
- Alembic for database migrations

**Integration Requirements:**
- TallyPrime with a Windows-based Tally synchronization agent
- Official WhatsApp Business API through a provider
- Razorpay for online payments and Pay Now links

**Other Requirements:**
- A compatible operating system and web browser
- Internet connectivity for cloud services and integrations
- Environment configuration through the `.env` file

### How to Run the Project

**Prerequisites:** Ensure that the project repository contains the required configuration files, dependencies, and application code. Install Python, Node.js, pnpm, Docker, and Git.

**1. Configure environment variables**

From the project root, copy the example environment file:

```bash
cp .env.example .env
```

Configure the required environment variables in `.env`.

**2. Start PostgreSQL and Redis**

From the project root, run:

```bash
docker compose up -d
```

This starts the database and Redis services defined in the Docker Compose configuration.

**3. Set up the backend API**

Navigate to the API directory:

```bash
cd apps/api
```

Create a Python virtual environment:

```bash
python -m venv .venv
```

Activate the environment.

For Linux/macOS:

```bash
source .venv/bin/activate
```

For Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Apply database migrations:

```bash
alembic upgrade head
```

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload --port 8000
```

The API documentation can be accessed at:

http://localhost:8000/docs

**4. Set up and start the frontend**

Open a new terminal and navigate to the project root. Install the frontend dependencies:

```bash
pnpm install
```

Start the web application:

```bash
pnpm dev:web
```

The frontend can be accessed at:

http://localhost:5173

**5. Verify the application**

Open the frontend and API documentation in a browser. Verify the available features and confirm that the required services are running.

*Note: These instructions describe the documented development setup. Features requiring TallyPrime, WhatsApp, Razorpay, or other external services may require additional configuration. Only implemented features can be verified during execution.*

### Expected Output

The completed FashionOS system is intended to provide a unified platform for managing the physical fashion shop and its online website.

Expected outcomes include:

- Centralized product catalog and shared inventory management.
- Shop billing through a POS interface, including offline billing and synchronization.
- Customer Khata accounts, credit tracking, WhatsApp bills, and payment links.
- Integration with TallyPrime for accounting synchronization and reconciliation.
- Employee attendance, salary, and advance management.
- Saree fall-pico job tracking, quality checks, and worker payment management.
- Online product browsing, checkout, payments, shipping, and returns.
- Purchasing, reporting, access control, and audit logs.
- AI-assisted retail features introduced in later development phases.

The system should maintain accurate financial records, prevent duplicate bills, preserve transaction history, and synchronize data reliably between the shop, website, and accounting system.

The actual output depends on the modules implemented and configured in the project repository. Features that are still planned should be identified as such rather than reported as completed.