# =============================================================
# AeroDesk — FastAPI Application Entry Point
# backend/main.py
# =============================================================

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os

load_dotenv()

# =============================================================
# APPLICATION INSTANCE
# =============================================================

app = FastAPI(
    title="AeroDesk API",
    description="Airline Reservation and Flight Management System — Internal Staff API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================
# CORS MIDDLEWARE
# =============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================
# GLOBAL EXCEPTION HANDLER
# Returns clean JSON for unhandled errors
# =============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# =============================================================
# ROUTERS
# =============================================================

from backend.routers import auth_router
from backend.routers import passengers_router
from backend.routers import airports_router
from backend.routers import aircraft_router
from backend.routers import fare_classes_router
from backend.routers import staff_router
from backend.routers import flights_router
from backend.routers import bookings_router
from backend.routers import boarding_router
from backend.routers import reports_router

app.include_router(auth_router.router,          prefix="/auth",         tags=["Authentication"])
app.include_router(passengers_router.router,    prefix="/passengers",   tags=["Passengers"])
app.include_router(airports_router.router,      prefix="/airports",     tags=["Airports"])
app.include_router(aircraft_router.router,      prefix="/aircraft",     tags=["Aircraft"])
app.include_router(fare_classes_router.router,  prefix="/fare-classes", tags=["Fare Classes"])
app.include_router(staff_router.router,         prefix="/staff",        tags=["Staff"])
app.include_router(flights_router.router,       prefix="/flights",      tags=["Flights"])
app.include_router(bookings_router.router,      prefix="/bookings",     tags=["Bookings"])
app.include_router(boarding_router.router,      prefix="/boarding",     tags=["Boarding & Manifest"])
app.include_router(reports_router.router,       prefix="/reports",      tags=["Reports"])

# =============================================================
# HEALTH CHECK
# =============================================================

@app.get("/", tags=["Health"])
def root():
    return {
        "system":   "AeroDesk",
        "version":  "1.0.0",
        "status":   "running",
        "docs":     "http://localhost:8000/docs"
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
