## Setup
Inside the backend folder execute:

1. Sync packages:

```
$ uv sync
```


2. Fill database with dummy data:

```
$ uv run python3 -m src.scripts.populate_dummy_data
```


3. Start backend:

```
$ uv run python3 app.py
```


4. Test with e.g. postman:

```
GET http://127.0.0.1:8000/api/companies/
```
