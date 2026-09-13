# Central Fire Safety Institute (CFSI) - Backend API

Enterprise FastAPI backend for CFSI portal with MongoDB, Bcrypt password hashing, and JWT Bearer authentication.

---

## 🛠️ Tech Stack
- **Framework**: FastAPI (Python 3.13+)
- **Database**: MongoDB (Motor async driver) with mongomock-motor fallback
- **Authentication**: OAuth2 password flow with JWT (`HS256`, configurable expiration)
- **Password Security**: Bcrypt with unique salts
- **Server**: Uvicorn ASGI

---

## 🚀 Quick Start

1. **Activate Virtual Environment**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
2. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
3. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and set your MongoDB connection:
   ```env
   MONGODB_URL=mongodb://localhost:27017
   MONGODB_DB_NAME=cfsi_db
   JWT_SECRET_KEY=<generate-a-random-secret-of-at-least-32-characters>
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   BOOTSTRAP_ADMIN_USERNAME=admin@cfsi.com
   BOOTSTRAP_ADMIN_PASSWORD=<choose-a-strong-password>
   ```
4. **Run Server**:
   ```powershell
   python run.py
   ```
   - API: `http://localhost:8000`
   - Interactive Swagger Docs: `http://localhost:8000/docs`
   - Healthcheck: `http://localhost:8000/api/health`

---

## Authentication and role access

The panel uses OAuth2 password-form login at `POST /api/auth/token` and signed,
expiring JWT bearer tokens. The previous JSON `POST /api/auth/login` endpoint
remains compatible. This is institute username/password authentication; it does
not configure Google or Microsoft sign-in.

Before starting a fresh database, copy `.env.example` to `.env`, generate a random
`JWT_SECRET_KEY` (at least 32 characters), and set `BOOTSTRAP_ADMIN_PASSWORD` to a
strong password of 8–72 UTF-8 bytes. `BOOTSTRAP_ADMIN_USERNAME` defaults to
`admin@cfsi.com`. Startup creates the first administrator only if no admin exists;
it never resets an existing account. Without an explicit JWT secret, development
uses a random process-local secret and sessions expire on restart. Configure a
persistent MongoDB server: the existing offline mongomock fallback loses changes
on restart. Configure `CORS_ORIGINS` as a JSON array for your deployed frontend.

Open `/login`, choose Admin, and use the bootstrap credentials. Open **Manage
users** (`/users`) to create, list, edit, deactivate, or delete accounts. A Student
account requires an existing student ID. Usernames are immutable.
Passwords are hashed and never returned. Account updates invalidate existing
sessions; logout invalidates all sessions for that user. Admins cannot delete,
deactivate, or demote themselves. No client-side demo login is accepted.

| Role | Panel | Access |
| --- | --- | --- |
| Admin | `/dashboard`, `/users` | Institute dashboard and user CRUD |
| Teacher | `/teacher/dashboard` | Read and maintain attendance, student directory |
| Student | `/student/dashboard` | Own attendance and cadet profile only |

Public website pages remain accessible without login. Protected routes redirect
to `/login`; authenticated visitors to `/login` return to their role's panel.
Server dependencies enforce permissions independently of frontend guards.

User API: `GET/POST /api/users`, `GET/PATCH/DELETE /api/users/{id}` (Admin only).
Session API: `GET /api/auth/me`, `POST /api/auth/logout`.

Run the isolated security integration suite (no live database changes):

```sh
venv/bin/python -m unittest tests/test_auth_roles.py
```

OAuth2 implementation reference: [FastAPI OAuth2 with JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/).
