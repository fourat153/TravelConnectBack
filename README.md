# TravelConnect

A social travel platform that connects travelers, enabling them to share trips, discover destinations, and connect with people who share the same travel interests.

---

## Tech Stack

- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Authentication:** JWT (OAuth2)
- **Email:** fastapi-mail + Jinja2

---

## Project Structure

```
TravelConnectBack/
├── app/
│   ├── models/         # SQLAlchemy models (one file per table)
|   |── services        
│   ├── schema/         # Pydantic schemas
│   ├── router/         # FastAPI routers
│   ├── utils/          # Helpers (error handling, email, etc.)
│   └── database.py     # DB session and engine
├── alembic/            # Migrations
├── Dbengin.py          # SQLAlchemy base
├── main.py             # App entry point
├── .env                # Environment variables (not committed)
└── alembic.ini
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL running on port 5433

### Installation

```bash
# Clone the repo
git clone https://github.com/your-username/TravelConnectBack.git
cd TravelConnectBack

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the root:

```env
DATABASE_URL=postgresql://user:password@localhost:5433/travelconnect
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
MAIL_USERNAME=your_email
MAIL_PASSWORD=your_password
MAIL_FROM=your_email
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
```

### Run Migrations

```bash
alembic upgrade head
```

### Start the Server

```bash
uvicorn main:app --reload
```

API will be available at `http://localhost:8000`

Interactive docs at `http://localhost:8000/docs`

---

## Contributing

This project is under active development. Branch naming convention: `Dev/{initials}_{feature}`.
