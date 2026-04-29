"""
RealtouchHR - Time & Scheduling Service
Clock-in/out, Shift Scheduling, Rotas, and Timesheet Management

Features:
- Employee clock-in/clock-out with location tracking
- Shift scheduling and rota management
- Timesheet generation and approval workflow
- Overtime calculation
- Break tracking
"""

import os
import logging
from datetime import datetime, timezone, timedelta, date
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
import uuid

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class ClockEventType(str, Enum):
    CLOCK_IN = "clock_in"
    CLOCK_OUT = "clock_out"
    BREAK_START = "break_start"
    BREAK_END = "break_end"


class ShiftStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MISSED = "missed"
    CANCELLED = "cancelled"


class TimesheetStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class RotaStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# ==================== DATA CLASSES ====================

@dataclass
class ClockEvent:
    """A single clock event (in/out/break)"""
    event_id: str
    employee_id: str
    company_id: str
    event_type: ClockEventType
    timestamp: datetime
    location: Optional[Dict[str, float]] = None  # {lat, lng}
    location_name: Optional[str] = None
    device_info: Optional[str] = None
    notes: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "employee_id": self.employee_id,
            "company_id": self.company_id,
            "event_type": self.event_type.value if isinstance(self.event_type, ClockEventType) else self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "location": self.location,
            "location_name": self.location_name,
            "device_info": self.device_info,
            "notes": self.notes
        }


@dataclass
class Shift:
    """A scheduled shift"""
    shift_id: str
    company_id: str
    employee_id: str
    rota_id: Optional[str] = None
    date: date = None
    start_time: datetime = None
    end_time: datetime = None
    break_duration_minutes: int = 0
    role: Optional[str] = None
    location: Optional[str] = None
    status: ShiftStatus = ShiftStatus.SCHEDULED
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    actual_break_minutes: int = 0
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        return {
            "shift_id": self.shift_id,
            "company_id": self.company_id,
            "employee_id": self.employee_id,
            "rota_id": self.rota_id,
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "break_duration_minutes": self.break_duration_minutes,
            "role": self.role,
            "location": self.location,
            "status": self.status.value if isinstance(self.status, ShiftStatus) else self.status,
            "actual_start": self.actual_start.isoformat() if self.actual_start else None,
            "actual_end": self.actual_end.isoformat() if self.actual_end else None,
            "actual_break_minutes": self.actual_break_minutes,
            "notes": self.notes,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class Rota:
    """A weekly rota/schedule"""
    rota_id: str
    company_id: str
    name: str
    week_start_date: date
    week_end_date: date
    status: RotaStatus = RotaStatus.DRAFT
    created_by: str = None
    published_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        return {
            "rota_id": self.rota_id,
            "company_id": self.company_id,
            "name": self.name,
            "week_start_date": self.week_start_date.isoformat(),
            "week_end_date": self.week_end_date.isoformat(),
            "status": self.status.value if isinstance(self.status, RotaStatus) else self.status,
            "created_by": self.created_by,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class Timesheet:
    """Weekly timesheet for approval"""
    timesheet_id: str
    company_id: str
    employee_id: str
    week_start_date: date
    week_end_date: date
    total_hours: float = 0
    regular_hours: float = 0
    overtime_hours: float = 0
    break_hours: float = 0
    status: TimesheetStatus = TimesheetStatus.DRAFT
    submitted_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    entries: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        return {
            "timesheet_id": self.timesheet_id,
            "company_id": self.company_id,
            "employee_id": self.employee_id,
            "week_start_date": self.week_start_date.isoformat(),
            "week_end_date": self.week_end_date.isoformat(),
            "total_hours": self.total_hours,
            "regular_hours": self.regular_hours,
            "overtime_hours": self.overtime_hours,
            "break_hours": self.break_hours,
            "status": self.status.value if isinstance(self.status, TimesheetStatus) else self.status,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "entries": self.entries,
            "created_at": self.created_at.isoformat()
        }


# ==================== TIME SERVICE ====================

class TimeSchedulingService:
    """Service for time tracking and scheduling"""
    
    def __init__(self):
        self.standard_hours_per_week = 37.5  # UK standard
        self.overtime_threshold_daily = 8  # Hours after which overtime kicks in
    
    # ==================== CLOCK EVENTS ====================
    
    async def clock_in(
        self,
        employee_id: str,
        company_id: str,
        location: Optional[Dict[str, float]] = None,
        location_name: Optional[str] = None,
        device_info: Optional[str] = None,
        notes: Optional[str] = None
    ) -> ClockEvent:
        """Record employee clock-in"""
        # Check if already clocked in
        last_event = await self._get_last_clock_event(employee_id)
        if last_event and last_event.get("event_type") == ClockEventType.CLOCK_IN.value:
            raise ValueError("Employee is already clocked in. Please clock out first.")
        
        event = ClockEvent(
            event_id=f"clk_{uuid.uuid4().hex[:12]}",
            employee_id=employee_id,
            company_id=company_id,
            event_type=ClockEventType.CLOCK_IN,
            timestamp=datetime.now(timezone.utc),
            location=location,
            location_name=location_name,
            device_info=device_info,
            notes=notes
        )
        
        await db.clock_events.insert_one(event.to_dict())
        
        # Update any scheduled shift
        await self._update_shift_actual_start(employee_id, event.timestamp)
        
        return event
    
    async def clock_out(
        self,
        employee_id: str,
        company_id: str,
        location: Optional[Dict[str, float]] = None,
        location_name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> ClockEvent:
        """Record employee clock-out"""
        # Check if clocked in
        last_event = await self._get_last_clock_event(employee_id)
        if not last_event or last_event.get("event_type") != ClockEventType.CLOCK_IN.value:
            raise ValueError("Employee is not clocked in.")
        
        event = ClockEvent(
            event_id=f"clk_{uuid.uuid4().hex[:12]}",
            employee_id=employee_id,
            company_id=company_id,
            event_type=ClockEventType.CLOCK_OUT,
            timestamp=datetime.now(timezone.utc),
            location=location,
            location_name=location_name,
            notes=notes
        )
        
        await db.clock_events.insert_one(event.to_dict())
        
        # Update shift actual end
        await self._update_shift_actual_end(employee_id, event.timestamp)
        
        return event
    
    async def start_break(
        self,
        employee_id: str,
        company_id: str
    ) -> ClockEvent:
        """Record break start"""
        event = ClockEvent(
            event_id=f"clk_{uuid.uuid4().hex[:12]}",
            employee_id=employee_id,
            company_id=company_id,
            event_type=ClockEventType.BREAK_START,
            timestamp=datetime.now(timezone.utc)
        )
        
        await db.clock_events.insert_one(event.to_dict())
        return event
    
    async def end_break(
        self,
        employee_id: str,
        company_id: str
    ) -> ClockEvent:
        """Record break end"""
        event = ClockEvent(
            event_id=f"clk_{uuid.uuid4().hex[:12]}",
            employee_id=employee_id,
            company_id=company_id,
            event_type=ClockEventType.BREAK_END,
            timestamp=datetime.now(timezone.utc)
        )
        
        await db.clock_events.insert_one(event.to_dict())
        return event
    
    async def get_employee_status(self, employee_id: str) -> dict:
        """Get current clock status for an employee"""
        last_event = await self._get_last_clock_event(employee_id)
        
        if not last_event:
            return {
                "status": "not_clocked_in",
                "last_event": None
            }
        
        event_type = last_event.get("event_type")
        
        if event_type == ClockEventType.CLOCK_IN.value:
            clock_in_time = datetime.fromisoformat(last_event["timestamp"].replace("Z", "+00:00"))
            duration = datetime.now(timezone.utc) - clock_in_time
            return {
                "status": "clocked_in",
                "clocked_in_at": last_event["timestamp"],
                "duration_minutes": int(duration.total_seconds() / 60),
                "last_event": last_event
            }
        elif event_type == ClockEventType.BREAK_START.value:
            return {
                "status": "on_break",
                "break_started_at": last_event["timestamp"],
                "last_event": last_event
            }
        else:
            return {
                "status": "not_clocked_in",
                "last_event": last_event
            }
    
    async def _get_last_clock_event(self, employee_id: str) -> Optional[dict]:
        """Get the most recent clock event for an employee"""
        event = await db.clock_events.find_one(
            {"employee_id": employee_id},
            {"_id": 0},
            sort=[("timestamp", -1)]
        )
        return event
    
    async def _update_shift_actual_start(self, employee_id: str, timestamp: datetime):
        """Update today's shift with actual start time"""
        today = timestamp.date()
        await db.shifts.update_one(
            {
                "employee_id": employee_id,
                "date": today.isoformat(),
                "status": ShiftStatus.SCHEDULED.value
            },
            {"$set": {
                "actual_start": timestamp.isoformat(),
                "status": ShiftStatus.IN_PROGRESS.value
            }}
        )
    
    async def _update_shift_actual_end(self, employee_id: str, timestamp: datetime):
        """Update today's shift with actual end time"""
        today = timestamp.date()
        await db.shifts.update_one(
            {
                "employee_id": employee_id,
                "date": today.isoformat(),
                "status": ShiftStatus.IN_PROGRESS.value
            },
            {"$set": {
                "actual_end": timestamp.isoformat(),
                "status": ShiftStatus.COMPLETED.value
            }}
        )
    
    # ==================== SHIFTS ====================
    
    async def create_shift(
        self,
        company_id: str,
        employee_id: str,
        shift_date: date,
        start_time: datetime,
        end_time: datetime,
        break_duration_minutes: int = 30,
        role: Optional[str] = None,
        location: Optional[str] = None,
        rota_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Shift:
        """Create a new shift"""
        shift = Shift(
            shift_id=f"shift_{uuid.uuid4().hex[:12]}",
            company_id=company_id,
            employee_id=employee_id,
            rota_id=rota_id,
            date=shift_date,
            start_time=start_time,
            end_time=end_time,
            break_duration_minutes=break_duration_minutes,
            role=role,
            location=location,
            status=ShiftStatus.SCHEDULED
        )
        
        await db.shifts.insert_one(shift.to_dict())
        return shift
    
    async def get_shifts(
        self,
        company_id: str,
        start_date: date,
        end_date: date,
        employee_id: Optional[str] = None
    ) -> List[dict]:
        """Get shifts within a date range"""
        query = {
            "company_id": company_id,
            "date": {
                "$gte": start_date.isoformat(),
                "$lte": end_date.isoformat()
            }
        }
        
        if employee_id:
            query["employee_id"] = employee_id
        
        shifts = await db.shifts.find(query, {"_id": 0}).sort("date", 1).to_list(1000)
        return shifts
    
    async def update_shift(
        self,
        shift_id: str,
        updates: dict
    ) -> dict:
        """Update a shift"""
        now = datetime.now(timezone.utc)
        updates["updated_at"] = now.isoformat()
        
        result = await db.shifts.update_one(
            {"shift_id": shift_id},
            {"$set": updates}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"Shift {shift_id} not found")
        
        return {"status": "updated", "shift_id": shift_id}
    
    async def delete_shift(self, shift_id: str) -> dict:
        """Delete a shift"""
        result = await db.shifts.delete_one({"shift_id": shift_id})
        
        if result.deleted_count == 0:
            raise ValueError(f"Shift {shift_id} not found")
        
        return {"status": "deleted", "shift_id": shift_id}
    
    # ==================== ROTAS ====================
    
    async def create_rota(
        self,
        company_id: str,
        name: str,
        week_start_date: date,
        created_by: str
    ) -> Rota:
        """Create a new rota"""
        week_end_date = week_start_date + timedelta(days=6)
        
        rota = Rota(
            rota_id=f"rota_{uuid.uuid4().hex[:12]}",
            company_id=company_id,
            name=name,
            week_start_date=week_start_date,
            week_end_date=week_end_date,
            status=RotaStatus.DRAFT,
            created_by=created_by
        )
        
        await db.rotas.insert_one(rota.to_dict())
        return rota
    
    async def publish_rota(self, rota_id: str) -> dict:
        """Publish a rota, making it visible to employees"""
        now = datetime.now(timezone.utc)
        
        result = await db.rotas.update_one(
            {"rota_id": rota_id, "status": RotaStatus.DRAFT.value},
            {"$set": {
                "status": RotaStatus.PUBLISHED.value,
                "published_at": now.isoformat()
            }}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"Rota {rota_id} not found or already published")
        
        # TODO: Send notifications to employees
        
        return {"status": "published", "rota_id": rota_id}
    
    async def get_rotas(
        self,
        company_id: str,
        status: Optional[str] = None
    ) -> List[dict]:
        """Get rotas for a company"""
        query = {"company_id": company_id}
        if status:
            query["status"] = status
        
        rotas = await db.rotas.find(query, {"_id": 0}).sort("week_start_date", -1).to_list(100)
        return rotas
    
    async def copy_rota(
        self,
        rota_id: str,
        new_week_start_date: date,
        created_by: str
    ) -> Rota:
        """Copy a rota to a new week"""
        # Get original rota
        original = await db.rotas.find_one({"rota_id": rota_id}, {"_id": 0})
        if not original:
            raise ValueError(f"Rota {rota_id} not found")
        
        # Create new rota
        new_rota = await self.create_rota(
            company_id=original["company_id"],
            name=f"Copy of {original['name']}",
            week_start_date=new_week_start_date,
            created_by=created_by
        )
        
        # Copy shifts
        original_start = date.fromisoformat(original["week_start_date"])
        day_offset = (new_week_start_date - original_start).days
        
        shifts = await db.shifts.find({"rota_id": rota_id}, {"_id": 0}).to_list(1000)
        
        for shift in shifts:
            shift_date = date.fromisoformat(shift["date"])
            new_date = shift_date + timedelta(days=day_offset)
            
            await self.create_shift(
                company_id=shift["company_id"],
                employee_id=shift["employee_id"],
                shift_date=new_date,
                start_time=datetime.fromisoformat(shift["start_time"]),
                end_time=datetime.fromisoformat(shift["end_time"]),
                break_duration_minutes=shift.get("break_duration_minutes", 30),
                role=shift.get("role"),
                location=shift.get("location"),
                rota_id=new_rota.rota_id
            )
        
        return new_rota
    
    # ==================== TIMESHEETS ====================
    
    async def generate_timesheet(
        self,
        employee_id: str,
        company_id: str,
        week_start_date: date
    ) -> Timesheet:
        """Generate a timesheet from clock events"""
        week_end_date = week_start_date + timedelta(days=6)
        
        # Get clock events for the week
        events = await db.clock_events.find({
            "employee_id": employee_id,
            "timestamp": {
                "$gte": datetime.combine(week_start_date, datetime.min.time()).isoformat(),
                "$lte": datetime.combine(week_end_date, datetime.max.time()).isoformat()
            }
        }, {"_id": 0}).sort("timestamp", 1).to_list(1000)
        
        # Calculate hours
        entries = []
        total_hours = 0
        total_break_hours = 0
        
        current_day = week_start_date
        while current_day <= week_end_date:
            day_events = [e for e in events if e["timestamp"].startswith(current_day.isoformat())]
            day_hours, day_breaks = self._calculate_day_hours(day_events)
            
            if day_hours > 0:
                entries.append({
                    "date": current_day.isoformat(),
                    "hours_worked": round(day_hours, 2),
                    "break_hours": round(day_breaks, 2),
                    "events": day_events
                })
                total_hours += day_hours
                total_break_hours += day_breaks
            
            current_day += timedelta(days=1)
        
        # Calculate overtime
        regular_hours = min(total_hours, self.standard_hours_per_week)
        overtime_hours = max(0, total_hours - self.standard_hours_per_week)
        
        timesheet = Timesheet(
            timesheet_id=f"ts_{uuid.uuid4().hex[:12]}",
            company_id=company_id,
            employee_id=employee_id,
            week_start_date=week_start_date,
            week_end_date=week_end_date,
            total_hours=round(total_hours, 2),
            regular_hours=round(regular_hours, 2),
            overtime_hours=round(overtime_hours, 2),
            break_hours=round(total_break_hours, 2),
            status=TimesheetStatus.DRAFT,
            entries=entries
        )
        
        # Save or update
        await db.timesheets.update_one(
            {
                "employee_id": employee_id,
                "week_start_date": week_start_date.isoformat()
            },
            {"$set": timesheet.to_dict()},
            upsert=True
        )
        
        return timesheet
    
    def _calculate_day_hours(self, events: List[dict]) -> tuple:
        """Calculate hours worked and break hours from events"""
        hours_worked = 0
        break_hours = 0
        clock_in_time = None
        break_start_time = None
        
        for event in events:
            event_type = event.get("event_type")
            timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
            
            if event_type == ClockEventType.CLOCK_IN.value:
                clock_in_time = timestamp
            elif event_type == ClockEventType.CLOCK_OUT.value and clock_in_time:
                hours_worked += (timestamp - clock_in_time).total_seconds() / 3600
                clock_in_time = None
            elif event_type == ClockEventType.BREAK_START.value:
                break_start_time = timestamp
            elif event_type == ClockEventType.BREAK_END.value and break_start_time:
                break_hours += (timestamp - break_start_time).total_seconds() / 3600
                break_start_time = None
        
        # Subtract breaks from hours worked
        hours_worked = max(0, hours_worked - break_hours)
        
        return hours_worked, break_hours
    
    async def submit_timesheet(self, timesheet_id: str, employee_id: str) -> dict:
        """Submit a timesheet for approval"""
        now = datetime.now(timezone.utc)
        
        result = await db.timesheets.update_one(
            {
                "timesheet_id": timesheet_id,
                "employee_id": employee_id,
                "status": TimesheetStatus.DRAFT.value
            },
            {"$set": {
                "status": TimesheetStatus.SUBMITTED.value,
                "submitted_at": now.isoformat()
            }}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"Timesheet {timesheet_id} not found or already submitted")
        
        return {"status": "submitted", "timesheet_id": timesheet_id}
    
    async def approve_timesheet(
        self,
        timesheet_id: str,
        approved_by: str
    ) -> dict:
        """Approve a timesheet"""
        now = datetime.now(timezone.utc)
        
        result = await db.timesheets.update_one(
            {
                "timesheet_id": timesheet_id,
                "status": TimesheetStatus.SUBMITTED.value
            },
            {"$set": {
                "status": TimesheetStatus.APPROVED.value,
                "approved_by": approved_by,
                "approved_at": now.isoformat()
            }}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"Timesheet {timesheet_id} not found or not in submitted state")
        
        return {"status": "approved", "timesheet_id": timesheet_id}
    
    async def reject_timesheet(
        self,
        timesheet_id: str,
        rejected_by: str,
        reason: str
    ) -> dict:
        """Reject a timesheet"""
        now = datetime.now(timezone.utc)
        
        result = await db.timesheets.update_one(
            {
                "timesheet_id": timesheet_id,
                "status": TimesheetStatus.SUBMITTED.value
            },
            {"$set": {
                "status": TimesheetStatus.REJECTED.value,
                "approved_by": rejected_by,
                "approved_at": now.isoformat(),
                "rejection_reason": reason
            }}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"Timesheet {timesheet_id} not found or not in submitted state")
        
        return {"status": "rejected", "timesheet_id": timesheet_id}
    
    async def get_timesheets(
        self,
        company_id: str,
        employee_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[dict]:
        """Get timesheets"""
        query = {"company_id": company_id}
        if employee_id:
            query["employee_id"] = employee_id
        if status:
            query["status"] = status
        
        timesheets = await db.timesheets.find(
            query, {"_id": 0}
        ).sort("week_start_date", -1).limit(limit).to_list(limit)
        
        return timesheets
    
    async def get_pending_approvals(self, company_id: str) -> List[dict]:
        """Get all timesheets pending approval"""
        return await self.get_timesheets(
            company_id=company_id,
            status=TimesheetStatus.SUBMITTED.value
        )
    
    # ==================== REPORTS ====================
    
    async def get_attendance_summary(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> dict:
        """Get attendance summary for a date range"""
        # Get all employees
        employees = await db.employees.find(
            {"company_id": company_id, "status": "active"},
            {"employee_id": 1, "first_name": 1, "last_name": 1, "_id": 0}
        ).to_list(1000)
        
        summary = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_employees": len(employees),
            "employees": []
        }
        
        for emp in employees:
            # Get clock events for employee in period
            events = await db.clock_events.find({
                "employee_id": emp["employee_id"],
                "timestamp": {
                    "$gte": datetime.combine(start_date, datetime.min.time()).isoformat(),
                    "$lte": datetime.combine(end_date, datetime.max.time()).isoformat()
                }
            }, {"_id": 0}).to_list(1000)
            
            # Count days worked
            work_days = set()
            total_hours = 0
            
            for event in events:
                if event["event_type"] == ClockEventType.CLOCK_IN.value:
                    work_days.add(event["timestamp"][:10])
            
            # Get approved timesheet hours
            timesheets = await db.timesheets.find({
                "employee_id": emp["employee_id"],
                "week_start_date": {"$gte": start_date.isoformat()},
                "week_end_date": {"$lte": end_date.isoformat()},
                "status": {"$in": [TimesheetStatus.APPROVED.value, TimesheetStatus.PAID.value]}
            }, {"_id": 0}).to_list(10)
            
            for ts in timesheets:
                total_hours += ts.get("total_hours", 0)
            
            summary["employees"].append({
                "employee_id": emp["employee_id"],
                "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}",
                "days_worked": len(work_days),
                "total_hours": round(total_hours, 2)
            })
        
        return summary


# Singleton instance
time_service = TimeSchedulingService()
