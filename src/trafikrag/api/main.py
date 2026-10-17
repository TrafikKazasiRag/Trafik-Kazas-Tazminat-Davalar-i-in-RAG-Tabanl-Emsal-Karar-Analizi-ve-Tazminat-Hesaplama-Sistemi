from fastapi import FastAPI

app = FastAPI(title="Trafik Kazası RAG")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
