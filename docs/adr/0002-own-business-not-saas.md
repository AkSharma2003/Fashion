# ADR 0002: Own business, not a multi-tenant SaaS

Status: accepted

FashionOS serves one business (one shop and its website). There is no tenant table, no tenant_id, no
subscription billing and no row-level tenant isolation. A SaaS platform for other brands is parked.

Consequence: simpler code and tests. If SaaS is wanted later it is a new project phase with its own SRS.
