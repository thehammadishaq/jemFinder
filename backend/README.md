# Company Profile API - FastAPI Backend (MongoDB)

REST API backend for managing company profile data using FastAPI with MVC architecture and MongoDB.

## Project Structure

```
backend/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── env.example            # Environment variables template
├── init_db.py             # Database initialization script
├── config/                 # Configuration
│   ├── __init__.py
│   └── settings.py        # Application settings
├── database/              # Database configuration
│   ├── __init__.py
│   └── database.py        # MongoDB/Motor setup
├── models/                 # Database models (MVC - Model)
│   ├── __init__.py
│   └── company_profile.py # CompanyProfile Beanie model
├── schemas/                # Pydantic schemas
│   ├── __init__.py
│   └── company_profile.py # Request/Response schemas
├── services/               # Business logic layer
│   ├── __init__.py
│   └── company_profile_service.py
├── controllers/            # Controllers (MVC - Controller)
│   ├── __init__.py
│   └── company_profile_controller.py
└── routes/                 # API routes (MVC - View)
    ├── __init__.py
    └── company_profile_routes.py
```

## MVC Architecture

- **Models** (`models/`): Beanie ODM MongoDB document models
- **Views** (`routes/`): FastAPI route handlers (API endpoints)
- **Controllers** (`controllers/`): Business logic and orchestration
- **Services** (`services/`): Data access and business operations

## Prerequisites

- Python 3.8+
- MongoDB (local or cloud)
  - Local: Install MongoDB Community Edition
  - Cloud: MongoDB Atlas account (free tier available)

## Setup

### 1. Install MongoDB

**Local MongoDB:**
- Download from: https://www.mongodb.com/try/download/community
- Or use Docker: `docker run -d -p 27017:27017 --name mongodb mongo:latest`

**MongoDB Atlas (Cloud):**
- Sign up at: https://www.mongodb.com/cloud/atlas
- Create a free cluster
- Get connection string

### 2. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Install Playwright Browsers

After installing Python dependencies, you need to install Playwright browser binaries:

```bash
playwright install
```

This will download Chromium, Firefox, and WebKit browsers required for browser automation (used by Gemini AI scraping).

**Note:** This step is required! Without it, you'll get an error like:
```
Executable doesn't exist at ...\ms-playwright\chromium-1140\chrome-win\chrome.exe
```

### 4. Configure Environment

```bash
# Copy example env file
cp env.example .env

# Edit .env file with your MongoDB settings
```

**For Local MongoDB:**
```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=company_profiles_db
```

**For MongoDB Atlas:**
```env
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/dbname?retryWrites=true&w=majority
DATABASE_NAME=company_profiles_db
```

### 5. Initialize Database (Optional)

```bash
python init_db.py
```

The database will be automatically initialized when you start the server.

### 6. Run the Server

```bash
# Development mode
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Company Profiles

- `POST /api/v1/profiles/` - Create a new profile
- `GET /api/v1/profiles/` - Get all profiles (with pagination)
- `GET /api/v1/profiles/{id}` - Get profile by ID (MongoDB ObjectId)
- `GET /api/v1/profiles/ticker/{ticker}` - Get profile by ticker
- `PUT /api/v1/profiles/{id}` - Update profile
- `DELETE /api/v1/profiles/{id}` - Delete profile
- `POST /api/v1/profiles/upload` - Upload JSON file
- `GET /api/v1/profiles/search/{query}` - Search profiles

### Gemini AI Scraping

- `POST /api/v1/gemini/fetch-profile` - Fetch company profile from Gemini AI (exact same as geminiCompanyProfile.py)
- `GET /api/v1/gemini/fetch-profile/{ticker}` - Fetch company profile from Gemini AI (GET method)

**Note:** These endpoints use Playwright to scrape Gemini UI, exactly like `geminiCompanyProfile.py`. Browser window will open.

### Health Check

- `GET /` - Root endpoint
- `GET /health` - Health check

## How to Create Profiles for New Tickers

There are **3 ways** to create profiles for new tickers:

### Method 1: Through the Web UI (Recommended)

This is the easiest way to create profiles:

1. **Open the application** in your browser
2. **Click on "Company Profile" tab** (not Browse)
3. **Enter a ticker symbol** (e.g., `AAPL`, `TSLA`, `MSFT`, `NVDA`)
4. **Click "Load Profile"** - If profile doesn't exist, you'll see an empty profile
5. **Fetch data from any source:**
   - Click **"Fetch"** button under **Gemini AI** (takes 30-60 seconds, opens browser)
   - Click **"Fetch"** button under **Yahoo Finance** (fast, 3-8 seconds)
   - Click **"Fetch"** button under **Polygon.io** (fast, 2-5 seconds)
   - Click **"Fetch"** button under **Finnhub** (fast, 3-8 seconds)
6. **Profile is automatically saved** to the database when you fetch data

**Note:** You can fetch from multiple sources and they'll all be saved under the same ticker. Use the tabs (Profile, Gemini AI, Yahoo Finance, etc.) to switch between different data sources.

### Method 2: Using API Endpoints

#### Option A: Fetch from Gemini AI (via API)

```bash
curl -X POST "http://localhost:8000/api/v1/gemini/fetch-profile" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "save_to_db": true
  }'
```

#### Option B: Fetch from Yahoo Finance (via API)

```bash
curl -X POST "http://localhost:8000/api/v1/yfinance/fetch-data" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "save_to_db": true
  }'
```

#### Option C: Fetch from Polygon.io (via API)

```bash
curl -X POST "http://localhost:8000/api/v1/polygon/fetch-profile" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "save_to_db": true
  }'
```

#### Option D: Fetch from Finnhub (via API)

```bash
curl -X POST "http://localhost:8000/api/v1/finnhub/fetch-data" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "save_to_db": true
  }'
```

#### Option E: Create Profile Manually (via API)

```bash
curl -X POST "http://localhost:8000/api/v1/profiles/" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "data": {
      "What": {
        "CompanyName": "Apple Inc.",
        "Ticker": "AAPL"
      },
      "When": {
        "Founded": "1976"
      }
    }
  }'
```

### Method 3: Upload JSON File

If you have a JSON file with company profile data:

```bash
curl -X POST "http://localhost:8000/api/v1/profiles/upload" \
  -F "file=@gemini_company_profile_AAPL.json"
```

The JSON file should have the ticker in the filename or in the data structure.

## Example Usage

### Upload JSON File

```bash
curl -X POST "http://localhost:8000/api/v1/profiles/upload" \
  -F "file=@gemini_company_profile_AAPL.json"
```

### Create Profile

```bash
curl -X POST "http://localhost:8000/api/v1/profiles/" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "data": {
      "What": {...},
      "When": {...}
    }
  }'
```

### Get Profile by Ticker

```bash
curl "http://localhost:8000/api/v1/profiles/ticker/AAPL"
```

### Fetch Profile from Gemini AI

```bash
# POST request
curl -X POST "http://localhost:8000/api/v1/gemini/fetch-profile" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "save_to_db": true
  }'

# GET request
curl "http://localhost:8000/api/v1/gemini/fetch-profile/AAPL?save_to_db=true"
```

**Note:** Gemini scraping opens a browser window. Make sure you're logged into Gemini in the browser session.

### Get Profile by ID

```bash
curl "http://localhost:8000/api/v1/profiles/507f1f77bcf86cd799439011"
```

## Database

The application uses **MongoDB** with:
- **Motor**: Async MongoDB driver
- **Beanie**: ODM (Object Document Mapper) for MongoDB
- Automatic indexing on `ticker` field
- Automatic ID generation (MongoDB ObjectId)

### MongoDB Collections

- `company_profiles`: Stores company profile documents

### Document Structure

```json
{
  "_id": "ObjectId",
  "ticker": "AAPL",
  "data": {
    "What": {...},
    "When": {...},
    "Where": {...},
    "How": {...},
    "Who": {...}
  },
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

## Features

- ✅ RESTful API design
- ✅ MVC architecture
- ✅ MongoDB with Beanie ODM
- ✅ Async/await support
- ✅ Pydantic validation
- ✅ CORS support
- ✅ Automatic API documentation (Swagger/ReDoc)
- ✅ File upload support
- ✅ Search functionality
- ✅ Pagination
- ✅ Automatic indexing

## Troubleshooting

### MongoDB Connection Issues

1. **Check if MongoDB is running:**
   ```bash
   # Local MongoDB
   mongosh
   
   # Or check process
   ps aux | grep mongod
   ```

2. **Verify connection string:**
   - Local: `mongodb://localhost:27017`
   - Atlas: Check your cluster connection string

3. **Check firewall/network:**
   - Ensure MongoDB port (27017) is accessible
   - For Atlas, whitelist your IP address

### Common Errors

- **"Connection refused"**: MongoDB not running
- **"Authentication failed"**: Wrong credentials in connection string
- **"Network timeout"**: Check network/firewall settings
