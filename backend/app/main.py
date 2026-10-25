from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import creator, follower

app = FastAPI(title="道案内 API")

# 開発用。本番ではフロントの公開 URL に絞る
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(creator.router, prefix="/api", tags=["creator"])
app.include_router(follower.router, prefix="/api", tags=["follower"])
app.include_router(follower.pages, tags=["follower"])  # /r/{id}: QR の飛び先
