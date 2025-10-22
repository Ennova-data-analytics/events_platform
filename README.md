# Events Platform

A full-stack event management platform built with FastAPI and Vue.js, featuring event creation, ticketing, payment processing, and user management.

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - SQL toolkit and ORM
- **PostgreSQL** - Database
- **Alembic** - Database migrations
- **Stripe** - Payment processing
- **Resend** - Email service
- **JWT** - Authentication
- **AWS S3** (via boto3) - File storage

### Frontend
- **Vue 3** - Progressive JavaScript framework
- **Vuetify** - Material Design component framework
- **Vue Router** - Client-side routing
- **Pinia** - State management
- **Axios** - HTTP client
- **Vite** - Build tool

### Infrastructure
- **Docker** - Containerization
- **Nginx** - Web server & reverse proxy
- **Let's Encrypt** (via Certbot) - SSL certificates

## Project Structure

```
events_platform/
├── backend/              # FastAPI backend
│   ├── api/             # API endpoints
│   ├── core/            # Core configuration
│   ├── db/              # Database models
│   ├── domain/          # Business logic
│   ├── alembic/         # Database migrations
│   └── main.py          # Application entry point
├── frontend/            # Vue.js frontend
│   └── src/
│       ├── components/  # Vue components
│       ├── views/       # Page views
│       ├── router/      # Routing configuration
│       ├── stores/      # Pinia stores
│       └── services/    # API services
├── nginx/               # Nginx configuration
└── docker-compose.yml   # Docker orchestration
```

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Node.js 20.19+ or 22.12+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Environment Setup

Create a `.env` file in the root directory with the following variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/dbname

# Authentication
SECRET_KEY=your-secret-key
ALGORITHM=HS256

# AWS S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=your-region
S3_BUCKET_NAME=your-bucket-name

# Stripe
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key

# Email
RESEND_API_KEY=your-resend-api-key
```

### Running with Docker

1. Build and start all services:
```bash
docker-compose up --build
```

2. Access the application:
   - Frontend: http://localhost
   - Backend API: http://localhost/api
   - API Documentation: http://localhost/docs

### Local Development

#### Backend

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
# or
poetry install
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the development server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. Build for production:
```bash
npm run build
```

## Features

- Event creation and management
- Ticket purchasing and management
- User authentication and authorization
- Payment processing via Stripe
- Email notifications
- File uploads to AWS S3
- Responsive design with Vuetify
- SSL/HTTPS support

## API Documentation

Once the backend is running, visit `/docs` for interactive API documentation (Swagger UI) or `/redoc` for alternative documentation.

## Database Migrations

Create a new migration:
```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

## License

This project is private and proprietary.

## Author

Alan Fijał
