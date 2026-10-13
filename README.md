# Civic Issue Reporting and Management System: backend

A REST API for reporting and fixing civic problems such as potholes, garbage and broken streetlights.
Citizens report an issue with a photo and a pin on the map. The system finds the right department by itself,
warns about duplicates, lets workers fix the issue, tells the citizen what happens, and gives the admin
a dashboard. Final-year (TYCS) college project.

## 1. Project description

Three kinds of users work with the same API:

| Role | What they do |
|---|---|
| **Citizen** | Registers, reports issues (optionally anonymous), upvotes other reports, tracks status, gets notifications, earns points and badges |
| **Worker** | Sees the complaints of their own department, starts work, resolves complaints |
| **Admin** | Sees everything, manages departments, categories and workers, watches statistics, overdue complaints, a map and the audit log |

The normal life of a complaint:

```
Citizen reports  ->  category gives the department  ->  duplicate check (100 m, same category)
   -> new complaint (SUBMITTED)  ->  worker starts (IN_PROGRESS)  ->  worker resolves (RESOLVED)
   -> citizen is notified at every step (in-app and e-mail)
   -> if still open after 3 days: marked overdue and the admins are told
   -> points and badges are awarded along the way
```

## 2. Features

- Registration and login with JWT, bcrypt password hashing, role-based access (CITIZEN, WORKER, ADMIN)
- Departments and the 15 issue categories live in the database; admins can change them (nothing is hard-coded)
- Photo upload with type, size and content checks, random file names, replaceable storage backend
- Location as GeoJSON with a `2dsphere` index; "nearby complaints" search
- Duplicate detection: same category within a configurable radius returns the existing complaint instead of creating a new one
- Upvotes with a unique index (one per user and complaint) and an atomic counter
- Human-readable, concurrency-safe complaint numbers such as `CIV-2026-000001`
- Worker portal with strict status transitions `SUBMITTED -> IN_PROGRESS -> RESOLVED`
- Notifications (in-app) and optional e-mail for every status change
- Background job that marks complaints overdue after `OVERDUE_DAYS` and notifies admins
- Points and badges with an idempotent points ledger (no farming)
- Admin: dashboard, statistics, filters, map pins, audit logs, department / category / worker management
- Security: rate limiting on login and register, security headers, request size limits, strict validation, safe error messages, no secrets in logs or responses

## 3. Tech stack

| Part | Technology |
|---|---|
| Language / framework | Python 3.11, FastAPI, Uvicorn |
| Database | MongoDB (Atlas) through async PyMongo, 2dsphere geospatial index |
| Validation | Pydantic v2, pydantic-settings |
| Auth | PyJWT, bcrypt |
| Uploads | python-multipart, `StorageBackend` interface (local disk now, Cloudinary/S3 later) |
| Background job | APScheduler (the Python counterpart of node-cron) |
| E-mail | smtplib (built into Python) |
| Tests | pytest, FastAPI TestClient |

## 4. Folder structure

```
civic-issue-backend/
|-- app/
|   |-- main.py                 create the app, middleware, routes, start-up and shut-down
|   |-- seed.py, seed_data.py   `python -m app.seed`: departments, categories, admin, workers, badges
|   |-- core/                   settings, database, errors, responses, JWT + bcrypt, login dependencies, rate limiter
|   |-- middleware/             security headers, rate limit, request size limit
|   |-- models/                 collection names, document builders, indexes
|   |-- schemas/                Pydantic request bodies (validation)
|   |-- routes/                 URL paths only: they call services and never contain business rules
|   |-- services/               ALL business logic (complaints, duplicates, status, notifications, points, ...)
|   |-- jobs/scheduler.py       the overdue background job
|   `-- storage/                photo storage (local disk behind an interface)
|-- tests/                      pytest tests for every phase
|-- scripts/generate_api_docs.py   rebuilds docs/API.md and the endpoint list below
|-- docs/API.md                 API reference
|-- uploads/                    uploaded photos (not committed)
|-- .env                        your secrets (never committed)
|-- .env.example                the settings, with no secrets
`-- requirements.txt
```

The flow of a request is `route -> service -> model/database`. Routes only describe URLs and who may call them.

## 5. Installation

You need Python 3.11 or newer and a MongoDB database (section 7). In PowerShell:

```powershell
cd "D:\iot\civic issuse\civic-issue-backend"
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell refuses to run the activate script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

## 6. Environment setup

Copy `.env.example` to `.env` and fill it in. **Never commit `.env`** (it is in `.gitignore`).

| Variable | Default | Meaning |
|---|---|---|
| `APP_ENV` | `development` | `development` or `production` (`test` is set by the tests) |
| `MONGO_URI` | local MongoDB | Your MongoDB connection string |
| `MONGO_DB_NAME` | `civic_issue_db` | Database name |
| `CLIENT_URL` | `http://localhost:3000` | The only website allowed to call the API from a browser (CORS) |
| `JWT_SECRET` | none, **required** | At least 32 random characters. Generate one: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_EXPIRES_MINUTES` | `60` | How long a login lasts |
| `DUPLICATE_RADIUS_METERS` | `100` | Duplicate-detection radius |
| `OVERDUE_DAYS` | `3` | Days before an open complaint is overdue |
| `OVERDUE_CHECK_MINUTES` | `60` | How often the overdue job runs |
| `SCHEDULER_ENABLED` | `true` | `false` switches the background job off |
| `POINTS_COMPLAINT_CREATED` / `_UPVOTED` / `_RESOLVED` | `10` / `2` / `20` | Points per event (0 switches an event off) |
| `RATE_LIMIT_ENABLED` | `true` | Rate limiting on login and register |
| `RATE_LIMIT_LOGIN_MAX` / `RATE_LIMIT_REGISTER_MAX` | `10` / `5` | Attempts per client per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `900` | The window (15 minutes) |
| `TRUST_PROXY_HEADERS` | `false` | `true` only behind your own reverse proxy (then `X-Forwarded-For` identifies the client) |
| `MAX_JSON_BODY_KB` | `256` | Largest accepted non-upload request |
| `UPLOAD_DIR`, `MAX_UPLOAD_MB` | `uploads`, `5` | Photo folder and size limit |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | empty, `587` | E-mail. Leave `SMTP_HOST` empty to switch e-mail off. Gmail needs an "app password" |
| `SEED_ADMIN_NAME`, `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD`, `SEED_WORKER_PASSWORD` | | Used only by `python -m app.seed` |

An empty line such as `SMTP_PORT=` is treated as "not set" and the default is used.

## 7. MongoDB setup (Atlas, free)

1. Create a free account and a free **M0** cluster at <https://www.mongodb.com/atlas>.
2. **Database Access**: add a database user with a password (use only letters and digits to avoid URL-encoding problems).
3. **Network Access**: add your current IP address (for learning you may use `0.0.0.0/0`, but never in a real deployment).
4. **Connect -> Drivers**: copy the `mongodb+srv://...` string into `MONGO_URI`, replacing `<password>`.
5. Start the app. The indexes (unique e-mail, 2dsphere location, unique upvote, ...) are created automatically.

Troubleshooting: `The DNS query name does not exist` means the cluster host in the string is wrong, so copy it again from Atlas.
A timeout means your IP is not in Network Access.

## 8. Seed command

```powershell
python -m app.seed
```

Creates the departments, the 15 categories with their departments, the admin user, sample workers and the four badges.
It can be run again and again: it never creates duplicates and never overwrites changes an admin made later.

## 9. Development command

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

- Swagger (try everything in the browser): <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/api/v1/health>
- The terminal shows `Scheduler started: overdue check every 60 minute(s)`.

## 10. API endpoint list

Generated from the running application by `python scripts/generate_api_docs.py`. More detail in [docs/API.md](docs/API.md).

<!-- API-START -->

_49 endpoints. Every URL starts with `http://127.0.0.1:8000` while you develop._

### Health

Is the server (and database) running?

| Method | URL | Who can call it | What it does |
|---|---|---|---|
| GET | `/api/v1/health` | Public | Get Health. |

### Auth

Register, log in, who am I.

| Method | URL | Who can call it | What it does |
|---|---|---|---|
| POST | `/api/v1/auth/login` | Public | Login. |
| GET | `/api/v1/auth/me` | Any logged-in user | Get Me. |
| POST | `/api/v1/auth/register` | Public | Register. |

### Profile

Change my own name, phone and password.

| Method | URL | Who can call it | What it does |
|---|---|---|---|
| PATCH | `/api/v1/users/me` | Any logged-in user | Change my name or phone number. |
| POST | `/api/v1/users/me/change-password` | Any logged-in user | Change my password. |

### Departments

Departments (database-driven). Admins can create, edit and deactivate.

| Method | URL | Who can call it | What it does |
|---|---|---|---|
| GET | `/api/v1/departments` | Any logged-in user | List Departments. |
| POST | `/api/v1/departments` | ADMIN | Create a department (admin). |
| GET | `/api/v1/departments/{department_id}` | Any logged-in user | One department. |
| PATCH | `/api/v1/departments/{department_id}` | ADMIN | Edit a department (admin). |
| DELETE | `/api/v1/departments/{department_id}` | ADMIN | Deactivate a department (admin). |

### Categories

The 15 issue categories and the department each one belongs to.

| Method | URL | Who can call it | What it does |
|---|---|---|---|
| GET | `/api/v1/categories` | Any logged-in user | List Categories. |
| POST | `/api/v1/categories` | ADMIN | Create a category (admin). |
| GET | `/api/v1/categories/{category_id}` | Any logged-in user | Get Category. |
| PATCH | `/api/v1/categories/{category_id}` | ADMIN | Edit a category (admin). |
| DELETE | `/api/v1/categories/{category_id}` | ADMIN | Deactivate a category (admin). |

### Complaints

Report, view, upvote. Admins can edit, delete and change status.

| Method | URL | Who can call it | What it does |
|---|---|---|---|
| GET | `/api/v1/complaints` | ADMIN, CITIZEN | List Complaints. Filters: `status`, `page`, `limit`. |
| POST | `/api/v1/complaints` | CITIZEN | Create Complaint. |
| GET | `/api/v1/complaints/nearby` | CITIZEN | Nearby Complaints. Filters: `latitude`, `longitude`, `radius`, `categoryId`. |
| GET | `/api/v1/complaints/{complaint_id}` | ADMIN, CITIZEN | Get Complaint. |
| PATCH | `/api/v1/complaints/{complaint_id}` | ADMIN | Edit a complaint (admin). |
| DELETE | `/api/v1/complaints/{complaint_id}` | ADMIN | Delete a complaint (admin). |
| PATCH | `/api/v1/complaints/{complaint_id}/status` | ADMIN | Change the status of any complaint (admin). |
| POST | `/api/v1/complaints/{complaint_id}/upvote` | CITIZEN | Upvote Complaint. |
| DELETE | `/api/v1/complaints/{complaint_id}/upvote` | CITIZEN | Remove Upvote. |

### Worker

Worker portal: complaints of my own department and status changes.

| Method | URL | Who can call it | What it does |
|---|---|---|---|
| GET | `/api/v1/worker/complaints` | WORKER | List My Department Complaints. Filters: `status`, `assignedToMe`, `overdue`, `page`, `limit`. |
| GET | `/api/v1/worker/complaints/{complaint_id}` | WORKER | Get Complaint. |
| PATCH | `/api/v1/worker/complaints/{complaint_id}/status` | WORKER | Update Status. |

### Notifications

In-app notifications for every user.

| Method | URL | Who can call it | What it does |
|---|---|---|---|
| GET | `/api/v1/notifications` | Any logged-in user | List My Notifications. Filters: `unreadOnly`, `page`, `limit`. |
| PATCH | `/api/v1/notifications/read-all` | Any logged-in user | Mark All Read. |
| PATCH | `/api/v1/notifications/{notification_id}/read` | Any logged-in user | Mark Read. |

### Points and Badges

My points and badges, all badges, leaderboard.

| Method | URL | Who can call it | What it does |
|---|---|---|---|
| GET | `/api/v1/gamification/badges` | Any logged-in user | All Badges. |
| GET | `/api/v1/gamification/leaderboard` | Any logged-in user | Leaderboard. Filters: `limit`. |
| GET | `/api/v1/gamification/me` | Any logged-in user | My Points And Badges. |

### Admin

Dashboard, statistics, all complaints, map, overdue, audit logs.

| Method | URL | Who can call it | What it does |
|---|---|---|---|
| GET | `/api/v1/admin/audit-logs` | ADMIN | Who did what, newest first. Filters: `action`, `entity`, `userId`, `page`, `limit`. |
| GET | `/api/v1/admin/categories` | ADMIN | All categories, including inactive ones. |
| GET | `/api/v1/admin/complaints` | ADMIN | All complaints, with filters. Filters: `status`, `categoryId`, `departmentId`, `overdue`, `number`, `page`, `limit`. |
| GET | `/api/v1/admin/complaints/map` | ADMIN | All complaints as map pins. Filters: `status`, `categoryId`, `departmentId`, `overdue`, `limit`. |
| GET | `/api/v1/admin/complaints/{complaint_id}` | ADMIN | One complaint, full detail. |
| GET | `/api/v1/admin/dashboard` | ADMIN | Dashboard: statistics plus the oldest overdue complaints. |
| GET | `/api/v1/admin/departments` | ADMIN | All departments, including inactive ones. |
| GET | `/api/v1/admin/overdue` | ADMIN | Open complaints past the overdue limit, oldest first. Filters: `page`, `limit`. |
| POST | `/api/v1/admin/overdue/check` | ADMIN | Run the overdue check now. |
| GET | `/api/v1/admin/statistics` | ADMIN | Totals, and complaints by status, category and department. |

### Admin - Workers

Create and manage worker accounts.

| Method | URL | Who can call it | What it does |
|---|---|---|---|
| GET | `/api/v1/admin/workers` | ADMIN | List workers. Filters: `departmentId`, `isActive`, `page`, `limit`. |
| POST | `/api/v1/admin/workers` | ADMIN | Create a worker account. |
| GET | `/api/v1/admin/workers/{worker_id}` | ADMIN | One worker. |
| PATCH | `/api/v1/admin/workers/{worker_id}` | ADMIN | Edit a worker, move to another department, (de)activate, reset password. |
| DELETE | `/api/v1/admin/workers/{worker_id}` | ADMIN | Deactivate a worker (the account is kept). |

<!-- API-END -->

## 11. Authentication flow

1. `POST /api/v1/auth/register` creates a **citizen**. The role can never be chosen by the caller. Workers are created by an admin, and the first admin comes from the seed script.
2. `POST /api/v1/auth/login` checks the bcrypt hash and returns `accessToken` (a JWT that holds only the user id and an expiry time).
3. The client sends `Authorization: Bearer <accessToken>` with every later request.
4. For every request the server verifies the signature and expiry, loads the user from the database and refuses deactivated users. The **role and department always come from the database**, never from the token or the request body.
5. Role checks (`require_roles(...)`) run before any other work. Wrong role: 403. No or bad token: 401.

## 12. Role permissions

| Action | Citizen | Worker | Admin |
|---|:-:|:-:|:-:|
| Register, login, see own account, change own name / phone / password | yes | yes | yes |
| Report complaints, see own complaints, nearby complaints, upvote | yes | | |
| Notifications, points and badges, leaderboard | yes | yes | yes |
| See complaints of **own department**, start and resolve them | | yes | |
| See **all** complaints, edit, delete, change any status | | | yes |
| Dashboard, statistics, map, overdue list, audit logs | | | yes |
| Create / edit / deactivate departments, categories and workers | | | yes |

Citizens only ever see their own complaints, plus the shared view of other complaints (the reporter's identity is hidden when the complaint is anonymous).

## 13. Duplicate detection

When a citizen reports a complaint the server:

1. validates the category and takes the **department from the category** in the database;
2. validates the photo;
3. searches for an **open** complaint (SUBMITTED or IN_PROGRESS) of the **same category** within `DUPLICATE_RADIUS_METERS` using MongoDB's `$geoNear`;
4. if one exists, creates **nothing** and answers with that complaint, `canUpvote` and an `upvoteUrl`;
5. otherwise saves the photo, takes the next complaint number and creates the complaint.

Resolved complaints are not duplicates, so the same problem can be reported again after it was fixed once.

## 14. GeoJSON

A location is stored as a GeoJSON **Point**. The order is **longitude first, then latitude**, the reverse of how people say it:

```json
{ "type": "Point", "coordinates": [73.1920, 19.1867] }
```

The API accepts separate `latitude` and `longitude` fields (checked: -90..90 and -180..180) and builds the GeoJSON itself.
The `location` field has a **2dsphere** index, which MongoDB needs for distance queries such as the duplicate check and the nearby search.

## 15. Testing instructions

```powershell
python -m pytest -q          # everything
python -m pytest -v          # with the name of every test
python -m pytest tests/test_security.py -q
```

- The tests use the **real MongoDB** from your `.env` but a separate database called `civic_issue_test_db`, which is emptied between tests and dropped at the end. Your real data is never touched.
- With Atlas the full run takes a few minutes because every query goes over the internet. Wait for the last line (`... passed`).
- `tests/test_route_matrix.py` calls every endpoint as a visitor, citizen, worker and admin and checks that exactly the right roles get in. It also makes sure the documentation is true.
- Rate limiting and the background scheduler are switched off while `APP_ENV=test`; the tests that need them switch them on explicitly.

## Security notes

- Passwords: bcrypt, 8-72 characters, at least one letter and one number. Hashes are never returned or logged.
- JWT secret is checked at start-up (32+ characters), the app refuses to start otherwise.
- Request bodies are validated by Pydantic with unknown fields rejected (`extra="forbid"`), so `role`, `points`, `departmentId` and other protected fields cannot be injected. MongoDB operators such as `{"$ne": null}` are rejected because every field has a strict type.
- Ids in URLs are validated before they reach the database. The same 404 is returned for "does not exist" and "belongs to someone else".
- Login and register are rate limited per client address (429 with a `Retry-After` header).
- Headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cache-Control: no-store` and a strict `Content-Security-Policy` on API responses; HSTS over HTTPS; uploaded photos are served with a sandbox policy.
- Unexpected errors return a generic message; details go only to the server log.
- Every important change is written to the audit log, without passwords, tokens or e-mail addresses.

## Known limitations (honest list)

- The rate limiter keeps its counters in memory, so it works per server process. With several processes use Redis.
- A login token cannot be cancelled before it expires, but a **deactivated** user is refused immediately because the user is loaded on every request. Changing a password does not cancel tokens that were already issued.
- The request-size check uses the `Content-Length` header; the photo size is checked again while reading the file.
- Photos are stored on the local disk. For a real deployment switch `get_storage()` to Cloudinary or S3.
- E-mail needs an SMTP account. Without it only in-app notifications are created.
- The leaderboard shows citizens' names (not e-mail or id).

## Build history

The backend was built in 11 phases, each committed and tagged in Git: 1 setup, 2 authentication, 3 departments and categories,
4 complaints and GeoJSON, 5 duplicates and upvotes, 6 worker portal, 7 notifications and e-mail, 8 overdue job,
9 points and badges, 10 admin dashboard and management, 11 security hardening, tests and documentation.
