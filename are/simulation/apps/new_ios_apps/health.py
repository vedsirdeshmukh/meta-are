# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from are.simulation.apps.app import App
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import get_state_dict, type_check, uuid_hex


class MetricType(Enum):
    HEART_RATE = "Heart Rate"
    BLOOD_PRESSURE = "Blood Pressure"
    BLOOD_GLUCOSE = "Blood Glucose"
    WEIGHT = "Weight"
    HEIGHT = "Height"
    BODY_TEMPERATURE = "Body Temperature"
    OXYGEN_SATURATION = "Oxygen Saturation"
    STEPS = "Steps"
    SLEEP_HOURS = "Sleep Hours"
    WATER_INTAKE = "Water Intake"


class MedicationType(Enum):
    PRESCRIPTION = "Prescription"
    OVER_THE_COUNTER = "Over the Counter"
    SUPPLEMENT = "Supplement"


class HealthSharingCategory(Enum):
    WORKOUTS = "Workouts"
    ACTIVITY = "Activity"
    HEART = "Heart"
    MEDICATIONS = "Medications"
    CYCLE_TRACKING = "Cycle Tracking"
    MINDFULNESS = "Mindfulness"


class WorkoutType(Enum):
    RUNNING = "Running"
    WALKING = "Walking"
    CYCLING = "Cycling"
    SWIMMING = "Swimming"
    YOGA = "Yoga"
    STRENGTH_TRAINING = "Strength Training"
    HIIT = "HIIT"
    OTHER = "Other"


@dataclass
class HealthMetric:
    """Represents a health measurement or data point."""

    metric_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    metric_type: MetricType = MetricType.HEART_RATE
    value: float = 0.0
    unit: str = "bpm"
    timestamp: float = field(default_factory=time.time)
    source: str = "Manual Entry"  # e.g., "Apple Watch", "Manual Entry", "Blood Pressure Monitor"
    notes: str | None = None

    def __str__(self):
        return f"{self.metric_type.value}: {self.value} {self.unit}\nTimestamp: {time.ctime(self.timestamp)}\nSource: {self.source}"


@dataclass
class Medication:
    """Represents a medication with dosage and schedule."""

    medication_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Medication"
    medication_type: MedicationType = MedicationType.PRESCRIPTION
    dosage: str = "1 pill"
    frequency: str = "daily"  # e.g., "daily", "twice daily", "as needed"
    schedule_times: list[str] = field(default_factory=list)  # e.g., ["08:00", "20:00"]
    prescribing_doctor: str | None = None
    start_date: float | None = None
    end_date: float | None = None
    is_critical: bool = False  # For life-critical medications (e.g., insulin)
    purpose: str | None = None  # What condition it treats
    side_effects: list[str] = field(default_factory=list)
    is_active: bool = True

    def __str__(self):
        info = f"Medication: {self.name}\nType: {self.medication_type.value}\nDosage: {self.dosage}\nFrequency: {self.frequency}"

        if self.schedule_times:
            info += f"\nSchedule: {', '.join(self.schedule_times)}"
        if self.prescribing_doctor:
            info += f"\nPrescribed by: Dr. {self.prescribing_doctor}"
        if self.purpose:
            info += f"\nPurpose: {self.purpose}"
        if self.is_critical:
            info += "\n🚨 CRITICAL MEDICATION"
        if not self.is_active:
            info += "\n⚠️ Inactive"

        return info


@dataclass
class MedicalCondition:
    """Represents a medical condition or diagnosis."""

    condition_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Condition"
    diagnosis_date: float | None = None
    status: str = "Active"  # Active, Resolved, Managed
    severity: str = "Moderate"  # Mild, Moderate, Severe
    notes: str | None = None
    treating_doctor: str | None = None
    related_medications: list[str] = field(default_factory=list)  # medication_ids

    def __str__(self):
        info = f"Condition: {self.name}\nStatus: {self.status}\nSeverity: {self.severity}"

        if self.diagnosis_date:
            info += f"\nDiagnosed: {time.ctime(self.diagnosis_date)}"
        if self.treating_doctor:
            info += f"\nTreating Doctor: Dr. {self.treating_doctor}"
        if self.notes:
            info += f"\nNotes: {self.notes}"

        return info


@dataclass
class Appointment:
    """Represents a medical appointment."""

    appointment_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    doctor_name: str = "Doctor"
    specialty: str | None = None
    appointment_datetime: float = field(default_factory=time.time)
    location: str | None = None
    reason: str | None = None
    is_critical: bool = False  # For urgent or critical appointments
    notes: str | None = None
    status: str = "Scheduled"  # Scheduled, Completed, Cancelled, Missed

    def __str__(self):
        info = f"Appointment with Dr. {self.doctor_name}"
        if self.specialty:
            info += f" ({self.specialty})"
        info += f"\nDate/Time: {time.ctime(self.appointment_datetime)}\nStatus: {self.status}"

        if self.location:
            info += f"\nLocation: {self.location}"
        if self.reason:
            info += f"\nReason: {self.reason}"
        if self.is_critical:
            info += "\n🚨 CRITICAL APPOINTMENT"

        return info


@dataclass
class HealthShareInvitation:
    """Represents a Health Sharing invitation to share health data with someone."""

    invitation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    contact_id: str = ""  # Required: Contact ID from ContactsApp
    contact_name: str = "Contact"  # Display name (for convenience)
    enabled_categories: list[HealthSharingCategory] = field(default_factory=list)
    status: str = "Pending"  # Pending, Accepted, Declined
    created_date: float = field(default_factory=time.time)

    def __str__(self):
        info = f"Health Sharing with {self.contact_name}\n"
        info += f"Contact ID: {self.contact_id}\n"
        info += f"Status: {self.status}\n"
        info += f"Created: {time.ctime(self.created_date)}\n"

        if self.enabled_categories:
            categories_str = ", ".join([cat.value for cat in self.enabled_categories])
            info += f"Shared Categories: {categories_str}\n"
        else:
            info += "Shared Categories: None\n"

        return info


@dataclass
class Workout:
    """Represents a workout session."""

    workout_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    workout_type: WorkoutType = WorkoutType.RUNNING
    title: str = "Workout"
    start_time: float = field(default_factory=time.time)
    duration_minutes: float = 0.0
    distance: float | None = None  # in miles or km
    calories_burned: int | None = None
    average_heart_rate: int | None = None  # bpm
    max_heart_rate: int | None = None  # bpm
    has_route: bool = False
    notes: str | None = None

    def __str__(self):
        info = f"Workout: {self.title}\n"
        info += f"Type: {self.workout_type.value}\n"
        info += f"Start: {time.ctime(self.start_time)}\n"
        info += f"Duration: {self.duration_minutes} minutes\n"

        if self.distance:
            info += f"Distance: {self.distance} miles\n"
        if self.calories_burned:
            info += f"Calories: {self.calories_burned} kcal\n"
        if self.average_heart_rate:
            info += f"Avg Heart Rate: {self.average_heart_rate} bpm\n"
        if self.max_heart_rate:
            info += f"Max Heart Rate: {self.max_heart_rate} bpm\n"
        if self.has_route:
            info += "Route: Saved\n"
        if self.notes:
            info += f"Notes: {self.notes}\n"

        return info


@dataclass
class ActivitySummary:
    """Represents daily activity summary (rings)."""

    summary_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    date: str = ""  # YYYY-MM-DD format
    move_calories: int = 0  # Active calories burned
    move_goal: int = 600  # Move goal
    exercise_minutes: int = 0  # Exercise minutes
    exercise_goal: int = 30  # Exercise goal
    stand_hours: int = 0  # Stand hours
    stand_goal: int = 12  # Stand goal
    steps: int = 0
    distance: float = 0.0  # miles

    def __str__(self):
        info = f"Activity Summary: {self.date}\n"
        info += f"Move: {self.move_calories}/{self.move_goal} kcal\n"
        info += f"Exercise: {self.exercise_minutes}/{self.exercise_goal} min\n"
        info += f"Stand: {self.stand_hours}/{self.stand_goal} hrs\n"
        info += f"Steps: {self.steps}\n"
        info += f"Distance: {self.distance} miles\n"
        return info


@dataclass
class HeartRecord:
    """Represents an ECG or heart rhythm recording."""

    record_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    record_type: str = "ECG"  # ECG, Heart Rate, etc.
    classification: str = "Sinus Rhythm"  # e.g., "Sinus Rhythm", "AFib", "Inconclusive"
    recorded_date: float = field(default_factory=time.time)
    average_heart_rate: int | None = None
    provider: str | None = None  # Doctor who reviewed it
    notes: str | None = None
    exported_to_doctor: bool = False

    def __str__(self):
        info = f"Heart Record: {self.record_type}\n"
        info += f"Classification: {self.classification}\n"
        info += f"Date: {time.ctime(self.recorded_date)}\n"

        if self.average_heart_rate:
            info += f"Heart Rate: {self.average_heart_rate} bpm\n"
        if self.provider:
            info += f"Provider: {self.provider}\n"
        if self.exported_to_doctor:
            info += "✓ Exported to doctor\n"
        if self.notes:
            info += f"Notes: {self.notes}\n"

        return info


@dataclass
class ReproductiveHealth:
    """Represents cycle tracking and reproductive health data."""

    record_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    last_period_start: str | None = None  # YYYY-MM-DD
    cycle_length_days: int = 28
    period_length_days: int = 5
    predictions_enabled: bool = True
    notes: str | None = None

    def __str__(self):
        info = "Cycle Tracking\n"

        if self.last_period_start:
            info += f"Last Period: {self.last_period_start}\n"
        info += f"Cycle Length: {self.cycle_length_days} days\n"
        info += f"Period Length: {self.period_length_days} days\n"
        info += f"Predictions: {'Enabled' if self.predictions_enabled else 'Disabled'}\n"

        if self.notes:
            info += f"Notes: {self.notes}\n"

        return info


@dataclass
class MindfulnessSession:
    """Represents a mindfulness or meditation session."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    start_time: float = field(default_factory=time.time)
    duration_minutes: int = 5
    session_type: str = "Meditation"  # Meditation, Breathing, etc.
    notes: str | None = None

    def __str__(self):
        info = f"Mindfulness Session: {self.session_type}\n"
        info += f"Start: {time.ctime(self.start_time)}\n"
        info += f"Duration: {self.duration_minutes} minutes\n"

        if self.notes:
            info += f"Notes: {self.notes}\n"

        return info


@dataclass
class HealthApp(App):
    """
    Health tracking and medical records application.

    Manages health metrics, medications, medical conditions, and appointments.
    Provides comprehensive health monitoring and medical information management.

    Key Features:
        - Health Metrics: Track various health measurements (heart rate, blood pressure, etc.)
        - Medication Management: Track medications with schedules and reminders
        - Medical Conditions: Record and monitor medical conditions
        - Appointments: Manage medical appointments
        - Critical Health Data: Mark critical medications and appointments
        - Data Export: Export health data for sharing with doctors

    Notes:
        - Some medications may be life-critical (e.g., insulin for diabetes)
        - Critical appointments should not be missed or deleted
        - Health metrics can come from various sources (Apple Watch, manual entry, medical devices)
    """

    name: str | None = None
    metrics: dict[str, HealthMetric] = field(default_factory=dict)
    medications: dict[str, Medication] = field(default_factory=dict)
    conditions: dict[str, MedicalCondition] = field(default_factory=dict)
    appointments: dict[str, Appointment] = field(default_factory=dict)
    emergency_contact: str | None = None
    blood_type: str | None = None
    allergies: list[str] = field(default_factory=list)

    # Health Sharing
    health_shares: dict[str, HealthShareInvitation] = field(default_factory=dict)

    # Activity & Fitness Data
    workouts: dict[str, Workout] = field(default_factory=dict)
    activity_summaries: dict[str, ActivitySummary] = field(default_factory=dict)

    # Heart Health
    heart_records: dict[str, HeartRecord] = field(default_factory=dict)

    # Reproductive Health
    cycle_tracking: ReproductiveHealth | None = None

    # Mindfulness
    mindfulness_sessions: dict[str, MindfulnessSession] = field(default_factory=dict)

    def __post_init__(self):
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(
            self,
            ["metrics", "medications", "conditions", "appointments", "emergency_contact", "blood_type", "allergies",
             "health_shares", "workouts", "activity_summaries", "heart_records", "cycle_tracking", "mindfulness_sessions"],
        )

    def load_state(self, state_dict: dict[str, Any]):
        self.metrics = {k: HealthMetric(**v) for k, v in state_dict.get("metrics", {}).items()}
        self.medications = {k: Medication(**v) for k, v in state_dict.get("medications", {}).items()}
        self.conditions = {k: MedicalCondition(**v) for k, v in state_dict.get("conditions", {}).items()}
        self.appointments = {k: Appointment(**v) for k, v in state_dict.get("appointments", {}).items()}
        self.emergency_contact = state_dict.get("emergency_contact")
        self.blood_type = state_dict.get("blood_type")
        self.allergies = state_dict.get("allergies", [])

        self.health_shares = {k: HealthShareInvitation(**v) for k, v in state_dict.get("health_shares", {}).items()}
        self.workouts = {k: Workout(**v) for k, v in state_dict.get("workouts", {}).items()}
        self.activity_summaries = {k: ActivitySummary(**v) for k, v in state_dict.get("activity_summaries", {}).items()}
        self.heart_records = {k: HeartRecord(**v) for k, v in state_dict.get("heart_records", {}).items()}

        cycle_data = state_dict.get("cycle_tracking")
        self.cycle_tracking = ReproductiveHealth(**cycle_data) if cycle_data else None

        self.mindfulness_sessions = {k: MindfulnessSession(**v) for k, v in state_dict.get("mindfulness_sessions", {}).items()}

    def reset(self):
        super().reset()
        self.metrics = {}
        self.medications = {}
        self.conditions = {}
        self.appointments = {}
        self.allergies = []
        self.health_shares = {}
        self.workouts = {}
        self.activity_summaries = {}
        self.heart_records = {}
        self.cycle_tracking = None
        self.mindfulness_sessions = {}

    # Health Metrics

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def log_health_metric(
        self,
        metric_type: str,
        value: float,
        unit: str,
        source: str = "Manual Entry",
        notes: str | None = None,
    ) -> str:
        """
        Log a health metric measurement.

        :param metric_type: Type of metric. Options: Heart Rate, Blood Pressure, Blood Glucose, Weight, Height, Body Temperature, Oxygen Saturation, Steps, Sleep Hours, Water Intake
        :param value: Measurement value
        :param unit: Unit of measurement (e.g., "bpm", "mmHg", "mg/dL", "lbs", "°F", "%")
        :param source: Source of the measurement (e.g., "Apple Watch", "Manual Entry", "Blood Pressure Monitor")
        :param notes: Optional notes about the measurement
        :returns: metric_id of the logged metric
        """
        metric_type_enum = MetricType[metric_type.upper().replace(" ", "_")]

        metric = HealthMetric(
            metric_id=uuid_hex(self.rng),
            metric_type=metric_type_enum,
            value=value,
            unit=unit,
            timestamp=self.time_manager.time(),
            source=source,
            notes=notes,
        )

        self.metrics[metric.metric_id] = metric
        return metric.metric_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_recent_metrics(self, metric_type: str | None = None, limit: int = 10) -> str:
        """
        Get recent health metrics, optionally filtered by type.

        :param metric_type: Optional filter by metric type
        :param limit: Maximum number of metrics to return (default 10)
        :returns: String representation of recent metrics
        """
        filtered_metrics = list(self.metrics.values())

        if metric_type:
            metric_type_enum = MetricType[metric_type.upper().replace(" ", "_")]
            filtered_metrics = [m for m in filtered_metrics if m.metric_type == metric_type_enum]

        # Sort by timestamp descending
        filtered_metrics.sort(key=lambda m: m.timestamp, reverse=True)
        filtered_metrics = filtered_metrics[:limit]

        if not filtered_metrics:
            return "No metrics found."

        result = f"Recent health metrics ({len(filtered_metrics)}):\n\n"
        for metric in filtered_metrics:
            result += str(metric) + "\n" + "-" * 40 + "\n"

        return result

    # Medication Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_medication(
        self,
        name: str,
        dosage: str,
        frequency: str,
        schedule_times: list[str] | None = None,
        medication_type: str = "Prescription",
        is_critical: bool = False,
        purpose: str | None = None,
    ) -> str:
        """
        Add a medication to track.

        :param name: Name of the medication
        :param dosage: Dosage information (e.g., "10mg", "1 pill")
        :param frequency: How often to take (e.g., "daily", "twice daily", "as needed")
        :param schedule_times: List of times to take medication (e.g., ["08:00", "20:00"])
        :param medication_type: Type of medication. Options: Prescription, Over the Counter, Supplement
        :param is_critical: Whether this is a life-critical medication (e.g., insulin)
        :param purpose: What condition the medication treats
        :returns: medication_id of the added medication
        """
        if schedule_times is None:
            schedule_times = []

        medication_type_enum = MedicationType[medication_type.upper().replace(" ", "_")]

        medication = Medication(
            medication_id=uuid_hex(self.rng),
            name=name,
            medication_type=medication_type_enum,
            dosage=dosage,
            frequency=frequency,
            schedule_times=schedule_times,
            start_date=self.time_manager.time(),
            is_critical=is_critical,
            purpose=purpose,
        )

        self.medications[medication.medication_id] = medication
        return medication.medication_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_medications(self, include_inactive: bool = False) -> str:
        """
        List all medications.

        :param include_inactive: Whether to include inactive medications
        :returns: String representation of all medications
        """
        filtered_meds = [m for m in self.medications.values() if include_inactive or m.is_active]

        if not filtered_meds:
            return "No medications found."

        result = f"Medications ({len(filtered_meds)}):\n\n"
        for med in filtered_meds:
            result += str(med) + "\n" + "-" * 40 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def stop_medication(self, medication_id: str) -> str:
        """
        Mark a medication as inactive/stopped.

        :param medication_id: ID of the medication to stop
        :returns: Success or error message
        """
        if medication_id not in self.medications:
            return f"Medication with ID {medication_id} not found."

        med = self.medications[medication_id]

        if med.is_critical:
            return f"⚠️ WARNING: {med.name} is a CRITICAL medication. Stopping this medication could be dangerous. Please consult a doctor before stopping."

        med.is_active = False
        med.end_date = self.time_manager.time()

        return f"✓ Medication '{med.name}' marked as inactive."

    # Medical Conditions

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_medical_condition(
        self,
        name: str,
        status: str = "Active",
        severity: str = "Moderate",
        notes: str | None = None,
    ) -> str:
        """
        Add a medical condition.

        :param name: Name of the condition
        :param status: Status of condition. Options: Active, Resolved, Managed
        :param severity: Severity level. Options: Mild, Moderate, Severe
        :param notes: Additional notes about the condition
        :returns: condition_id of the added condition
        """
        condition = MedicalCondition(
            condition_id=uuid_hex(self.rng),
            name=name,
            diagnosis_date=self.time_manager.time(),
            status=status,
            severity=severity,
            notes=notes,
        )

        self.conditions[condition.condition_id] = condition
        return condition.condition_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_medical_conditions(self, status: str | None = None) -> str:
        """
        List medical conditions, optionally filtered by status.

        :param status: Optional filter by status (Active, Resolved, Managed)
        :returns: String representation of medical conditions
        """
        filtered_conditions = list(self.conditions.values())

        if status:
            filtered_conditions = [c for c in filtered_conditions if c.status.lower() == status.lower()]

        if not filtered_conditions:
            return "No medical conditions found."

        result = f"Medical Conditions ({len(filtered_conditions)}):\n\n"
        for condition in filtered_conditions:
            result += str(condition) + "\n" + "-" * 40 + "\n"

        return result

    # Appointments

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def schedule_appointment(
        self,
        doctor_name: str,
        appointment_datetime: str,
        specialty: str | None = None,
        location: str | None = None,
        reason: str | None = None,
        is_critical: bool = False,
    ) -> str:
        """
        Schedule a medical appointment.

        :param doctor_name: Name of the doctor
        :param appointment_datetime: Date and time in format "YYYY-MM-DD HH:MM:SS"
        :param specialty: Doctor's specialty (e.g., "Cardiologist", "Oncologist")
        :param location: Location of appointment
        :param reason: Reason for appointment
        :param is_critical: Whether this is a critical/urgent appointment
        :returns: appointment_id of the scheduled appointment
        """
        from datetime import datetime, timezone

        # Parse datetime
        dt = datetime.strptime(appointment_datetime, "%Y-%m-%d %H:%M:%S")
        timestamp = dt.replace(tzinfo=timezone.utc).timestamp()

        appointment = Appointment(
            appointment_id=uuid_hex(self.rng),
            doctor_name=doctor_name,
            specialty=specialty,
            appointment_datetime=timestamp,
            location=location,
            reason=reason,
            is_critical=is_critical,
        )

        self.appointments[appointment.appointment_id] = appointment
        return appointment.appointment_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_appointments(self, upcoming_only: bool = True) -> str:
        """
        List medical appointments.

        :param upcoming_only: If True, only show upcoming appointments
        :returns: String representation of appointments
        """
        filtered_appointments = list(self.appointments.values())

        if upcoming_only:
            current_time = self.time_manager.time()
            filtered_appointments = [
                a for a in filtered_appointments if a.appointment_datetime > current_time and a.status == "Scheduled"
            ]

        # Sort by datetime
        filtered_appointments.sort(key=lambda a: a.appointment_datetime)

        if not filtered_appointments:
            return "No appointments found."

        result = f"Appointments ({len(filtered_appointments)}):\n\n"
        for appointment in filtered_appointments:
            result += str(appointment) + "\n" + "-" * 40 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def cancel_appointment(self, appointment_id: str) -> str:
        """
        Cancel a medical appointment.

        :param appointment_id: ID of the appointment to cancel
        :returns: Success or error message
        """
        if appointment_id not in self.appointments:
            return f"Appointment with ID {appointment_id} not found."

        appointment = self.appointments[appointment_id]

        if appointment.is_critical:
            return f"⚠️ WARNING: This is a CRITICAL appointment with Dr. {appointment.doctor_name}. Cancelling may have serious health consequences. Please reschedule immediately if cancelled."

        appointment.status = "Cancelled"
        return f"✓ Appointment with Dr. {appointment.doctor_name} cancelled."

    # Health Profile

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_emergency_contact(self, contact_name: str) -> str:
        """
        Set emergency contact information.

        :param contact_name: Name of emergency contact
        :returns: Success message
        """
        self.emergency_contact = contact_name
        return f"✓ Emergency contact set to {contact_name}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_allergy(self, allergy: str) -> str:
        """
        Add an allergy to health profile.

        :param allergy: Allergy description (e.g., "Penicillin", "Peanuts")
        :returns: Success message
        """
        if allergy not in self.allergies:
            self.allergies.append(allergy)
            return f"✓ Allergy '{allergy}' added to health profile."
        return f"Allergy '{allergy}' already exists in health profile."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_health_summary(self) -> str:
        """
        Get a summary of health profile and recent data.

        :returns: Comprehensive health summary
        """
        summary = "=== HEALTH SUMMARY ===\n\n"

        if self.blood_type:
            summary += f"Blood Type: {self.blood_type}\n"

        if self.emergency_contact:
            summary += f"Emergency Contact: {self.emergency_contact}\n"

        if self.allergies:
            summary += f"Allergies: {', '.join(self.allergies)}\n"

        summary += f"\nActive Conditions: {len([c for c in self.conditions.values() if c.status == 'Active'])}\n"
        summary += f"Active Medications: {len([m for m in self.medications.values() if m.is_active])}\n"

        critical_meds = [m for m in self.medications.values() if m.is_critical and m.is_active]
        if critical_meds:
            summary += f"\n⚠️ CRITICAL MEDICATIONS: {len(critical_meds)}\n"
            for med in critical_meds:
                summary += f"  - {med.name}: {med.dosage} {med.frequency}\n"

        upcoming_appointments = [
            a
            for a in self.appointments.values()
            if a.appointment_datetime > self.time_manager.time() and a.status == "Scheduled"
        ]
        summary += f"\nUpcoming Appointments: {len(upcoming_appointments)}\n"

        return summary

    # Health Sharing

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def setup_health_sharing(
        self,
        contact_id: str,
        categories: list[str],
    ) -> str:
        """
        Set up Health Sharing with a contact to share specific health data categories.

        IMPORTANT: You must first use ContactsApp to search for the contact and get their contact_id.
        Use list_contacts(search_query="name") or search_contacts(query="name") to find the contact_id.

        :param contact_id: Contact ID from ContactsApp (required). Must be obtained by searching contacts first.
        :param categories: List of categories to share. Options: Workouts, Activity, Heart, Medications, Cycle Tracking, Mindfulness
        :returns: invitation_id of the health sharing invitation
        """
        # Validate contact_id is provided
        if not contact_id or contact_id.strip() == "":
            return "Error: contact_id is required. Please search contacts using ContactsApp (list_contacts or search_contacts) to get the contact_id first."

        # Note: We don't validate against ContactsApp here because apps should be independent.
        # The agent is responsible for providing a valid contact_id from ContactsApp.
        # Use contact_id as display name for now (will show in invitation)
        contact_name = f"Contact {contact_id}"

        # Parse categories
        enabled_categories = []
        for cat_str in categories:
            try:
                cat_enum = HealthSharingCategory[cat_str.upper().replace(" ", "_")]
                enabled_categories.append(cat_enum)
            except KeyError:
                return f"Invalid category: '{cat_str}'. Valid options: Workouts, Activity, Heart, Medications, Cycle Tracking, Mindfulness"

        invitation = HealthShareInvitation(
            invitation_id=uuid_hex(self.rng),
            contact_id=contact_id,
            contact_name=contact_name if contact_name else f"Contact {contact_id}",
            enabled_categories=enabled_categories,
            status="Pending",
            created_date=self.time_manager.time(),
        )

        self.health_shares[invitation.invitation_id] = invitation

        categories_str = ", ".join([cat.value for cat in enabled_categories])
        return f"✓ Health Sharing invitation created for {invitation.contact_name} (ID: {contact_id}) with categories: {categories_str}\nInvitation ID: {invitation.invitation_id}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_health_shares(self) -> str:
        """
        List all Health Sharing invitations and active shares.

        :returns: String representation of all health shares
        """
        if not self.health_shares:
            return "No Health Sharing invitations or active shares."

        result = f"Health Sharing ({len(self.health_shares)}):\n\n"
        for share in self.health_shares.values():
            result += str(share) + "-" * 50 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_health_sharing_categories(
        self,
        invitation_id: str,
        categories: list[str],
    ) -> str:
        """
        Update which categories are shared in an existing Health Sharing invitation.

        :param invitation_id: ID of the invitation to update
        :param categories: New list of categories to share. Options: Workouts, Activity, Heart, Medications, Cycle Tracking, Mindfulness
        :returns: Success or error message
        """
        if invitation_id not in self.health_shares:
            return f"Health Sharing invitation with ID {invitation_id} not found."

        # Parse categories
        enabled_categories = []
        for cat_str in categories:
            try:
                cat_enum = HealthSharingCategory[cat_str.upper().replace(" ", "_")]
                enabled_categories.append(cat_enum)
            except KeyError:
                return f"Invalid category: '{cat_str}'. Valid options: Workouts, Activity, Heart, Medications, Cycle Tracking, Mindfulness"

        share = self.health_shares[invitation_id]
        share.enabled_categories = enabled_categories

        categories_str = ", ".join([cat.value for cat in enabled_categories])
        return f"✓ Updated Health Sharing for {share.contact_name}. New categories: {categories_str}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def stop_health_sharing(self, invitation_id: str) -> str:
        """
        Stop sharing health data with a contact.

        :param invitation_id: ID of the health sharing invitation to stop
        :returns: Success or error message
        """
        if invitation_id not in self.health_shares:
            return f"Health Sharing invitation with ID {invitation_id} not found."

        share = self.health_shares[invitation_id]
        contact_name = share.contact_name
        del self.health_shares[invitation_id]

        return f"✓ Stopped Health Sharing with {contact_name}."

    # Workouts

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_workout(
        self,
        title: str,
        workout_type: str,
        duration_minutes: float,
        distance: float | None = None,
        calories_burned: int | None = None,
        average_heart_rate: int | None = None,
        max_heart_rate: int | None = None,
        has_route: bool = False,
        notes: str | None = None,
    ) -> str:
        """
        Add a workout session.

        :param title: Title of the workout
        :param workout_type: Type of workout. Options: Running, Walking, Cycling, Swimming, Yoga, Strength Training, HIIT, Other
        :param duration_minutes: Duration in minutes
        :param distance: Distance covered (optional, in miles)
        :param calories_burned: Calories burned (optional)
        :param average_heart_rate: Average heart rate in bpm (optional)
        :param max_heart_rate: Maximum heart rate in bpm (optional)
        :param has_route: Whether a route was recorded
        :param notes: Additional notes (optional)
        :returns: workout_id of the added workout
        """
        workout_type_enum = WorkoutType[workout_type.upper().replace(" ", "_")]

        workout = Workout(
            workout_id=uuid_hex(self.rng),
            workout_type=workout_type_enum,
            title=title,
            start_time=self.time_manager.time(),
            duration_minutes=duration_minutes,
            distance=distance,
            calories_burned=calories_burned,
            average_heart_rate=average_heart_rate,
            max_heart_rate=max_heart_rate,
            has_route=has_route,
            notes=notes,
        )

        self.workouts[workout.workout_id] = workout
        return workout.workout_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_workouts(self, workout_type: str | None = None, limit: int = 10) -> str:
        """
        List recent workouts, optionally filtered by type.

        :param workout_type: Optional filter by workout type
        :param limit: Maximum number of workouts to return (default 10)
        :returns: String representation of workouts
        """
        filtered_workouts = list(self.workouts.values())

        if workout_type:
            workout_type_enum = WorkoutType[workout_type.upper().replace(" ", "_")]
            filtered_workouts = [w for w in filtered_workouts if w.workout_type == workout_type_enum]

        # Sort by start time descending
        filtered_workouts.sort(key=lambda w: w.start_time, reverse=True)
        filtered_workouts = filtered_workouts[:limit]

        if not filtered_workouts:
            return "No workouts found."

        result = f"Workouts ({len(filtered_workouts)}):\n\n"
        for workout in filtered_workouts:
            result += str(workout) + "-" * 50 + "\n"

        return result

    # Activity Summaries

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_activity_summary(
        self,
        date: str,
        move_calories: int,
        move_goal: int = 600,
        exercise_minutes: int = 0,
        exercise_goal: int = 30,
        stand_hours: int = 0,
        stand_goal: int = 12,
        steps: int = 0,
        distance: float = 0.0,
    ) -> str:
        """
        Add a daily activity summary (activity rings).

        :param date: Date in YYYY-MM-DD format
        :param move_calories: Active calories burned
        :param move_goal: Move goal for the day
        :param exercise_minutes: Exercise minutes completed
        :param exercise_goal: Exercise goal for the day
        :param stand_hours: Stand hours completed
        :param stand_goal: Stand goal for the day
        :param steps: Total steps
        :param distance: Total distance in miles
        :returns: summary_id of the activity summary
        """
        summary = ActivitySummary(
            summary_id=uuid_hex(self.rng),
            date=date,
            move_calories=move_calories,
            move_goal=move_goal,
            exercise_minutes=exercise_minutes,
            exercise_goal=exercise_goal,
            stand_hours=stand_hours,
            stand_goal=stand_goal,
            steps=steps,
            distance=distance,
        )

        self.activity_summaries[summary.summary_id] = summary
        return summary.summary_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_activity_summary(self, date: str | None = None) -> str:
        """
        Get activity summary for a specific date or recent summaries.

        :param date: Optional date in YYYY-MM-DD format. If not provided, shows recent summaries.
        :returns: String representation of activity summary
        """
        if date:
            # Find summary for specific date
            for summary in self.activity_summaries.values():
                if summary.date == date:
                    return str(summary)
            return f"No activity summary found for {date}."
        else:
            # Show recent summaries
            if not self.activity_summaries:
                return "No activity summaries found."

            summaries = list(self.activity_summaries.values())
            summaries.sort(key=lambda s: s.date, reverse=True)
            summaries = summaries[:7]  # Last 7 days

            result = f"Activity Summaries ({len(summaries)}):\n\n"
            for summary in summaries:
                result += str(summary) + "-" * 50 + "\n"

            return result

    # Heart Records

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_heart_record(
        self,
        classification: str,
        record_type: str = "ECG",
        average_heart_rate: int | None = None,
        provider: str | None = None,
        notes: str | None = None,
    ) -> str:
        """
        Add an ECG or heart rhythm recording.

        :param classification: Classification result (e.g., "Sinus Rhythm", "AFib", "Inconclusive")
        :param record_type: Type of record (default: ECG)
        :param average_heart_rate: Average heart rate in bpm (optional)
        :param provider: Doctor who reviewed the recording (optional)
        :param notes: Additional notes (optional)
        :returns: record_id of the heart record
        """
        record = HeartRecord(
            record_id=uuid_hex(self.rng),
            record_type=record_type,
            classification=classification,
            recorded_date=self.time_manager.time(),
            average_heart_rate=average_heart_rate,
            provider=provider,
            notes=notes,
        )

        self.heart_records[record.record_id] = record
        return record.record_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_heart_records(self, limit: int = 10) -> str:
        """
        List recent heart records.

        :param limit: Maximum number of records to return (default 10)
        :returns: String representation of heart records
        """
        if not self.heart_records:
            return "No heart records found."

        records = list(self.heart_records.values())
        records.sort(key=lambda r: r.recorded_date, reverse=True)
        records = records[:limit]

        result = f"Heart Records ({len(records)}):\n\n"
        for record in records:
            result += str(record) + "-" * 50 + "\n"

        return result

    # Cycle Tracking

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def setup_cycle_tracking(
        self,
        last_period_start: str,
        cycle_length_days: int = 28,
        period_length_days: int = 5,
        predictions_enabled: bool = True,
    ) -> str:
        """
        Set up or update cycle tracking.

        :param last_period_start: Last period start date in YYYY-MM-DD format
        :param cycle_length_days: Average cycle length in days
        :param period_length_days: Average period length in days
        :param predictions_enabled: Whether to enable predictions
        :returns: Success message
        """
        self.cycle_tracking = ReproductiveHealth(
            record_id=uuid_hex(self.rng),
            last_period_start=last_period_start,
            cycle_length_days=cycle_length_days,
            period_length_days=period_length_days,
            predictions_enabled=predictions_enabled,
        )

        return "✓ Cycle tracking set up successfully."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_cycle_tracking(self) -> str:
        """
        Get cycle tracking information.

        :returns: String representation of cycle tracking data
        """
        if not self.cycle_tracking:
            return "Cycle tracking is not set up."

        return str(self.cycle_tracking)

    # Mindfulness

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_mindfulness_session(
        self,
        duration_minutes: int,
        session_type: str = "Meditation",
        notes: str | None = None,
    ) -> str:
        """
        Add a mindfulness or meditation session.

        :param duration_minutes: Duration in minutes
        :param session_type: Type of session (e.g., Meditation, Breathing)
        :param notes: Additional notes (optional)
        :returns: session_id of the mindfulness session
        """
        session = MindfulnessSession(
            session_id=uuid_hex(self.rng),
            start_time=self.time_manager.time(),
            duration_minutes=duration_minutes,
            session_type=session_type,
            notes=notes,
        )

        self.mindfulness_sessions[session.session_id] = session
        return session.session_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_mindfulness_sessions(self, limit: int = 10) -> str:
        """
        List recent mindfulness sessions.

        :param limit: Maximum number of sessions to return (default 10)
        :returns: String representation of mindfulness sessions
        """
        if not self.mindfulness_sessions:
            return "No mindfulness sessions found."

        sessions = list(self.mindfulness_sessions.values())
        sessions.sort(key=lambda s: s.start_time, reverse=True)
        sessions = sessions[:limit]

        result = f"Mindfulness Sessions ({len(sessions)}):\n\n"
        for session in sessions:
            result += str(session) + "-" * 50 + "\n"

        return result
