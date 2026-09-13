# Central Fire Safety Institute (CFSI) - Backend API

Enterprise FastAPI backend for CFSI portal with MongoDB, Bcrypt password hashing, and JWT Bearer authentication.

---

## 🛠️ Tech Stack
- **Framework**: FastAPI (Python 3.13+)
- **Database**: MongoDB (Motor async driver) with mongomock-motor fallback
- **Authentication**: JWT (`HS256`, 24h expiration)
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
   CFSI_JWT_SECRET=cfsi_jwt_secure_secret_key_2026_vadodara_safety
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ```
4. **Run Server**:
   ```powershell
   python run.py
   ```
   - API: `http://localhost:8000`
   - Interactive Swagger Docs: `http://localhost:8000/docs`
   - Healthcheck: `http://localhost:8000/api/health`

---

## 🧪 Run Tests
```powershell
.\venv\Scripts\python tests\test_backend.py
.\venv\Scripts\python tests\test_api_endpoints.py
```

---

## 🔑 Administrator Account (Bcrypt Hashed in DB)

- **ID / Email**: `admin@cfsi.com`
- **Password**: `Password@1`
- **Role**: `admin` (Full administrative privileges)
