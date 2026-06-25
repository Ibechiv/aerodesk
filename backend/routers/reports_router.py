# =============================================================
# AeroDesk — Reports Router
# backend/routers/reports_router.py
# =============================================================
# Revenue and operational reports using SQL aggregates
# Access: Super_Admin, Finance_Officer, Operations_Manager
# =============================================================

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date

from backend.database import get_db
from backend.models.models import Staff, StaffRoleEnum
from backend.auth.auth import require_roles

router = APIRouter()

REPORT_ROLES = (
    StaffRoleEnum.Super_Admin,
    StaffRoleEnum.Finance_Officer,
    StaffRoleEnum.Operations_Manager,
)


@router.get("/revenue")
def revenue_report(
    date_from:      Optional[date] = Query(None, description="Start date YYYY-MM-DD"),
    date_to:        Optional[date] = Query(None, description="End date YYYY-MM-DD"),
    db:             Session        = Depends(get_db),
    current_user:   Staff          = Depends(require_roles(*REPORT_ROLES))
):
    """
    Revenue report with SQL aggregates.
    Returns: total revenue, revenue by class, revenue by route,
             revenue by payment method, top flights by revenue.
    """

    date_filter = ""
    params = {}
    if date_from:
        date_filter += " AND p.payment_date >= :date_from"
        params["date_from"] = date_from
    if date_to:
        date_filter += " AND p.payment_date <= :date_to"
        params["date_to"] = date_to

    # Total revenue
    total_sql = text(f"""
        SELECT
            COUNT(p.payment_id)         AS total_transactions,
            SUM(p.amount)               AS total_revenue,
            AVG(p.amount)               AS average_fare,
            SUM(p.refund_amount)        AS total_refunds,
            SUM(p.amount) - SUM(p.refund_amount) AS net_revenue
        FROM payments p
        WHERE p.status IN ('Completed', 'Refunded')
        {date_filter}
    """)
    total = dict(db.execute(total_sql, params).mappings().one())

    # Revenue by class
    class_sql = text(f"""
        SELECT
            fc.class_name,
            COUNT(t.ticket_id)          AS tickets_sold,
            SUM(t.final_fare)           AS class_revenue,
            AVG(t.final_fare)           AS avg_fare,
            fc.multiplier
        FROM tickets t
        JOIN fare_classes fc ON t.fare_class_id = fc.fare_class_id
        JOIN bookings b ON t.booking_id = b.booking_id
        JOIN payments p ON b.booking_id = p.booking_id
        WHERE t.is_cancelled = FALSE
        AND p.status = 'Completed'
        {date_filter}
        GROUP BY fc.class_name, fc.multiplier
        ORDER BY class_revenue DESC
    """)
    by_class = [dict(r) for r in db.execute(class_sql, params).mappings().all()]

    # Revenue by route
    route_sql = text(f"""
        SELECT
            oa.iata_code || ' → ' || da.iata_code  AS route,
            COUNT(b.booking_id)                     AS bookings,
            SUM(p.amount)                           AS route_revenue,
            AVG(p.amount)                           AS avg_fare
        FROM bookings b
        JOIN flights f  ON b.flight_id      = f.flight_id
        JOIN airports oa ON f.origin_airport_id = oa.airport_id
        JOIN airports da ON f.dest_airport_id   = da.airport_id
        JOIN payments p  ON b.booking_id        = p.booking_id
        WHERE p.status = 'Completed'
        {date_filter}
        GROUP BY oa.iata_code, da.iata_code
        ORDER BY route_revenue DESC
    """)
    by_route = [dict(r) for r in db.execute(route_sql, params).mappings().all()]

    # Revenue by payment method
    method_sql = text(f"""
        SELECT
            p.method                    AS payment_method,
            COUNT(p.payment_id)         AS transaction_count,
            SUM(p.amount)               AS method_revenue
        FROM payments p
        WHERE p.status = 'Completed'
        {date_filter}
        GROUP BY p.method
        ORDER BY method_revenue DESC
    """)
    by_method = [dict(r) for r in db.execute(method_sql, params).mappings().all()]

    # Top flights by revenue
    top_flights_sql = text(f"""
        SELECT
            f.flight_no,
            oa.iata_code || ' → ' || da.iata_code  AS route,
            COUNT(b.booking_id)                     AS passengers,
            SUM(p.amount)                           AS flight_revenue
        FROM flights f
        JOIN bookings b  ON f.flight_id         = b.flight_id
        JOIN airports oa ON f.origin_airport_id = oa.airport_id
        JOIN airports da ON f.dest_airport_id   = da.airport_id
        JOIN payments p  ON b.booking_id        = p.booking_id
        WHERE p.status = 'Completed'
        {date_filter}
        GROUP BY f.flight_no, oa.iata_code, da.iata_code
        ORDER BY flight_revenue DESC
        LIMIT 10
    """)
    top_flights = [dict(r) for r in db.execute(top_flights_sql, params).mappings().all()]

    return {
        "report_type":  "Revenue Report",
        "date_from":    str(date_from) if date_from else "All time",
        "date_to":      str(date_to)   if date_to   else "All time",
        "summary":      total,
        "by_class":     by_class,
        "by_route":     by_route,
        "by_method":    by_method,
        "top_flights":  top_flights,
    }


@router.get("/operational")
def operational_report(
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*REPORT_ROLES))
):
    """
    Operational report.
    Returns: flight counts by status, seat occupancy rates,
             on-time performance, no-show rates.
    """

    # Flights by status
    status_sql = text("""
        SELECT
            status,
            COUNT(*) AS flight_count
        FROM flights
        GROUP BY status
        ORDER BY flight_count DESC
    """)
    by_status = [dict(r) for r in db.execute(status_sql).mappings().all()]

    # Seat occupancy per flight
    occupancy_sql = text("""
        SELECT
            f.flight_no,
            oa.iata_code || ' → ' || da.iata_code  AS route,
            ac.seat_capacity,
            COUNT(b.booking_id)                     AS confirmed_bookings,
            ROUND(
                COUNT(b.booking_id)::NUMERIC /
                NULLIF(ac.seat_capacity, 0) * 100, 1
            )                                       AS occupancy_percent
        FROM flights f
        JOIN aircraft ac ON f.aircraft_id       = ac.aircraft_id
        JOIN airports oa ON f.origin_airport_id = oa.airport_id
        JOIN airports da ON f.dest_airport_id   = da.airport_id
        LEFT JOIN bookings b ON f.flight_id     = b.flight_id
            AND b.status = 'Confirmed'
        GROUP BY f.flight_no, oa.iata_code, da.iata_code, ac.seat_capacity
        ORDER BY occupancy_percent DESC NULLS LAST
    """)
    occupancy = [dict(r) for r in db.execute(occupancy_sql).mappings().all()]

    # No-show rate per flight
    noshow_sql = text("""
        SELECT
            f.flight_no,
            COUNT(br.boarding_id)                                           AS total_boarded,
            COUNT(CASE WHEN br.status = 'No_Show' THEN 1 END)              AS no_shows,
            COUNT(CASE WHEN br.status = 'Boarded' THEN 1 END)              AS boarded,
            ROUND(
                COUNT(CASE WHEN br.status = 'No_Show' THEN 1 END)::NUMERIC /
                NULLIF(COUNT(br.boarding_id), 0) * 100, 1
            )                                                               AS noshow_percent
        FROM flights f
        JOIN boarding_records br ON f.flight_id = br.flight_id
        GROUP BY f.flight_no
        ORDER BY noshow_percent DESC NULLS LAST
    """)
    noshow = [dict(r) for r in db.execute(noshow_sql).mappings().all()]

    # On-time performance
    ontime_sql = text("""
        SELECT
            f.flight_no,
            fs.dep_datetime     AS scheduled_dep,
            fs.actual_dep       AS actual_dep,
            CASE
                WHEN fs.actual_dep IS NULL THEN 'Not Departed'
                WHEN fs.actual_dep <= fs.dep_datetime THEN 'On Time'
                ELSE 'Delayed'
            END                 AS departure_status,
            CASE
                WHEN fs.actual_dep IS NOT NULL AND fs.actual_dep > fs.dep_datetime
                THEN EXTRACT(EPOCH FROM (fs.actual_dep - fs.dep_datetime)) / 60
                ELSE 0
            END                 AS delay_minutes
        FROM flights f
        JOIN flight_schedules fs ON f.flight_id = fs.flight_id
        ORDER BY fs.dep_datetime DESC
    """)
    ontime = [dict(r) for r in db.execute(ontime_sql).mappings().all()]

    # Overall stats
    stats_sql = text("""
        SELECT
            COUNT(DISTINCT f.flight_id)         AS total_flights,
            COUNT(DISTINCT b.booking_id)        AS total_bookings,
            COUNT(DISTINCT p.passenger_id)      AS total_passengers,
            COUNT(DISTINCT CASE WHEN b.status = 'Cancelled'
                THEN b.booking_id END)          AS cancelled_bookings
        FROM flights f
        LEFT JOIN bookings b    ON f.flight_id      = b.flight_id
        LEFT JOIN passengers p  ON b.passenger_id   = p.passenger_id
    """)
    overall = dict(db.execute(stats_sql).mappings().one())

    return {
        "report_type":          "Operational Report",
        "overall_stats":        overall,
        "flights_by_status":    by_status,
        "seat_occupancy":       occupancy,
        "noshow_rates":         noshow,
        "ontime_performance":   ontime,
    }
