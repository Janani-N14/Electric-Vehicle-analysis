# EV Fleet Management & Predictive Analytics Platform

A modern, high-performance web application designed for smart Electric Vehicle (EV) data monitoring, driver behavior assessment, vehicle telemetry visualization, and predictive maintenance analysis. The application features a premium dark-themed, glassmorphic dashboard interface for both fleet administrators and drivers.

---

## 🚀 Key Features

- **Double-Sided Dashboards**:
  - **Admin Dashboard**: View global fleet status, aggregate telemetry KPIs, monthly trends, vehicle performance comparisons, driver safety rankings, and predictive maintenance correlations. Includes dynamic multi-variable filtering (date range, status, model, driver).
  - **Driver Portal**: Personal trip statistics, safety scorecards, recent driving alerts, and vehicle efficiency tracking.
- **Advanced Predictive & Behavior Analytics**:
  - **Driver Safety Score**: Computes safety scores dynamically based on harsh braking, harsh acceleration, and overspeeding violations normalized per 100 km.
  - **Violation-Efficiency Correlation**: Employs Pearson Correlation Coefficients to prove the direct negative impact of harsh driving habits on battery efficiency (km/kWh).
  - **Predictive Maintenance Heatmap**: Analyzes relationships between maintenance costs, battery health, breakdowns, vehicle age, and distance travelled.
- **Robust Security**: Fully secured using JWT (JSON Web Tokens) with cookie-based authorization and role-based permissions (Admin vs. Driver).
- **Automated Seeding**: Automatically parses and seeds the database from Excel sheets (`EV_Admin.xlsx` and `EV_Fleet_Drivers.xlsx`) upon initial startup.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.13, [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy ORM](https://www.sqlalchemy.org/), [Uvicorn](https://www.uvicorn.org/)
- **Database**: SQLite (local dev database `ev_fleet.db`)
- **Data processing / Math**: [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/), [OpenPyXL](https://openpyxl.readthedocs.io/)
- **Frontend**: Responsive HTML5, Custom Vanilla CSS (featuring glassmorphism and modern dark-mode aesthetics), Jinja2 Templates, JavaScript, and Highcharts/Chart.js for interactive visualizations.
- **Testing**: [Pytest](https://docs.pytest.org/) & FastAPI TestClient

---

## 📁 Directory Structure

```text
Electric-Vehicle-analysis/
├── data/                         # Initial Excel databases used for seeding
│   ├── EV_Admin.xlsx
│   └── EV_Fleet_Drivers.xlsx
├── ev_fleet_management/          # Core python package containing all source code
│   ├── config/                   # App configurations and environment settings
│   │   └── settings.py
│   ├── exception/                # Custom exception classes
│   │   └── custom_exception.py
│   ├── logger/                   # Standardized application logging setup
│   │   └── custom_logger.py
│   ├── model/                    # SQLAlchemy database tables & Pydantic schemas
│   │   └── models.py
│   ├── src/                      # API Routers implementing business logic
│   │   ├── alerts.py             # Alert logging and dismissal
│   │   ├── analytics.py          # Dashboard analytics & correlation computation
│   │   ├── auth.py               # User registration, login, and token verification
│   │   ├── data_ingestion.py     # Parsing Excel files and database seeding
│   │   ├── drivers.py            # Driver metadata endpoints
│   │   ├── telemetry.py          # EV telemetry logs ingestion & querying
│   │   └── vehicles.py           # EV fleet management actions
│   └── utils/                    # Shared database connections and JWT helper functions
│       ├── db.py
│       └── jwt_helper.py
├── static/                       # Client-side static assets (JS scripts, images)
├── templates/                    # Jinja2 HTML views
│   ├── index.html                # Registration and Login Portal
│   ├── admin-dashboard.html      # Fleet Operations Hub
│   └── driver-dashboard.html     # Driver Performance Portal
├── tests/                        # Comprehensive test suite (Unit & Integration)
│   ├── conftest.py               # Database fixtures and mock client setups
│   ├── integration/
│   │   └── test_auth.py
│   └── unit/
│       └── test_analytics.py
├── ev_fleet.db                   # Generated SQLite database file
├── main.py                       # Main application entry point
└── pytest.ini                    # Test environment configurations
```

---

## ⚙️ Installation & Setup

### Prerequisites
Make sure you have **Python 3.10+** installed on your machine.

### 1. Clone the repository
```bash
git clone https://github.com/Janani-N14/Electric-Vehicle-analysis.git
cd Electric-Vehicle-analysis
```

### 2. Install dependencies
Install all required libraries (it is highly recommended to run this inside a virtual environment):
```bash
pip install fastapi uvicorn sqlalchemy pandas numpy openpyxl jinja2 python-multipart pyjwt cryptography httpx pytest
```

### 3. Run the application
Run the FastAPI development server:
```bash
python main.py
```
By default, the server will start at: [http://127.0.0.1:8000](http://127.0.0.1:8000)

*Note: On startup, the server automatically reads files from the `/data` directory to seed database records in `ev_fleet.db` if they are not already initialized.*

---

## 🧪 Running Tests

You can run unit and integration tests using pytest:

```bash
python -m pytest
```

The test runner utilizes an isolated in-memory SQLite database (`sqlite:///:memory:`) to verify routes, registration, authentication flows, telemetry processing, and mathematical analytics calculations.
