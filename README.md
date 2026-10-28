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

### Paginated list endpoints

List endpoints accept `page_number` and `page_size` query parameters. Paginated
responses include the result collection together with `page_number`,
`page_size`, `total_pages`, and `total_records`. The default page size is 10
and the maximum page size is 100.

### Seed local demo data

After applying migrations, run the repeatable demo seeder from the repository
root:

```bash
python -m scripts.seed
```

The command uses the same `database_*` environment variables as the
application. It creates demo users, cities, public trips and ordered stops,
posts, friendships, likes, comments, and notifications. Existing records are
never deleted or reset, and matching demo records are skipped on later runs.

For local development, the demo accounts all use the password
`TravelConnectDemo123!`:

- `alice.demo@travelconnect.local`
- `ben.demo@travelconnect.local`
- `claire.demo@travelconnect.local`
- `diego.demo@travelconnect.local`
- `emma.demo@travelconnect.local`
- `finn.demo@travelconnect.local`
- `grace.demo@travelconnect.local`

The seeder creates one stable public image row for every demo post, so posts
display media immediately through the normal API without requiring a
Cloudinary upload. New media can still be added through the existing upload
endpoints when Cloudinary credentials are configured.

Every demo user also likes and comments on each post owned by another demo
user. Self-likes and self-comments are intentionally excluded.

Emma, Finn, and Grace are profile-only demo users. They are intentionally not
connected by friendships to the existing user with ID `26`, or to the other
seeded users.

Each demo user is also connected through a friendship to the existing account
`ahmedli@yopmail.com` (database user ID `26`). The seeder stops with an explicit
error if that email and ID do not identify the same account.

---

## Contributing

This project is under active development. Branch naming convention: `Dev/{initials}_{feature}`.
