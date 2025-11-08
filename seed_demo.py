# seed_demo.py
import requests

CENTRAL_BASE_URL = "http://localhost:5000"
SERVICE_API_KEY = "super-secret-key"

BRANCHES = [
    {
        "code": "DOWNTOWN_TORONTO",
        "name": "Toronto Reference Library",
        "base_url": "http://localhost:5001",
    },
    {
        "code": "NORTH_YORK",
        "name": "North York Central Library",
        "base_url": "http://localhost:5002",
    },
    {
        "code": "SCARBOROUGH",
        "name": "Scarborough Civic Centre Library",
        "base_url": "http://localhost:5003",
    },
    {
        "code": "MISSISSAUGA",
        "name": "Mississauga Central Library",
        "base_url": "http://localhost:5004",
    },
    {
        "code": "BRAMPTON",
        "name": "Brampton Four Corners Library",
        "base_url": "http://localhost:5005",
    },
]

BOOKS = [
    {
        "isbn": "978-0132350884",
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "publisher": "Prentice Hall",
        "year": 2008,
    },
    {
        "isbn": "978-0201616224",
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt, David Thomas",
        "publisher": "Addison-Wesley",
        "year": 1999,
    },
    {
        "isbn": "978-0131103627",
        "title": "The C Programming Language",
        "author": "Brian W. Kernighan, Dennis M. Ritchie",
        "publisher": "Prentice Hall",
        "year": 1988,
    },
    {
        "isbn": "978-0134685991",
        "title": "Effective Java",
        "author": "Joshua Bloch",
        "publisher": "Addison-Wesley",
        "year": 2018,
    },
    {
        "isbn": "978-0262033848",
        "title": "Introduction to Algorithms",
        "author": "Cormen, Leiserson, Rivest, Stein",
        "publisher": "MIT Press",
        "year": 2009,
    },
    {
        "isbn": "978-0134494166",
        "title": "Clean Architecture",
        "author": "Robert C. Martin",
        "publisher": "Prentice Hall",
        "year": 2017,
    },
    {
        "isbn": "978-1491950357",
        "title": "Designing Data-Intensive Applications",
        "author": "Martin Kleppmann",
        "publisher": "O'Reilly Media",
        "year": 2017,
    },
    {
        "isbn": "978-0135974445",
        "title": "Operating System Concepts",
        "author": "Silberschatz, Galvin, Gagne",
        "publisher": "Wiley",
        "year": 2018,
    },
    {
        "isbn": "978-1617296086",
        "title": "Kubernetes in Action",
        "author": "Marko Luksa",
        "publisher": "Manning",
        "year": 2017,
    },
    {
        "isbn": "978-1492078005",
        "title": "Kubernetes: Up & Running",
        "author": "Kelsey Hightower, Brendan Burns, Joe Beda",
        "publisher": "O'Reilly Media",
        "year": 2022,
    },
]


def check_service(name, url):
    """Hit /api/health and return True/False."""
    health_url = f"{url.rstrip('/')}/api/health"
    try:
        r = requests.get(health_url, timeout=3)
        print(f"[CHECK] {name} -> {health_url} -> {r.status_code}")
        return r.ok
    except Exception as e:
        print(f"[ERROR] {name} not reachable at {health_url}: {e}")
        return False


def register_branches():
    print("\n== Registering branches with central ==")
    ok = True
    for b in BRANCHES:
        try:
            resp = requests.post(
                f"{CENTRAL_BASE_URL}/api/branches",
                json={
                    "code": b["code"],
                    "name": b["name"],
                    "base_url": b["base_url"],
                },
                timeout=5,
            )
            print(f"  {b['code']}: {resp.status_code} {resp.text.strip()}")
            if not resp.ok:
                ok = False
        except Exception as e:
            print(f"  {b['code']}: FAILED -> {e}")
            ok = False
    return ok


def seed_books_for_branch(branch):
    print(f"\n== Seeding books for {branch['code']} ({branch['base_url']}) ==")

    for i, book in enumerate(BOOKS, start=1):
        payload = dict(book)
        # vary copies per title to make availability more interesting
        payload["total_copies"] = 2 + (i % 4)  # 2–5 copies

        try:
            resp = requests.post(
                f"{branch['base_url']}/api/books",
                headers={"X-API-Key": SERVICE_API_KEY},
                json=payload,
                timeout=5,
            )
            print(f"  [{i:02}] {book['title']} -> {resp.status_code}")
            if not resp.ok:
                print(f"      Body: {resp.text.strip()}")
        except Exception as e:
            print(f"  [{i:02}] {book['title']} -> FAILED: {e}")


def main():
    # 0) Make sure central is up
    print("Checking central service...")
    if not check_service("Central", CENTRAL_BASE_URL):
        print("\nCentral service is not reachable. Make sure it is running on 5000.")
        return

    # 1) Make sure each branch is up
    live_branches = []
    print("\nChecking branch services...")
    for b in BRANCHES:
        if check_service(b["code"], b["base_url"]):
            live_branches.append(b)
        else:
            print(f"  Skipping {b['code']} because /api/health failed.")

    if not live_branches:
        print("\nNo branch services are reachable, nothing to seed.")
        return

    # 2) Register all branches with central
    register_branches()

    # 3) Seed books into each live branch (this also triggers availability sync)
    for b in live_branches:
        seed_books_for_branch(b)

    # 4) Small hint for you
    print("\nDone.")
    print("Try hitting:")
    print("  http://localhost:5000/api/global/books")
    print("and refresh catalog.html in the browser.")


if __name__ == "__main__":
    main()
