# distributed_library

1️Normal start-up (most common case)
Use this when central.db and the branch_*.db files already exist.
1. Activate your virtualenv
In every new terminal/tab:
cd ~/distributed-library
source .venv/bin/activate

2. Start the central service
Terminal 1:
cd ~/distributed-library
source .venv/bin/activate

export DATABASE_URL="sqlite:///central.db"
export SERVICE_API_KEY="super-secret-key"
export JWT_SECRET="another-secret"
export PORT=5000

python3 -m central_service.app

Central UI will be at: http://localhost:5000/

3. Start each branch service (one terminal per branch)
Downtown Toronto
Terminal 2:
cd ~/distributed-library
source .venv/bin/activate

export DATABASE_URL="sqlite:///branch_downtown.db"
export SERVICE_API_KEY="super-secret-key"
export CENTRAL_BASE_URL="http://localhost:5000"
export BRANCH_CODE="DOWNTOWN_TORONTO"
export PORT=5001

python3 -m branch_service.app

North York
Terminal 3:
cd ~/distributed-library
source .venv/bin/activate

export DATABASE_URL="sqlite:///branch_northyork.db"
export SERVICE_API_KEY="super-secret-key"
export CENTRAL_BASE_URL="http://localhost:5000"
export BRANCH_CODE="NORTH_YORK"
export PORT=5002

python3 -m branch_service.app

Scarborough
Terminal 4:
cd ~/distributed-library
source .venv/bin/activate

export DATABASE_URL="sqlite:///branch_scarborough.db"
export SERVICE_API_KEY="super-secret-key"
export CENTRAL_BASE_URL="http://localhost:5000"
export BRANCH_CODE="SCARBOROUGH"
export PORT=5003

python3 -m branch_service.app

Mississauga
Terminal 5:
cd ~/distributed-library
source .venv/bin/activate

export DATABASE_URL="sqlite:///branch_mississauga.db"
export SERVICE_API_KEY="super-secret-key"
export CENTRAL_BASE_URL="http://localhost:5000"
export BRANCH_CODE="MISSISSAUGA"
export PORT=5004

python3 -m branch_service.app

Brampton
Terminal 6:
cd ~/distributed-library
source .venv/bin/activate

export DATABASE_URL="sqlite:///branch_brampton.db"
export SERVICE_API_KEY="super-secret-key"
export CENTRAL_BASE_URL="http://localhost:5000"
export BRANCH_CODE="BRAMPTON"
export PORT=5005

python3 -m branch_service.app

That’s it for a normal day: central + 5 branches running, data already in the DBs.
Open http://localhost:5000/ in the browser and you’re good.

2️Full reset from scratch (fresh DBs)
Use this if you delete central.db or any branch_*.db, or you’ve just cloned the repo.
0. (Optional) Delete old DBs
cd ~/distributed-library

rm -f central.db \
      branch_downtown.db \
      branch_northyork.db \
      branch_scarborough.db \
      branch_mississauga.db \
      branch_brampton.db

1. Start central service
Same as above:
cd ~/distributed-library
source .venv/bin/activate

export DATABASE_URL="sqlite:///central.db"
export SERVICE_API_KEY="super-secret-key"
export JWT_SECRET="another-secret"
export PORT=5000

python3 -m central_service.app

2. Start all 5 branches
Use the same commands as in section 1 for each branch (downtown, north_york, etc.).
 Each in its own terminal with its own DB filename and PORT.
3. Seed demo branches + books
New terminal:
cd ~/distributed-library
source .venv/bin/activate

python3 seed_demo.py

You should see it:
registering the 5 branches with central


seeding 10 books into each branch


central logs a bunch of /api/global/sync/availability calls


4. Create a demo user (e.g. Alice, ID 123)
Still in that terminal:
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "123",
    "name": "Alice Example",
    "email": "alice@example.com",
    "home_branch": "DOWNTOWN_TORONTO"
  }'

You should get a JSON response showing created: true and each branch ok: true.
5. Quick sanity checks (optional but handy)
curl http://localhost:5000/api/branches
curl http://localhost:5000/api/global/books
curl http://localhost:5000/api/user_central/123

You should see:
5 branches


10 books


user 123 coming back from /api/user_central/123



3️ Using the system (user flow reminder)
Go to http://localhost:5000/ (Dashboard).


Click “Borrow a book” or scroll to the Sign in to get started panel.


Enter 123 in Library user ID and click Log in.


If login succeeds, you’ll see a friendly “Logged in as Alice Example” message.


Click “Search for a book →” – it takes you to catalog.html.


On Global catalog:


Search or scroll to the title you want.


Use the branch badges & any “Borrow” controls you add later to place the loan.

