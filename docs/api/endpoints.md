# Endpoint list

Generated from the API by `python -m scripts.gen_api_docs` (in `apps/api`). Do not edit by hand. 201 operations.
Request and response fields: `http://localhost:8000/docs`. Conventions: [README.md](README.md).

## ai

| Method | Path | What it does |
|---|---|---|
| POST | `/api/v1/ai/chat` | Chat Message |
| POST | `/api/v1/ai/describe` | Describe |
| GET | `/api/v1/ai/forecast` | Forecast |
| POST | `/api/v1/ai/index/refresh` | Refresh Index |
| GET | `/api/v1/ai/missing-requests` | Missing Requests |
| POST | `/api/v1/ai/missing-requests` | Add Missing |
| PATCH | `/api/v1/ai/missing-requests/{request_id}` | Update Missing |
| POST | `/api/v1/ai/poster` | Poster |
| POST | `/api/v1/ai/poster/copy` | Poster Copy |
| GET | `/api/v1/ai/recommendations` | Recommendations |
| GET | `/api/v1/ai/search` | Smart Search |
| POST | `/api/v1/ai/size` | Size Help |
| GET | `/api/v1/ai/size-chart` | Size Chart |
| GET | `/api/v1/ai/trends` | Trends |
| GET | `/api/v1/ai/usage` | Usage |
| POST | `/api/v1/ai/visual-search` | Visual Search |
| GET | `/api/v1/ai/what-to-buy` | What To Buy |

## auth

| Method | Path | What it does |
|---|---|---|
| POST | `/api/v1/auth/google` | Google Sign In |
| GET | `/api/v1/auth/google/config` | Google Config |
| POST | `/api/v1/auth/login` | Login |
| GET | `/api/v1/auth/me` | Get Current User Info |
| POST | `/api/v1/auth/otp/send` | Send Otp |
| POST | `/api/v1/auth/otp/verify` | Verify Otp |
| POST | `/api/v1/auth/refresh` | Refresh Token |
| GET | `/api/v1/auth/registered-users` | Registered Users |
| POST | `/api/v1/auth/registered-users/{customer_id}/role` | Give Role |
| POST | `/api/v1/auth/registered-users/{customer_id}/role/remove` | Remove Role |
| GET | `/api/v1/auth/role-history` | Role History |
| GET | `/api/v1/auth/roles` | List Roles |
| POST | `/api/v1/auth/sign-in` | Sign In |
| GET | `/api/v1/auth/users` | List Staff Users |
| POST | `/api/v1/auth/users` | Create Staff User |
| PATCH | `/api/v1/auth/users/{user_id}` | Update Staff User |

## catalog

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/catalog/` | List Products |
| POST | `/api/v1/catalog/` | Create Product |
| GET | `/api/v1/catalog/{product_id}` | Get Product |
| PATCH | `/api/v1/catalog/{product_id}` | Update Product |
| DELETE | `/api/v1/catalog/{product_id}` | Deactivate Product |
| GET | `/api/v1/catalog/{product_id}/images` | List Product Images |
| POST | `/api/v1/catalog/{product_id}/images` | Upload Product Image Endpoint |
| PUT | `/api/v1/catalog/{product_id}/images/{image_id}` | Replace Product Image |
| DELETE | `/api/v1/catalog/{product_id}/images/{image_id}` | Remove Product Image |
| DELETE | `/api/v1/catalog/{product_id}/permanent` | Delete Product Permanently |
| GET | `/api/v1/catalog/{product_id}/variants` | List Variants |
| POST | `/api/v1/catalog/{product_id}/variants` | Create Catalog Variant |
| PATCH | `/api/v1/catalog/{product_id}/variants/{variant_id}` | Update Catalog Variant |
| DELETE | `/api/v1/catalog/{product_id}/variants/{variant_id}` | Deactivate Catalog Variant |
| DELETE | `/api/v1/catalog/{product_id}/variants/{variant_id}/permanent` | Delete Variant Permanently |

## customers

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/customers/customers` | List Customer |
| POST | `/api/v1/customers/customers` | Created Customer |
| POST | `/api/v1/customers/customers/website/register` | Website Register |
| POST | `/api/v1/customers/customers/website/verify-otp` | Website Verify Otp |
| GET | `/api/v1/customers/customers/{customer_id}` | Get Customer |
| PUT | `/api/v1/customers/customers/{customer_id}` | Update Customer |
| DELETE | `/api/v1/customers/customers/{customer_id}` | Delete Customer |

## employees

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/employees` | List Employees |
| POST | `/api/v1/employees` | Create Employee |
| GET | `/api/v1/employees/attendance` | Attendance For Day |
| POST | `/api/v1/employees/attendance` | Mark Attendance Bulk |
| PATCH | `/api/v1/employees/{employee_id}` | Update Employee |
| GET | `/api/v1/employees/{employee_id}/advances` | List Advances |
| POST | `/api/v1/employees/{employee_id}/advances` | Give Advance |
| GET | `/api/v1/employees/{employee_id}/attendance` | Employee Attendance |
| POST | `/api/v1/employees/{employee_id}/salary-payments` | Record Salary Payment |
| GET | `/api/v1/employees/{employee_id}/statement` | Employee Statement |

## fp

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/fp/cost` | Cost Report |
| GET | `/api/v1/fp/jobs` | List Jobs |
| GET | `/api/v1/fp/jobs/{job_id}` | Get Job |
| POST | `/api/v1/fp/jobs/{job_id}/assign` | Assign Job |
| POST | `/api/v1/fp/jobs/{job_id}/incidents` | Add Incident |
| POST | `/api/v1/fp/jobs/{job_id}/status` | Set Job Status |
| POST | `/api/v1/fp/materials` | Add Material |
| GET | `/api/v1/fp/workers` | List Workers |
| POST | `/api/v1/fp/workers` | Create Worker |
| PATCH | `/api/v1/fp/workers/{worker_id}` | Update Worker |
| POST | `/api/v1/fp/workers/{worker_id}/payments` | Pay Worker |
| GET | `/api/v1/fp/workers/{worker_id}/statement` | Worker Statement |

## internal

| Method | Path | What it does |
|---|---|---|
| POST | `/api/v1/internal/ai/refresh` | Ai Refresh |
| POST | `/api/v1/internal/khata/integrity` | Khata Integrity |
| POST | `/api/v1/internal/khata/reminders` | Khata Reminders |
| POST | `/api/v1/internal/orders/release-expired` | Release Expired |
| POST | `/api/v1/internal/outbox/messages` | Send Messages |
| POST | `/api/v1/internal/tally/backlog` | Tally Backlog |
| POST | `/api/v1/internal/tally/reconcile` | Tally Reconcile |

## inventory

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/inventory/stock` | Get Stock |
| POST | `/api/v1/inventory/stock/adjustments` | Adjust Stock |
| POST | `/api/v1/inventory/stock/counts` | Create Stock Count |
| GET | `/api/v1/inventory/stock/{variant_id}/movements` | Get Movements |
| POST | `/api/v1/inventory/variants` | Create Variant |

## khata

| Method | Path | What it does |
|---|---|---|
| POST | `/api/v1/khata/account` | Create Khata Account |
| GET | `/api/v1/khata/account/{khata_id}` | Get Khata Account |
| PATCH | `/api/v1/khata/account/{khata_id}/activate` | Activate Khata Account |
| PATCH | `/api/v1/khata/account/{khata_id}/deactivate` | Deactivate Khata Account |
| GET | `/api/v1/khata/accounts` | List Accounts |
| POST | `/api/v1/khata/accounts` | Open Account |
| GET | `/api/v1/khata/accounts/{account_id}` | Get Account |
| PATCH | `/api/v1/khata/accounts/{account_id}` | Update Account |
| POST | `/api/v1/khata/accounts/{account_id}/adjustments` | Adjust |
| GET | `/api/v1/khata/accounts/{account_id}/ledger` | Get Ledger |
| POST | `/api/v1/khata/accounts/{account_id}/paylink` | Make Paylink |
| POST | `/api/v1/khata/accounts/{account_id}/payments` | Receive Payment |
| GET | `/api/v1/khata/customer/{customer_id}/account` | Get Customer Khata |
| POST | `/api/v1/khata/customers/{customer_id}/make-khata` | Make Khata Customer |
| POST | `/api/v1/khata/customers/{customer_id}/make-normal` | Make Normal Customer |
| GET | `/api/v1/khata/integrity` | Integrity |
| GET | `/api/v1/khata/lookup` | Lookup By Phone |
| GET | `/api/v1/khata/reports/ageing` | Ageing Report |

## messages

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/messages` | List Messages |
| POST | `/api/v1/messages/optins` | Set Optin |
| GET | `/api/v1/messages/{job_id}` | Get Message |
| POST | `/api/v1/messages/{job_id}/resend` | Resend |

## orders

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/orders` | List Orders |
| GET | `/api/v1/orders/{order_id}` | Get Order |
| POST | `/api/v1/orders/{order_id}/returns` | Create Return |
| POST | `/api/v1/orders/{order_id}/shipment` | Create Shipment |
| PATCH | `/api/v1/orders/{order_id}/status` | Set Status |

## other

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Health |

## pay

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/pay/{token}` | Open Link |
| POST | `/api/v1/pay/{token}/simulate/{razorpay_order_id}` | Simulate Payment |
| POST | `/api/v1/pay/{token}/start` | Start Payment |

## payments

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/payments` | List Payments |

## payroll

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/payroll/me/statement` | My Statement |
| GET | `/api/v1/payroll/runs` | List Runs |
| POST | `/api/v1/payroll/runs` | Create Or Refresh Run |
| GET | `/api/v1/payroll/runs/{run_id}` | Get Run |
| POST | `/api/v1/payroll/runs/{run_id}/approve` | Approve |
| PATCH | `/api/v1/payroll/runs/{run_id}/lines/{line_id}` | Update Line |

## pos

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/pos/bills` | List Bills |
| POST | `/api/v1/pos/bills` | Push Bill |
| GET | `/api/v1/pos/bills/by-number/{bill_no}` | Bill By Number |
| GET | `/api/v1/pos/bills/{bill_id}` | Get Bill |
| POST | `/api/v1/pos/bills/{bill_id}/return` | Return Bill |
| GET | `/api/v1/pos/counters` | List Counters |
| GET | `/api/v1/pos/lookup` | Lookup Code |
| POST | `/api/v1/pos/registers/close` | Close Register |
| GET | `/api/v1/pos/registers/current` | Current Register |
| POST | `/api/v1/pos/registers/open` | Open Register |
| GET | `/api/v1/pos/sync` | Sync |

## purchases

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/purchases` | List Purchases |
| POST | `/api/v1/purchases` | Create Purchase |
| GET | `/api/v1/purchases/orders` | List Pos |
| POST | `/api/v1/purchases/orders` | Create Po |
| POST | `/api/v1/purchases/orders/from-suggestions` | Create Po From Suggestions |
| POST | `/api/v1/purchases/orders/{po_id}/receive` | Receive Po |
| POST | `/api/v1/purchases/orders/{po_id}/status` | Set Po Status |
| GET | `/api/v1/purchases/suppliers` | List Suppliers |
| POST | `/api/v1/purchases/suppliers` | Create Supplier |
| GET | `/api/v1/purchases/{purchase_id}/labels` | Purchase Labels |

## reports

| Method | Path | What it does |
|---|---|---|
| POST | `/api/v1/reports/alerts/{alert_id}/resolve` | Resolve Alert |
| GET | `/api/v1/reports/dashboard` | Dashboard |
| GET | `/api/v1/reports/gst` | Gst |
| GET | `/api/v1/reports/sales` | Sales |

## settings

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/settings` | Get Settings |
| PATCH | `/api/v1/settings` | Update Settings |

## shops

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/shops` | List Shops |
| PATCH | `/api/v1/shops/{shop_id}` | Update Shop |

## store

| Method | Path | What it does |
|---|---|---|
| POST | `/api/v1/store/auth/login` | Customer Login |
| GET | `/api/v1/store/categories` | Categories |
| POST | `/api/v1/store/checkout` | Checkout |
| POST | `/api/v1/store/contact` | Contact |
| GET | `/api/v1/store/contact-messages` | Contact Messages |
| PATCH | `/api/v1/store/contact-messages/{message_id}` | Contact Message Status |
| GET | `/api/v1/store/me` | My Profile |
| PATCH | `/api/v1/store/me` | Update Profile |
| GET | `/api/v1/store/me/addresses` | List Addresses |
| POST | `/api/v1/store/me/addresses` | Add Address |
| PATCH | `/api/v1/store/me/addresses/{address_id}` | Edit Address |
| DELETE | `/api/v1/store/me/addresses/{address_id}` | Delete Address |
| POST | `/api/v1/store/me/addresses/{address_id}/default` | Set Default Address |
| POST | `/api/v1/store/me/photo` | Upload Photo |
| DELETE | `/api/v1/store/me/photo` | Remove Photo |
| GET | `/api/v1/store/me/shopping` | My Shopping |
| PUT | `/api/v1/store/me/shopping` | Save Shopping |
| POST | `/api/v1/store/me/shopping/merge` | Merge Shopping |
| GET | `/api/v1/store/my/orders` | My Orders |
| GET | `/api/v1/store/orders/{order_no}` | Track Order |
| POST | `/api/v1/store/orders/{order_no}/pay` | Retry Payment |
| POST | `/api/v1/store/orders/{order_no}/simulate-payment` | Simulate Order Payment |
| GET | `/api/v1/store/products` | List Products |
| GET | `/api/v1/store/products/{product_id}` | Product Detail |
| GET | `/api/v1/store/search` | Search |

## tally

| Method | Path | What it does |
|---|---|---|
| POST | `/api/v1/tally/heartbeat` | Heartbeat |
| POST | `/api/v1/tally/inbox` | Inbox |
| GET | `/api/v1/tally/issues` | List Issues |
| POST | `/api/v1/tally/issues/{issue_id}/resolve` | Resolve Issue |
| POST | `/api/v1/tally/issues/{issue_id}/retry` | Retry Issue |
| GET | `/api/v1/tally/mappings/items` | Item Mappings |
| POST | `/api/v1/tally/mappings/items` | Add Item Mapping |
| GET | `/api/v1/tally/mappings/ledgers` | Ledger Mappings |
| POST | `/api/v1/tally/mappings/ledgers` | Add Ledger Mapping |
| POST | `/api/v1/tally/mode` | Set Mode |
| GET | `/api/v1/tally/outbox` | List Outbox |
| GET | `/api/v1/tally/outbox/pending` | Pending Outbox |
| POST | `/api/v1/tally/outbox/{event_id}/result` | Outbox Result |
| GET | `/api/v1/tally/overview` | Overview |
| GET | `/api/v1/tally/reconciliation` | List Reconciliation |
| POST | `/api/v1/tally/reconciliation/run` | Run Reconciliation |
| GET | `/api/v1/tally/status` | Status Check |
| POST | `/api/v1/tally/test-sale` | Queue Test Sale |

## webhooks

| Method | Path | What it does |
|---|---|---|
| POST | `/api/v1/webhooks/razorpay` | Razorpay Webhook |
| POST | `/api/v1/webhooks/whatsapp` | Whatsapp Webhook |
