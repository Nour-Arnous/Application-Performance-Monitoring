```markdown
# Application Performance Monitoring (APM) Dashboard

APM Dashboard is a complete, real-time monitoring system for web applications.
 It collects performance metrics (response time, request count, error count) from external applications via a lightweight Agent,
 visualizes them in an interactive dashboard, and uses AI (Prophet) to forecast future response times.

---

## Project File Hierarchy

```text
APM/                                    # Root project folder
│
├── src/                                 # All source code
│   ├── manage.py                        # Django management script
│   ├── agent_app.py                     # Unified Agent (GUI + CLI)
│   ├── requirements.txt                 # All Python dependencies
│   │
│   ├── project/                         # Django project settings
│   │   ├── __init__.py
│   │   ├── settings.py                  # Main settings (JWT, Channels, Celery, Redis)
│   │   ├── urls.py                      # Root URL configuration
│   │   ├── asgi.py                      # ASGI config for WebSocket (Channels)
│   │   ├── wsgi.py                      # WSGI config for production
│   │   └── celery.py                    # Celery app definition (tasks & beat schedule)
│   │
│   ├── account/                         # Authentication app (JWT + Session)
│   │   ├── __init__.py
│   │   ├── admin.py                     # Admin panel registration
│   │   ├── apps.py
│   │   ├── models.py                    # UserProfile model with signals for auto‑creation
│   │   ├── serializers.py               # Register, Login, Profile serializers
│   │   ├── urls.py                      # Auth endpoints (/api/auth/...)
│   │   ├── views.py                     # JWT & Session views
│   │   └── channels_auth.py             # WebSocket JWT authentication middleware
│   │
│   ├── monitor/                         # Main monitoring app
│   │   ├── __init__.py
│   │   ├── admin.py                     # Admin config for Application, Metric, Alert
│   │   ├── apps.py
│   │   ├── models.py                    # Application (with api_key), Metric, Alert models
│   │   ├── views.py                     # HTML views + API ViewSets
│   │   ├── serializers.py               # Application, Metric, Alert serializers
│   │   ├── permissions.py               # Custom permissions
│   │   ├── consumers.py                 # WebSocket consumer (real-time updates)
│   │   ├── routing.py                   # WebSocket URL routing
│   │   ├── tasks.py                     # Celery tasks (averages, thresholds, cleanup, forecast)
│   │   ├── forecast.py                  # Prophet forecasting logic
│   │   ├── urls.py                      # App URLs (HTML + API)
│   │   └── tests.py                     # Unit tests
│   │
│   ├── templates/                       # Global HTML templates
│   │   ├── base.html                    # Base template (navbar, footer)
│   │   ├── authentication/              # Auth pages (login, register, profile)
│   │   └── monitor/                     # Monitoring pages (home, about, dashboard, manage_apps, alerts_list)
│   │
│   ├── static/                          # Static files (served in development)
│   │   ├── downloads/APM_Agent.exe      # Pre‑built Agent executable
│   │   ├── images/                      # Guide images
│   │   ├── css/style.css                # Custom CSS
│   │   └── js/dashboard.js              # Custom JS
│   │
│   └── staticfiles/                     # Collected static files (for production)
│
├── README.md                            # Complete project guide
├── .gitignore                           # Files/folders excluded from Git
└── ScreenShots/                         # Postman test screenshots
    ├── register_test_postman.png
    ├── login_test_postman.png
    ├── profile_test_postman.png
    ├── modify_profile_test_postman.png
    ├── add_application_test_postman.png
    ├── add_metrics_test_postman.png
    └── logout_test_postman.png

```

---

## Step‑by‑Step Installation & Setup

### Prerequisites

* Python 3.10 or higher installed on your system.
* Redis installed and running (for Celery background tasks).
* Git (to clone the repository).

### 1️⃣ Clone the Repository

```bash
git clone [https://github.com/Nour-Arnous/Application-Performance-Monitoring.git](https://github.com/Nour-Arnous/Application-Performance-Monitoring.git)
cd Application-Performance-Monitoring

```

### 2️⃣ Create and Activate a Virtual Environment

* **Windows:**

```bash
python -m venv venv
venv\Scripts\activate

```

* **Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate

```

### 3️⃣ Install Dependencies

```bash
cd src
pip install -r requirements.txt

```

> *Note: If you are on Windows and encounter issues with eventlet or redis, make sure you have the correct versions specified in requirements.txt.*

### 4️⃣ Set Up the Database

```bash
python manage.py migrate
python manage.py createsuperuser    # (Optional) – for admin access

```

### 5️⃣ Install & Start Redis

* **Windows:** Download Redis for Windows from [GitHub Releases](https://github.com/tporadowski/redis/releases), install and run it as a service.
* **Linux / macOS:**

```bash
sudo apt install redis-server    # Ubuntu/Debian
# or
brew install redis               # macOS
redis-server

```

* **Verify Redis is running:**

```bash
redis-cli ping
# should return PONG

```

### 6️⃣ Start the Project (Three Terminals Required)

Open three separate terminal windows in the `src/` folder:

* **Terminal 1 – Main Web Server (Daphne/Django):**

```bash
python manage.py runserver

```

* **Terminal 2 – Celery Worker (Background Tasks):**

```bash
celery -A project worker -l info -P eventlet

```

*(Note: On Linux/macOS, use `-P gevent` or omit the `-P` flag).*

* **Terminal 3 – Celery Beat (Task Scheduler):**

```bash
celery -A project beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

```

---

## Accessing the Application

| Page | URL |
| --- | --- |
| **Home (Landing)** | `http://127.0.0.1:8000/` |
| **Dashboard** | `http://127.0.0.1:8000/dashboard/` |
| **About / Guide** | `http://127.0.0.1:8000/about/` |
| **My Apps (API Keys)** | `http://127.0.0.1:8000/apps/` |
| **Admin Panel** | `http://127.0.0.1:8000/admin/` |
| **API Root** | `http://127.0.0.1:8000/api/` |

---

## API Endpoints (JWT Authentication)

| Method | Endpoint | Description |
| --- | --- | --- |
| **POST** | `/api/auth/register/` | Register a new user |
| **POST** | `/api/auth/login/` | Login (returns access & refresh tokens) |
| **GET** | `/api/auth/profile/` | Get current user profile |
| **POST** | `/api/auth/logout/` | Logout (blacklist refresh token) |
| **GET** | `/api/applications/` | List user's applications (admin sees all) |
| **POST** | `/api/applications/` | Create a new application |
| **GET** | `/api/metrics/` | List metrics (with time filter `?hours=24`) |
| **POST** | `/api/metrics/` | Send a new metric (JWT or API Key) |
| **GET** | `/api/applications/{id}/forecast/` | Get AI forecast for an application |
| **GET** | `/api/alerts/` | List alerts |

---

## The Agent – How to Use It

### Download the Agent

The agent executable (`APM_Agent.exe`) is available for download from the Home or About pages of the web interface.

### For Non‑Technical Users (GUI Mode)

1. Double‑click the downloaded `APM_Agent.exe` file.
2. Enter your **API Key** and **Application ID** (found in the My Apps page).
3. Set the sending interval (in seconds).
4. Click **Start Monitoring** to send simulated performance data automatically.

### For Developers (CLI Mode)

Open a terminal in the folder where the agent file is located and run:

```bash
APM_Agent.exe --key YOUR_API_KEY --app-id YOUR_APP_ID --interval 5

```

* `--key`: Your API Key.
* `--app-id`: The numeric ID of your application.
* `--interval`: Time between each metric send (default = 5 seconds).

> **Configuration File:** The agent automatically saves your settings in `agent_config.ini` next to the executable, avoiding the need to re-enter them next time.

---

## Testing the System

### 1. Create a User

Go to `http://127.0.0.1:8000/register/` or via Postman:

```json
POST /api/auth/register/
{
  "username": "test_user",
  "password": "Secure@1234",
  "password2": "Secure@1234",
  "email": "test@example.com"
}

```

### 2. Create an Application

Via Admin panel (`/admin/monitor/application/add/`) or via API (with JWT token):

```json
POST /api/applications/
{
  "name": "My Test App",
  "description": "Testing the system"
}

```

### 3. Send Data via the Agent

Run the agent using the generated API Key and Application ID.

### 4. Check the Dashboard

Open `http://127.0.0.1:8000/dashboard/` to view:

* Updating statistical cards.
* Real-time line charts showing metrics over time.
* Request and error distribution charts.

---

## AI Forecasting (Prophet)

* The system uses **Prophet** to predict response times for the next 60 minutes.
* Forecasts are generated automatically every hour via a Celery background task.
* Requires at least 10 data points to run effectively.
* Appears on the dashboard as a dashed purple line with a confidence interval.

---

## Support & Contact
For any questions or issues:
* **Developer:** Nour Arnous
* **Email:** nourarnous.dev@example.com

```

```
