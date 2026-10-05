from fastapi import FastAPI

app = FastAPI(title="FashionOS AI service")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

# Rules (SRS FR-AI-00..05): the main API calls this service with a 3 second timeout and always has a fallback.
# Never receive full phone numbers, addresses, salary or payment data here.
