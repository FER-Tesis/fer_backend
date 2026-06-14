from fastapi import FastAPI
from app.core.cors import configure_cors
from app.api.users_routes import router as user_router
from app.api.supervisor_agent_routes import router as supervisor_agent_router
from app.db.connection import connect_db, close_db
from app.events.event_bus import event_bus

app = FastAPI(title="User Service", version="1.0", root_path="/users")

configure_cors(app)

@app.on_event("startup")
async def startup_event():
    await connect_db()
    await event_bus.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()
    await event_bus.disconnect()

app.include_router(user_router, prefix="/api/user", tags=["user"])
app.include_router(supervisor_agent_router, prefix="/api/relations", tags=["relations"])