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


class WorkoutType(Enum):
    RUNNING = "Running"
    WALKING = "Walking"
    CYCLING = "Cycling"
    SWIMMING = "Swimming"
    YOGA = "Yoga"
    STRENGTH_TRAINING = "Strength Training"
    HIIT = "HIIT"
    PILATES = "Pilates"
    DANCE = "Dance"
    HIKING = "Hiking"
    ROWING = "Rowing"
    ELLIPTICAL = "Elliptical"
    STAIR_CLIMBING = "Stair Climbing"
    MARTIAL_ARTS = "Martial Arts"
    SPORTS = "Sports"
    OTHER = "Other"


class IntensityLevel(Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    VIGOROUS = "Vigorous"


class GoalType(Enum):
    WEIGHT_LOSS = "Weight Loss"
    MUSCLE_GAIN = "Muscle Gain"
    ENDURANCE = "Endurance"
    FLEXIBILITY = "Flexibility"
    GENERAL_FITNESS = "General Fitness"
    STRESS_REDUCTION = "Stress Reduction"


@dataclass
class Workout:
    """Represents a completed workout session."""

    workout_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    workout_type: WorkoutType = WorkoutType.RUNNING
    start_time: float = field(default_factory=time.time)
    end_time: float = field(default_factory=time.time)
    duration_minutes: float = 0.0  # Total duration in minutes

    # Metrics
    distance: float | None = None  # In miles or km
    calories_burned: int | None = None
    average_heart_rate: int | None = None  # bpm
    max_heart_rate: int | None = None  # bpm
    steps: int | None = None
    elevation_gain: float | None = None  # In feet or meters

    # Additional details
    intensity: IntensityLevel = IntensityLevel.MODERATE
    location: str | None = None
    notes: str | None = None
    weather_conditions: str | None = None

    # Performance metrics
    splits: list[dict[str, Any]] = field(default_factory=list)  # For running/cycling splits
    route_name: str | None = None

    def __post_init__(self):
        if self.duration_minutes == 0.0 and self.end_time > self.start_time:
            self.duration_minutes = (self.end_time - self.start_time) / 60.0

    def __str__(self):
        info = f"Workout: {self.workout_type.value}\n"
        info += f"Date: {time.ctime(self.start_time)}\n"
        info += f"Duration: {self.duration_minutes:.1f} minutes\n"
        info += f"Intensity: {self.intensity.value}\n"

        if self.distance:
            info += f"Distance: {self.distance:.2f} miles\n"
        if self.calories_burned:
            info += f"Calories: {self.calories_burned}\n"
        if self.average_heart_rate:
            info += f"Avg Heart Rate: {self.average_heart_rate} bpm\n"
        if self.steps:
            info += f"Steps: {self.steps:,}\n"
        if self.location:
            info += f"Location: {self.location}\n"
        if self.notes:
            info += f"Notes: {self.notes}\n"

        return info


@dataclass
class FitnessGoal:
    """Represents a fitness goal."""

    goal_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Fitness Goal"
    goal_type: GoalType = GoalType.GENERAL_FITNESS
    target_value: float = 0.0
    current_value: float = 0.0
    unit: str = "workouts"  # e.g., "workouts", "minutes", "miles", "lbs"
    start_date: float = field(default_factory=time.time)
    target_date: float | None = None
    is_active: bool = True
    frequency: str | None = None  # e.g., "3 times per week", "daily"
    notes: str | None = None

    @property
    def progress_percentage(self) -> float:
        """Calculate progress as percentage."""
        if self.target_value == 0:
            return 0.0
        return min(100.0, (self.current_value / self.target_value) * 100.0)

    def __str__(self):
        info = f"Goal: {self.name}\n"
        info += f"Type: {self.goal_type.value}\n"
        info += f"Progress: {self.current_value}/{self.target_value} {self.unit} ({self.progress_percentage:.1f}%)\n"
        info += f"Status: {'Active' if self.is_active else 'Completed/Inactive'}\n"

        if self.target_date:
            info += f"Target Date: {time.ctime(self.target_date)}\n"
        if self.frequency:
            info += f"Frequency: {self.frequency}\n"
        if self.notes:
            info += f"Notes: {self.notes}\n"

        return info


@dataclass
class WorkoutPlan:
    """Represents a structured workout plan."""

    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Workout Plan"
    description: str | None = None
    duration_weeks: int = 4
    difficulty_level: str = "Beginner"  # Beginner, Intermediate, Advanced
    workouts_per_week: int = 3
    focus_areas: list[str] = field(default_factory=list)  # e.g., ["cardio", "strength", "flexibility"]
    scheduled_workouts: list[dict[str, Any]] = field(default_factory=list)  # Daily workout schedule
    is_active: bool = False
    created_date: float = field(default_factory=time.time)
    started_date: float | None = None

    def __str__(self):
        info = f"Plan: {self.name}\n"
        info += f"Duration: {self.duration_weeks} weeks\n"
        info += f"Difficulty: {self.difficulty_level}\n"
        info += f"Frequency: {self.workouts_per_week} workouts/week\n"
        info += f"Status: {'Active' if self.is_active else 'Inactive'}\n"

        if self.focus_areas:
            info += f"Focus: {', '.join(self.focus_areas)}\n"
        if self.description:
            info += f"Description: {self.description}\n"

        return info


@dataclass
class ActivityRing:
    """Represents daily activity rings (Move, Exercise, Stand)."""

    date: float = field(default_factory=time.time)

    # Move ring (active calories)
    move_goal: int = 500  # calories
    move_current: int = 0

    # Exercise ring (minutes of brisk activity)
    exercise_goal: int = 30  # minutes
    exercise_current: int = 0

    # Stand ring (hours stood)
    stand_goal: int = 12  # hours
    stand_current: int = 0

    @property
    def move_percentage(self) -> float:
        return min(100.0, (self.move_current / self.move_goal) * 100.0)

    @property
    def exercise_percentage(self) -> float:
        return min(100.0, (self.exercise_current / self.exercise_goal) * 100.0)

    @property
    def stand_percentage(self) -> float:
        return min(100.0, (self.stand_current / self.stand_goal) * 100.0)

    @property
    def all_rings_closed(self) -> bool:
        return self.move_percentage >= 100 and self.exercise_percentage >= 100 and self.stand_percentage >= 100

    def __str__(self):
        info = f"Activity Rings for {time.ctime(self.date)}\n"
        info += f"🔴 Move: {self.move_current}/{self.move_goal} cal ({self.move_percentage:.1f}%)\n"
        info += f"🟢 Exercise: {self.exercise_current}/{self.exercise_goal} min ({self.exercise_percentage:.1f}%)\n"
        info += f"🔵 Stand: {self.stand_current}/{self.stand_goal} hrs ({self.stand_percentage:.1f}%)\n"

        if self.all_rings_closed:
            info += "✨ All rings closed!\n"

        return info


@dataclass
class PersonalRecord:
    """Represents a personal fitness record."""

    record_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    achievement_name: str = "Personal Record"
    workout_type: WorkoutType = WorkoutType.RUNNING
    metric_name: str = "Distance"  # e.g., "Distance", "Time", "Weight", "Reps"
    value: float = 0.0
    unit: str = "miles"
    date_achieved: float = field(default_factory=time.time)
    previous_record: float | None = None
    notes: str | None = None

    def __str__(self):
        info = f"🏆 {self.achievement_name}\n"
        info += f"Type: {self.workout_type.value}\n"
        info += f"Record: {self.value} {self.unit} ({self.metric_name})\n"
        info += f"Date: {time.ctime(self.date_achieved)}\n"

        if self.previous_record:
            improvement = self.value - self.previous_record
            info += f"Previous: {self.previous_record} {self.unit} (Improvement: +{improvement:.2f})\n"

        return info


@dataclass
class FitnessApp(App):
    """
    Fitness and activity tracking application.

    Manages workouts, fitness goals, activity rings, workout plans, and personal records.
    Tracks various exercise types and provides comprehensive fitness monitoring.

    Key Features:
        - Workout Tracking: Log various types of workouts with detailed metrics
        - Activity Rings: Daily Move, Exercise, and Stand goals (Apple Watch style)
        - Fitness Goals: Set and track progress towards fitness objectives
        - Workout Plans: Create and follow structured training programs
        - Personal Records: Track personal bests and achievements
        - Statistics: View trends, averages, and progress over time
        - Multi-User Support: Track fitness for different people (e.g., family members)

    Notes:
        - Workouts can include distance, duration, calories, heart rate, and more
        - Activity rings track daily activity across three dimensions
        - Goals can be short-term or long-term with progress tracking
        - Personal records are automatically tracked when new bests are achieved
    """

    name: str | None = None
    workouts: dict[str, Workout] = field(default_factory=dict)
    goals: dict[str, FitnessGoal] = field(default_factory=dict)
    plans: dict[str, WorkoutPlan] = field(default_factory=dict)
    activity_rings: dict[str, ActivityRing] = field(default_factory=dict)  # date string -> ActivityRing
    personal_records: dict[str, PersonalRecord] = field(default_factory=dict)

    # User profile
    age: int | None = None
    weight: float | None = None  # lbs
    height: float | None = None  # inches
    fitness_level: str = "Intermediate"  # Beginner, Intermediate, Advanced

    def __post_init__(self):
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(
            self,
            ["workouts", "goals", "plans", "activity_rings", "personal_records", "age", "weight", "height", "fitness_level"],
        )

    def load_state(self, state_dict: dict[str, Any]):
        self.workouts = {k: Workout(**v) for k, v in state_dict.get("workouts", {}).items()}
        self.goals = {k: FitnessGoal(**v) for k, v in state_dict.get("goals", {}).items()}
        self.plans = {k: WorkoutPlan(**v) for k, v in state_dict.get("plans", {}).items()}
        self.activity_rings = {k: ActivityRing(**v) for k, v in state_dict.get("activity_rings", {}).items()}
        self.personal_records = {k: PersonalRecord(**v) for k, v in state_dict.get("personal_records", {}).items()}
        self.age = state_dict.get("age")
        self.weight = state_dict.get("weight")
        self.height = state_dict.get("height")
        self.fitness_level = state_dict.get("fitness_level", "Intermediate")

    def reset(self):
        super().reset()
        self.workouts = {}
        self.goals = {}
        self.plans = {}
        self.activity_rings = {}
        self.personal_records = {}

    # Workout Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def log_workout(
        self,
        workout_type: str,
        duration_minutes: float,
        intensity: str = "Moderate",
        distance: float | None = None,
        calories_burned: int | None = None,
        average_heart_rate: int | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> str:
        """
        Log a completed workout.

        :param workout_type: Type of workout. Options: Running, Walking, Cycling, Swimming, Yoga, Strength Training, HIIT, Pilates, Dance, Hiking, Rowing, Elliptical, Stair Climbing, Martial Arts, Sports, Other
        :param duration_minutes: Duration of workout in minutes
        :param intensity: Intensity level. Options: Low, Moderate, High, Vigorous
        :param distance: Distance covered (in miles)
        :param calories_burned: Estimated calories burned
        :param average_heart_rate: Average heart rate during workout (bpm)
        :param location: Location where workout took place
        :param notes: Additional notes about the workout
        :returns: workout_id of the logged workout
        """
        workout_type_enum = WorkoutType[workout_type.upper().replace(" ", "_")]
        intensity_enum = IntensityLevel[intensity.upper()]

        current_time = self.time_manager.time()
        start_time = current_time - (duration_minutes * 60)

        workout = Workout(
            workout_id=uuid_hex(self.rng),
            workout_type=workout_type_enum,
            start_time=start_time,
            end_time=current_time,
            duration_minutes=duration_minutes,
            distance=distance,
            calories_burned=calories_burned,
            average_heart_rate=average_heart_rate,
            intensity=intensity_enum,
            location=location,
            notes=notes,
        )

        self.workouts[workout.workout_id] = workout

        # Update activity rings
        self._update_activity_rings(workout)

        # Update goals
        self._update_goals_from_workout(workout)

        return workout.workout_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_workout_history(
        self,
        workout_type: str | None = None,
        limit: int = 10,
        sort_by: str = "date",
    ) -> str:
        """
        Get workout history, optionally filtered by type.

        :param workout_type: Optional filter by workout type
        :param limit: Maximum number of workouts to return (default 10, use -1 for all)
        :param sort_by: Sort by 'date', 'duration', or 'calories' (default 'date')
        :returns: String representation of workout history
        """
        filtered_workouts = list(self.workouts.values())

        if workout_type:
            workout_type_enum = WorkoutType[workout_type.upper().replace(" ", "_")]
            filtered_workouts = [w for w in filtered_workouts if w.workout_type == workout_type_enum]

        # Sort workouts
        if sort_by == "date":
            filtered_workouts.sort(key=lambda w: w.start_time, reverse=True)
        elif sort_by == "duration":
            filtered_workouts.sort(key=lambda w: w.duration_minutes, reverse=True)
        elif sort_by == "calories":
            filtered_workouts.sort(key=lambda w: w.calories_burned or 0, reverse=True)

        if limit > 0:
            filtered_workouts = filtered_workouts[:limit]

        if not filtered_workouts:
            return "No workouts found."

        result = f"Workout History ({len(filtered_workouts)} workout{'s' if len(filtered_workouts) != 1 else ''}):\n\n"
        for workout in filtered_workouts:
            result += str(workout) + "-" * 50 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_workout(self, workout_id: str) -> str:
        """
        Delete a workout from history.

        :param workout_id: ID of the workout to delete
        :returns: Success or error message
        """
        if workout_id not in self.workouts:
            return f"Workout with ID {workout_id} not found."

        workout = self.workouts[workout_id]
        del self.workouts[workout_id]

        return f"✓ {workout.workout_type.value} workout from {time.ctime(workout.start_time)} deleted."

    # Activity Rings

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_todays_activity_rings(self) -> str:
        """
        Get today's activity rings status.

        :returns: Current activity rings status
        """
        date_key = time.strftime("%Y-%m-%d", time.gmtime(self.time_manager.time()))

        if date_key not in self.activity_rings:
            self.activity_rings[date_key] = ActivityRing(date=self.time_manager.time())

        return str(self.activity_rings[date_key])

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_activity_ring(self, ring_type: str, value: int) -> str:
        """
        Manually update an activity ring value.

        :param ring_type: Type of ring to update. Options: move, exercise, stand
        :param value: Value to add to the ring
        :returns: Updated ring status
        """
        date_key = time.strftime("%Y-%m-%d", time.gmtime(self.time_manager.time()))

        if date_key not in self.activity_rings:
            self.activity_rings[date_key] = ActivityRing(date=self.time_manager.time())

        ring = self.activity_rings[date_key]

        if ring_type.lower() == "move":
            ring.move_current = min(ring.move_goal * 2, ring.move_current + value)
            return f"✓ Move ring updated: {ring.move_current}/{ring.move_goal} cal ({ring.move_percentage:.1f}%)"
        elif ring_type.lower() == "exercise":
            ring.exercise_current = min(ring.exercise_goal * 2, ring.exercise_current + value)
            return f"✓ Exercise ring updated: {ring.exercise_current}/{ring.exercise_goal} min ({ring.exercise_percentage:.1f}%)"
        elif ring_type.lower() == "stand":
            ring.stand_current = min(ring.stand_goal, ring.stand_current + value)
            return f"✓ Stand ring updated: {ring.stand_current}/{ring.stand_goal} hrs ({ring.stand_percentage:.1f}%)"
        else:
            return "Invalid ring type. Use 'move', 'exercise', or 'stand'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_activity_ring_goals(
        self,
        move_goal: int | None = None,
        exercise_goal: int | None = None,
        stand_goal: int | None = None,
    ) -> str:
        """
        Set daily activity ring goals.

        :param move_goal: Daily move goal in calories
        :param exercise_goal: Daily exercise goal in minutes
        :param stand_goal: Daily stand goal in hours
        :returns: Success message
        """
        date_key = time.strftime("%Y-%m-%d", time.gmtime(self.time_manager.time()))

        if date_key not in self.activity_rings:
            self.activity_rings[date_key] = ActivityRing(date=self.time_manager.time())

        ring = self.activity_rings[date_key]
        changes = []

        if move_goal is not None:
            ring.move_goal = move_goal
            changes.append(f"Move: {move_goal} cal")

        if exercise_goal is not None:
            ring.exercise_goal = exercise_goal
            changes.append(f"Exercise: {exercise_goal} min")

        if stand_goal is not None:
            ring.stand_goal = stand_goal
            changes.append(f"Stand: {stand_goal} hrs")

        return f"✓ Activity ring goals updated: {', '.join(changes)}"

    # Fitness Goals

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_fitness_goal(
        self,
        name: str,
        goal_type: str,
        target_value: float,
        unit: str,
        target_date: str | None = None,
        frequency: str | None = None,
        notes: str | None = None,
    ) -> str:
        """
        Create a new fitness goal.

        :param name: Name of the goal (e.g., "Run 100 miles this month")
        :param goal_type: Type of goal. Options: Weight Loss, Muscle Gain, Endurance, Flexibility, General Fitness, Stress Reduction
        :param target_value: Target value to achieve
        :param unit: Unit of measurement (e.g., "workouts", "miles", "lbs", "minutes")
        :param target_date: Target completion date in format "YYYY-MM-DD" (optional)
        :param frequency: How often to work on goal (e.g., "3 times per week", "daily")
        :param notes: Additional notes about the goal
        :returns: goal_id of the created goal
        """
        goal_type_enum = GoalType[goal_type.upper().replace(" ", "_")]

        target_timestamp = None
        if target_date:
            from datetime import datetime, timezone
            dt = datetime.strptime(target_date, "%Y-%m-%d")
            target_timestamp = dt.replace(tzinfo=timezone.utc).timestamp()

        goal = FitnessGoal(
            goal_id=uuid_hex(self.rng),
            name=name,
            goal_type=goal_type_enum,
            target_value=target_value,
            unit=unit,
            start_date=self.time_manager.time(),
            target_date=target_timestamp,
            frequency=frequency,
            notes=notes,
        )

        self.goals[goal.goal_id] = goal
        return goal.goal_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_fitness_goals(self, active_only: bool = True) -> str:
        """
        List fitness goals.

        :param active_only: If True, only show active goals
        :returns: String representation of fitness goals
        """
        filtered_goals = [g for g in self.goals.values() if not active_only or g.is_active]

        if not filtered_goals:
            return "No fitness goals found."

        # Sort by progress percentage (descending)
        filtered_goals.sort(key=lambda g: g.progress_percentage, reverse=True)

        result = f"Fitness Goals ({len(filtered_goals)}):\n\n"
        for goal in filtered_goals:
            result += str(goal) + "-" * 50 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_goal_progress(self, goal_id: str, new_value: float) -> str:
        """
        Update progress on a fitness goal.

        :param goal_id: ID of the goal to update
        :param new_value: New current value
        :returns: Updated goal status
        """
        if goal_id not in self.goals:
            return f"Goal with ID {goal_id} not found."

        goal = self.goals[goal_id]
        goal.current_value = new_value

        if goal.current_value >= goal.target_value:
            goal.is_active = False
            return f"🎉 Goal '{goal.name}' completed! Progress: {goal.current_value}/{goal.target_value} {goal.unit}"

        return f"✓ Goal '{goal.name}' updated: {goal.current_value}/{goal.target_value} {goal.unit} ({goal.progress_percentage:.1f}%)"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_fitness_goal(self, goal_id: str) -> str:
        """
        Delete a fitness goal.

        :param goal_id: ID of the goal to delete
        :returns: Success or error message
        """
        if goal_id not in self.goals:
            return f"Goal with ID {goal_id} not found."

        goal = self.goals[goal_id]
        del self.goals[goal_id]

        return f"✓ Goal '{goal.name}' deleted."

    # Workout Plans

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_workout_plan(
        self,
        name: str,
        duration_weeks: int,
        difficulty_level: str = "Intermediate",
        workouts_per_week: int = 3,
        focus_areas: list[str] | None = None,
        description: str | None = None,
    ) -> str:
        """
        Create a new workout plan.

        :param name: Name of the plan (e.g., "Couch to 5K", "Summer Shred")
        :param duration_weeks: Duration of plan in weeks
        :param difficulty_level: Difficulty level. Options: Beginner, Intermediate, Advanced
        :param workouts_per_week: Number of workouts per week
        :param focus_areas: List of focus areas (e.g., ["cardio", "strength", "flexibility"])
        :param description: Description of the plan
        :returns: plan_id of the created plan
        """
        if focus_areas is None:
            focus_areas = []

        plan = WorkoutPlan(
            plan_id=uuid_hex(self.rng),
            name=name,
            description=description,
            duration_weeks=duration_weeks,
            difficulty_level=difficulty_level,
            workouts_per_week=workouts_per_week,
            focus_areas=focus_areas,
            created_date=self.time_manager.time(),
        )

        self.plans[plan.plan_id] = plan
        return plan.plan_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def start_workout_plan(self, plan_id: str) -> str:
        """
        Start following a workout plan.

        :param plan_id: ID of the plan to start
        :returns: Success or error message
        """
        if plan_id not in self.plans:
            return f"Workout plan with ID {plan_id} not found."

        # Deactivate other plans
        for plan in self.plans.values():
            plan.is_active = False

        plan = self.plans[plan_id]
        plan.is_active = True
        plan.started_date = self.time_manager.time()

        return f"✓ Started workout plan '{plan.name}'. Duration: {plan.duration_weeks} weeks, {plan.workouts_per_week} workouts/week."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_workout_plans(self) -> str:
        """
        List all workout plans.

        :returns: String representation of all workout plans
        """
        if not self.plans:
            return "No workout plans found."

        result = f"Workout Plans ({len(self.plans)}):\n\n"
        for plan in self.plans.values():
            result += str(plan) + "-" * 50 + "\n"

        return result

    # Personal Records

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_personal_record(
        self,
        achievement_name: str,
        workout_type: str,
        metric_name: str,
        value: float,
        unit: str,
        notes: str | None = None,
    ) -> str:
        """
        Set a new personal record.

        :param achievement_name: Name of the achievement (e.g., "Fastest 5K", "Longest Run")
        :param workout_type: Type of workout
        :param metric_name: Name of metric (e.g., "Distance", "Time", "Weight", "Reps")
        :param value: Record value
        :param unit: Unit of measurement
        :param notes: Optional notes
        :returns: record_id of the personal record
        """
        workout_type_enum = WorkoutType[workout_type.upper().replace(" ", "_")]

        # Check for existing record
        existing_record = None
        for record in self.personal_records.values():
            if (record.achievement_name == achievement_name and
                record.workout_type == workout_type_enum and
                record.metric_name == metric_name):
                existing_record = record
                break

        previous_value = existing_record.value if existing_record else None

        record = PersonalRecord(
            record_id=uuid_hex(self.rng),
            achievement_name=achievement_name,
            workout_type=workout_type_enum,
            metric_name=metric_name,
            value=value,
            unit=unit,
            date_achieved=self.time_manager.time(),
            previous_record=previous_value,
            notes=notes,
        )

        self.personal_records[record.record_id] = record

        if previous_value:
            improvement = value - previous_value
            return f"🏆 New personal record! {achievement_name}: {value} {unit} (Previous: {previous_value}, Improvement: +{improvement:.2f})"
        else:
            return f"🏆 Personal record set! {achievement_name}: {value} {unit}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_personal_records(self, workout_type: str | None = None) -> str:
        """
        List personal records.

        :param workout_type: Optional filter by workout type
        :returns: String representation of personal records
        """
        filtered_records = list(self.personal_records.values())

        if workout_type:
            workout_type_enum = WorkoutType[workout_type.upper().replace(" ", "_")]
            filtered_records = [r for r in filtered_records if r.workout_type == workout_type_enum]

        if not filtered_records:
            return "No personal records found."

        # Sort by date (most recent first)
        filtered_records.sort(key=lambda r: r.date_achieved, reverse=True)

        result = f"Personal Records ({len(filtered_records)}):\n\n"
        for record in filtered_records:
            result += str(record) + "-" * 50 + "\n"

        return result

    # Statistics and Analytics

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_fitness_summary(self, days: int = 30) -> str:
        """
        Get comprehensive fitness summary for specified time period.

        :param days: Number of days to include in summary (default 30)
        :returns: Detailed fitness statistics
        """
        current_time = self.time_manager.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)

        recent_workouts = [w for w in self.workouts.values() if w.start_time >= cutoff_time]

        if not recent_workouts:
            return f"No workouts found in the last {days} days."

        # Calculate statistics
        total_workouts = len(recent_workouts)
        total_minutes = sum(w.duration_minutes for w in recent_workouts)
        total_calories = sum(w.calories_burned for w in recent_workouts if w.calories_burned)
        total_distance = sum(w.distance for w in recent_workouts if w.distance)

        workout_types = {}
        for workout in recent_workouts:
            workout_types[workout.workout_type.value] = workout_types.get(workout.workout_type.value, 0) + 1

        summary = f"=== FITNESS SUMMARY (Last {days} Days) ===\n\n"
        summary += f"Total Workouts: {total_workouts}\n"
        summary += f"Total Time: {total_minutes:.0f} minutes ({total_minutes/60:.1f} hours)\n"
        summary += f"Average Workout: {total_minutes/total_workouts:.1f} minutes\n"

        if total_calories > 0:
            summary += f"Total Calories Burned: {total_calories:,}\n"
            summary += f"Average per Workout: {total_calories/total_workouts:.0f} calories\n"

        if total_distance > 0:
            summary += f"Total Distance: {total_distance:.2f} miles\n"

        summary += f"\nWorkout Types:\n"
        for workout_type, count in sorted(workout_types.items(), key=lambda x: x[1], reverse=True):
            summary += f"  {workout_type}: {count} ({count/total_workouts*100:.1f}%)\n"

        # Active goals
        active_goals = [g for g in self.goals.values() if g.is_active]
        if active_goals:
            summary += f"\nActive Goals: {len(active_goals)}\n"
            for goal in active_goals:
                summary += f"  {goal.name}: {goal.progress_percentage:.1f}% complete\n"

        return summary

    # Helper methods

    def _update_activity_rings(self, workout: Workout):
        """Update activity rings based on completed workout."""
        date_key = time.strftime("%Y-%m-%d", time.gmtime(workout.start_time))

        if date_key not in self.activity_rings:
            self.activity_rings[date_key] = ActivityRing(date=workout.start_time)

        ring = self.activity_rings[date_key]

        # Update move (calories)
        if workout.calories_burned:
            ring.move_current = min(ring.move_goal * 2, ring.move_current + workout.calories_burned)

        # Update exercise (minutes of moderate+ activity)
        if workout.intensity in [IntensityLevel.MODERATE, IntensityLevel.HIGH, IntensityLevel.VIGOROUS]:
            exercise_minutes = int(workout.duration_minutes)
            ring.exercise_current = min(ring.exercise_goal * 2, ring.exercise_current + exercise_minutes)

    def _update_goals_from_workout(self, workout: Workout):
        """Update relevant goals based on completed workout."""
        for goal in self.goals.values():
            if not goal.is_active:
                continue

            # Update based on goal unit
            if goal.unit == "workouts":
                goal.current_value += 1
            elif goal.unit == "minutes" and goal.goal_type == GoalType.ENDURANCE:
                goal.current_value += workout.duration_minutes
            elif goal.unit == "miles" and workout.distance:
                goal.current_value += workout.distance

            # Check if goal completed
            if goal.current_value >= goal.target_value:
                goal.is_active = False
