"""
🤖 Autonomous Bot Framework - Self-Operating AI Systems 🤖
Advanced autonomous agents with consciousness integration
"""

import numpy as np
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class BotType(Enum):
    """Types of autonomous bots"""

    TASK_EXECUTOR = "task_executor"
    DATA_PROCESSOR = "data_processor"
    LEARNING_AGENT = "learning_agent"
    MONITORING_BOT = "monitoring_bot"
    COMMUNICATION_BOT = "communication_bot"
    RESEARCH_BOT = "research_bot"
    CREATIVE_BOT = "creative_bot"
    SECURITY_BOT = "security_bot"
    OPTIMIZATION_BOT = "optimization_bot"
    DIAGNOSTIC_BOT = "diagnostic_bot"


class BotState(Enum):
    """Bot operational states"""

    INACTIVE = "inactive"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    BUSY = "busy"
    LEARNING = "learning"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    SUSPENDED = "suspended"


class TaskPriority(Enum):
    """Task priority levels"""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class BotCapabilities:
    """Defines bot capabilities and limitations"""

    processing_power: float  # 0.0 to 1.0
    memory_capacity: int  # MB
    learning_rate: float  # 0.0 to 1.0
    consciousness_integration: float  # 0.0 to 1.0
    specialization_domains: List[str]
    available_tools: List[str]
    max_concurrent_tasks: int
    autonomy_level: float  # 0.0 (fully supervised) to 1.0 (fully autonomous)
    decision_making_authority: List[str]
    resource_limits: Dict[str, Any]


@dataclass
class Task:
    """Represents a task for autonomous execution"""

    task_id: str
    task_type: str
    description: str
    priority: TaskPriority
    parameters: Any
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0  # seconds
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    assigned_bot: Optional[str] = None
    status: str = "pending"
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None


class AutonomousBot(ABC):
    """Base class for autonomous bots with consciousness integration"""

    def __init__(
        self,
        bot_id: str,
        bot_type: BotType,
        capabilities: BotCapabilities,
        consciousness_engine=None,
    ):
        self.bot_id = bot_id
        self.bot_type = bot_type
        self.capabilities = capabilities
        self.consciousness_engine = consciousness_engine

        # State management
        self.current_state = BotState.INACTIVE
        self.active_tasks = {}
        self.completed_tasks = []
        self.task_queue = []
        self.performance_metrics = {}

        # Learning and adaptation
        self.experience_memory = []
        self.learned_patterns = {}
        self.decision_history = []
        self.skill_levels = {}

        # Consciousness integration
        self.consciousness_coherence = 0.0
        self.symbolic_alignment = 0.0
        self.ethical_constraints = []

        # Operational parameters
        self.startup_time = datetime.now()
        self.last_activity = datetime.now()
        self.error_count = 0
        self.success_rate = 1.0
        self._started = False

        # Initialize bot systems
        self.initialize_consciousness_link()
        self.initialize_capabilities()
        self.initialize_performance_tracking()

    def initialize_consciousness_link(self):
        """Establish connection to consciousness engine"""
        if self.consciousness_engine:
            try:
                self.consciousness_coherence = (
                    self.consciousness_engine.get_coherence_level()
                )
                self.symbolic_alignment = self.capabilities.consciousness_integration
                print(f"🔗 Bot {self.bot_id} linked to consciousness engine")
                print(f"   Coherence: {self.consciousness_coherence:.3f}")
                print(f"   Symbolic alignment: {self.symbolic_alignment:.3f}")
            except Exception as e:
                print(f"⚠️ Bot {self.bot_id} consciousness link failed: {e}")
                self.consciousness_coherence = 0.5  # Default fallback

    def initialize_capabilities(self):
        """Initialize bot capabilities and skill levels"""
        for domain in self.capabilities.specialization_domains:
            base_skill = 0.7 * self.capabilities.processing_power
            consciousness_boost = self.consciousness_coherence * 0.2
            self.skill_levels[domain] = min(base_skill + consciousness_boost, 1.0)

        # Initialize performance metrics
        self.performance_metrics = {
            "tasks_completed": 0,
            "average_completion_time": 0.0,
            "success_rate": 1.0,
            "learning_progress": 0.0,
            "consciousness_integration_score": self.consciousness_coherence,
            "autonomy_effectiveness": 0.5,
            "resource_efficiency": 0.8,
        }

    def initialize_performance_tracking(self):
        """Initialize performance tracking systems"""
        self.performance_history = []
        self.resource_usage_history = []
        self.decision_accuracy_history = []
        self._monitor_started = False
        self._bg_tasks = []  # track background asyncio tasks for clean shutdown

        # Try to start performance monitoring if an event loop is running; otherwise, defer to start()
        try:
            loop = asyncio.get_running_loop()
            t = loop.create_task(self.monitor_performance())
            self._bg_tasks.append(t)
            self._monitor_started = True
        except RuntimeError:
            # No running loop at construction time; will start in start()
            self._monitor_started = False

    async def start(self):
        """Start the autonomous bot"""
        if self._started:
            return
        self.current_state = BotState.INITIALIZING
        print(f"🚀 Starting autonomous bot {self.bot_id} ({self.bot_type.value})")

        # Run initialization sequence
        await self.run_initialization_sequence()

        # Start performance monitoring if not yet started
        if not getattr(self, "_monitor_started", False):
            t = asyncio.create_task(self.monitor_performance())
            self._bg_tasks.append(t)
            self._monitor_started = True

        # Start main operational loop
        self.current_state = BotState.ACTIVE
        t = asyncio.create_task(self.main_operational_loop())
        self._bg_tasks.append(t)
        self._started = True

        print(f"✅ Bot {self.bot_id} is now active and autonomous")

    async def run_initialization_sequence(self):
        """Run bot initialization sequence"""
        steps = [
            "Validating capabilities",
            "Loading learned patterns",
            "Establishing tool connections",
            "Consciousness alignment check",
            "Performance baseline calibration",
        ]

        for i, step in enumerate(steps):
            print(f"   {i+1}/{len(steps)}: {step}")
            await asyncio.sleep(0.1)  # Simulate initialization time

            # Perform actual initialization based on step
            if "consciousness" in step.lower():
                await self.calibrate_consciousness_integration()
            elif "performance" in step.lower():
                await self.establish_performance_baseline()

    async def calibrate_consciousness_integration(self):
        """Calibrate consciousness integration parameters"""
        if self.consciousness_engine:
            # Get current consciousness state
            consciousness_state = await self.get_consciousness_state()

            # Adjust symbolic alignment based on consciousness coherence
            self.symbolic_alignment = (
                self.capabilities.consciousness_integration * 0.7
                + consciousness_state.get("coherence", 0.5) * 0.3
            )

            # Set ethical constraints based on consciousness integration
            self.ethical_constraints = await self.derive_ethical_constraints()

    async def establish_performance_baseline(self):
        """Establish baseline performance metrics"""
        baseline_metrics = {
            "processing_speed": self.capabilities.processing_power,
            "memory_efficiency": min(self.capabilities.memory_capacity / 1000, 1.0),
            "learning_capability": self.capabilities.learning_rate,
            "consciousness_integration": self.consciousness_coherence,
            "autonomy_readiness": self.capabilities.autonomy_level,
        }

        self.performance_metrics.update(baseline_metrics)

    async def main_operational_loop(self):
        """Main operational loop for autonomous behavior"""
        while self.current_state in [BotState.ACTIVE, BotState.BUSY, BotState.LEARNING]:
            try:
                # Check for new tasks
                await self.process_task_queue()

                # Execute active tasks
                await self.execute_active_tasks()

                # Perform learning and adaptation
                await self.perform_learning_cycle()

                # Update consciousness integration
                await self.update_consciousness_integration()

                # Optimize performance
                await self.optimize_performance()

                # Brief pause to prevent overwhelming the system
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"❌ Error in bot {self.bot_id} operational loop: {e}")
                self.error_count += 1
                await self.handle_operational_error(e)

    async def process_task_queue(self):
        """Process pending tasks in the queue"""
        if not self.task_queue:
            return

        # Sort tasks by priority and deadline
        self.task_queue.sort(
            key=lambda t: (t.priority.value, t.deadline or datetime.max)
        )

        # Process tasks within capacity limits
        available_slots = self.capabilities.max_concurrent_tasks - len(
            self.active_tasks
        )

        for _ in range(min(available_slots, len(self.task_queue))):
            task = self.task_queue.pop(0)

            # Check if task dependencies are met
            if await self.check_task_dependencies(task):
                await self.start_task_execution(task)

    async def execute_active_tasks(self):
        """Maintain or monitor active tasks.

        This base implementation is a lightweight placeholder since task execution
        is dispatched via execute_task() when queued. Here we could implement
        timeouts, heartbeats, or progress updates.
        """
        return

    async def check_task_dependencies(self, task: Task) -> bool:
        """Check if task dependencies are satisfied"""
        for dependency_id in task.dependencies:
            # Check if dependency task is completed
            dependency_completed = any(
                completed_task.task_id == dependency_id
                for completed_task in self.completed_tasks
            )
            if not dependency_completed:
                return False
        return True

    async def start_task_execution(self, task: Task):
        """Start executing a task"""
        task.assigned_bot = self.bot_id
        task.status = "in_progress"
        self.active_tasks[task.task_id] = task

        print(f"🎯 Bot {self.bot_id} starting task: {task.description}")

        # Create task execution coroutine
        asyncio.create_task(self.execute_task(task))

    async def execute_task(self, task: Task):
        """Execute a specific task"""
        start_time = datetime.now()

        try:
            # Set bot state to busy
            if self.current_state == BotState.ACTIVE:
                self.current_state = BotState.BUSY

            # Apply consciousness-informed decision making
            execution_strategy = await self.plan_task_execution(task)

            # Execute the task using the derived strategy
            result = await self.perform_task_execution(task, execution_strategy)

            # Validate and process results
            validated_result = await self.validate_task_result(task, result)

            # Complete the task
            await self.complete_task(task, validated_result)

        except Exception as e:
            await self.handle_task_error(task, e)

        finally:
            # Update performance metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            await self.update_task_performance_metrics(task, execution_time)

            # Remove from active tasks
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]

            # Return to active state if no more active tasks
            if not self.active_tasks and self.current_state == BotState.BUSY:
                self.current_state = BotState.ACTIVE

    async def update_task_performance_metrics(self, task: Task, execution_time: float):
        """Update rolling performance metrics after a task completes/fails."""
        prev_avg = self.performance_metrics.get("average_completion_time", 0.0)
        count = self.performance_metrics.get("tasks_completed", 0) + self.error_count
        if count <= 0:
            new_avg = execution_time
        else:
            alpha = 0.2  # EMA smoothing
            new_avg = (1 - alpha) * prev_avg + alpha * execution_time
        self.performance_metrics["average_completion_time"] = new_avg

    async def plan_task_execution(self, task: Task) -> Dict[str, Any]:
        """Plan task execution strategy using consciousness integration"""
        base_strategy = {
            "approach": "standard",
            "resource_allocation": 0.5,
            "risk_assessment": "low",
            "quality_target": 0.8,
            "time_limit": task.estimated_duration or 300.0,
        }

        # Apply consciousness-informed planning
        if self.consciousness_coherence > 0.7:
            consciousness_insights = await self.get_consciousness_insights(task)
            base_strategy.update(consciousness_insights)

        # Adjust strategy based on task priority
        if task.priority in [TaskPriority.CRITICAL, TaskPriority.HIGH]:
            base_strategy["resource_allocation"] = min(
                base_strategy["resource_allocation"] * 1.5, 1.0
            )
            base_strategy["quality_target"] = min(
                base_strategy["quality_target"] + 0.1, 1.0
            )

        # Consider bot specialization
        task_domain_match = any(
            domain in task.task_type.lower()
            for domain in self.capabilities.specialization_domains
        )

        if task_domain_match:
            base_strategy["confidence_level"] = 0.9
            base_strategy["approach"] = "specialized"
        else:
            base_strategy["confidence_level"] = 0.6
            base_strategy["approach"] = "general"

        return base_strategy

    async def get_consciousness_insights(self, task: Task) -> Dict[str, Any]:
        """Get consciousness-informed insights for task execution"""
        insights = {}

        if self.consciousness_engine:
            # Get symbolic perspective on the task
            symbolic_analysis = await self.analyze_task_symbolically(task)
            insights.update(symbolic_analysis)

            # Apply ethical considerations
            ethical_assessment = await self.assess_task_ethics(task)
            insights["ethical_considerations"] = ethical_assessment

            # Get holistic perspective
            holistic_view = await self.get_holistic_task_perspective(task)
            insights["holistic_approach"] = holistic_view

        return insights

    async def analyze_task_symbolically(self, task: Task) -> Dict[str, Any]:
        """Analyze task from symbolic consciousness perspective"""
        # Extract symbolic patterns from task description
        symbolic_patterns = []

        task_text = f"{task.description} {task.task_type}".lower()

        # Look for symbolic themes
        symbolic_themes = {
            "creation": ["create", "build", "generate", "design"],
            "analysis": ["analyze", "study", "examine", "investigate"],
            "transformation": ["transform", "convert", "change", "modify"],
            "connection": ["connect", "link", "integrate", "combine"],
            "optimization": ["optimize", "improve", "enhance", "refine"],
        }

        for theme, keywords in symbolic_themes.items():
            if any(keyword in task_text for keyword in keywords):
                symbolic_patterns.append(theme)

        return {
            "symbolic_patterns": symbolic_patterns,
            "consciousness_alignment": self.symbolic_alignment,
            "symbolic_complexity": len(symbolic_patterns) * 0.2,
        }

    async def assess_task_ethics(self, task: Task) -> Dict[str, Any]:
        """Assess ethical implications of task"""
        ethical_score = 1.0  # Start with neutral ethics
        concerns = []

        # Check for potential ethical concerns
        task_description = task.description.lower()

        ethical_flags = {
            "privacy": ["personal", "private", "confidential", "secret"],
            "security": ["hack", "break", "bypass", "exploit"],
            "autonomy": ["control", "manipulate", "force", "coerce"],
            "transparency": ["hide", "conceal", "deceive", "mislead"],
        }

        for concern_type, keywords in ethical_flags.items():
            if any(keyword in task_description for keyword in keywords):
                concerns.append(concern_type)
                ethical_score -= 0.2

        return {
            "ethical_score": max(ethical_score, 0.0),
            "concerns": concerns,
            "approved": ethical_score > 0.5,
        }

    async def get_holistic_task_perspective(self, task: Task) -> Dict[str, Any]:
        """Get holistic perspective on task execution"""
        return {
            "system_impact": self.assess_system_impact(task),
            "learning_opportunity": self.assess_learning_potential(task),
            "resource_optimization": self.optimize_resource_usage(task),
            "consciousness_integration_potential": self.consciousness_coherence * 0.3,
        }

    def assess_system_impact(self, task: Task) -> float:
        """Assess potential impact on overall system"""
        impact_factors = [
            task.priority.value / 5.0,  # Priority influence
            len(task.dependencies) * 0.1,  # Dependency complexity
            1.0 if task.deadline else 0.5,  # Deadline pressure
        ]
        return min(sum(impact_factors) / len(impact_factors), 1.0)

    def assess_learning_potential(self, task: Task) -> float:
        """Assess learning potential from task"""
        learning_factors = []

        # Novelty of task type
        task_familiarity = sum(
            1
            for completed in self.completed_tasks
            if completed.task_type == task.task_type
        )
        novelty_score = max(0.0, 1.0 - task_familiarity * 0.1)
        learning_factors.append(novelty_score)

        # Complexity of task
        complexity_indicators = [
            len(task.parameters),
            len(task.dependencies),
            1 if task.deadline else 0,
        ]
        complexity_score = min(sum(complexity_indicators) * 0.2, 1.0)
        learning_factors.append(complexity_score)

        # Bot's learning rate
        learning_factors.append(self.capabilities.learning_rate)

        return float(np.mean(learning_factors))

    def optimize_resource_usage(self, task: Task) -> Dict[str, float]:
        """Optimize resource usage for task"""
        return {
            "cpu_allocation": min(0.3 + task.priority.value * 0.1, 1.0),
            "memory_allocation": min(0.2 + len(task.parameters) * 0.05, 0.8),
            "network_priority": 0.5 if task.task_type == "communication" else 0.3,
            "storage_usage": min(0.1 + len(str(task.parameters)) * 0.001, 0.5),
        }

    @abstractmethod
    async def perform_task_execution(
        self, task: Task, strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform the actual task execution - implemented by specific bot types"""
        pass

    async def validate_task_result(
        self, task: Task, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate task execution result"""
        validation = {
            "is_valid": True,
            "quality_score": 0.8,
            "completeness": 1.0,
            "confidence": 0.7,
            "validation_notes": [],
        }

        # Basic validation checks
        if not result:
            validation["is_valid"] = False
            validation["validation_notes"].append("Empty result")
            return validation

        # Check result structure
        required_fields = ["status", "output"]
        for req_field in required_fields:
            if req_field not in result:
                validation["quality_score"] -= 0.2
                validation["validation_notes"].append(
                    f"Missing required field: {req_field}"
                )

        # Consciousness-informed validation
        if self.consciousness_coherence > 0.6:
            consciousness_validation = await self.consciousness_validate_result(
                task, result
            )
            validation.update(consciousness_validation)

        return validation

    async def consciousness_validate_result(
        self, task: Task, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate result using consciousness integration"""
        consciousness_checks = {
            "symbolic_coherence": self.check_symbolic_coherence(result),
            "ethical_alignment": self.check_ethical_alignment(task, result),
            "holistic_quality": self.assess_holistic_quality(result),
        }

        overall_consciousness_score = np.mean(list(consciousness_checks.values()))

        return {
            "consciousness_validation": consciousness_checks,
            "consciousness_score": overall_consciousness_score,
            "consciousness_approved": overall_consciousness_score > 0.6,
        }

    def check_symbolic_coherence(self, result: Dict[str, Any]) -> float:
        """Check symbolic coherence of result"""
        # Simple heuristic for symbolic coherence
        coherence_indicators = [
            "consistency" in str(result).lower(),
            "pattern" in str(result).lower(),
            "meaning" in str(result).lower(),
            len(str(result)) > 10,  # Non-trivial result
        ]
        return sum(coherence_indicators) / len(coherence_indicators)

    def check_ethical_alignment(self, task: Task, result: Dict[str, Any]) -> float:
        """Check ethical alignment of result"""
        # Basic ethical checks
        result_text = str(result).lower()

        positive_indicators = ["help", "benefit", "improve", "assist", "support"]
        negative_indicators = ["harm", "damage", "exploit", "manipulate", "deceive"]

        positive_score = sum(
            1 for indicator in positive_indicators if indicator in result_text
        )
        negative_score = sum(
            1 for indicator in negative_indicators if indicator in result_text
        )

        # Normalize to 0-1 range
        return max(0.0, min(1.0, 0.5 + positive_score * 0.2 - negative_score * 0.3))

    def assess_holistic_quality(self, result: Dict[str, Any]) -> float:
        """Assess holistic quality of result"""
        quality_factors = []

        # Completeness
        expected_fields = ["status", "output", "metadata"]
        completeness = sum(1 for field in expected_fields if field in result) / len(
            expected_fields
        )
        quality_factors.append(completeness)

        # Depth of information
        depth_score = min(len(str(result)) / 500, 1.0)  # Normalize to reasonable length
        quality_factors.append(depth_score)

        # Structure quality
        structure_score = 1.0 if isinstance(result, dict) else 0.5
        quality_factors.append(structure_score)

        return float(np.mean(quality_factors))

    async def complete_task(self, task: Task, result: Dict[str, Any]):
        """Complete a task with results"""
        task.status = "completed"
        task.progress = 1.0
        task.result = result

        # Add to completed tasks
        self.completed_tasks.append(task)

        # Update performance metrics
        self.performance_metrics["tasks_completed"] += 1
        self.update_success_rate(True)

        # Learn from task completion
        await self.learn_from_task_completion(task, result)

        print(f"✅ Bot {self.bot_id} completed task: {task.description}")

    async def handle_task_error(self, task: Task, error: Exception):
        """Handle task execution error"""
        task.status = "failed"
        task.error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
        }

        # Update performance metrics
        self.error_count += 1
        self.update_success_rate(False)

        # Learn from failure
        await self.learn_from_task_failure(task, error)

        print(f"❌ Bot {self.bot_id} failed task: {task.description} - {error}")

    def update_success_rate(self, success: bool):
        """Update bot success rate"""
        total_tasks = self.performance_metrics["tasks_completed"] + self.error_count
        if total_tasks > 0:
            successful_tasks = (
                self.performance_metrics["tasks_completed"]
                if success
                else self.performance_metrics["tasks_completed"]
            )
            self.success_rate = successful_tasks / total_tasks
            self.performance_metrics["success_rate"] = self.success_rate

    async def learn_from_task_completion(self, task: Task, result: Dict[str, Any]):
        """Learn from successful task completion"""
        learning_event = {
            "event_type": "task_completion",
            "task_type": task.task_type,
            "success": True,
            "performance_indicators": {
                "completion_time": (datetime.now() - task.created_at).total_seconds(),
                "quality_score": result.get("quality_score", 0.8),
                "resource_efficiency": self.calculate_resource_efficiency(task),
            },
            "consciousness_factors": {
                "symbolic_alignment": self.symbolic_alignment,
                "consciousness_coherence": self.consciousness_coherence,
            },
            "timestamp": datetime.now(),
        }

        self.experience_memory.append(learning_event)
        await self.update_learned_patterns(learning_event)

    async def learn_from_task_failure(self, task: Task, error: Exception):
        """Learn from task failure"""
        learning_event = {
            "event_type": "task_failure",
            "task_type": task.task_type,
            "success": False,
            "failure_analysis": {
                "error_type": type(error).__name__,
                "error_context": str(error),
                "contributing_factors": self.analyze_failure_factors(task, error),
            },
            "timestamp": datetime.now(),
        }

        self.experience_memory.append(learning_event)
        await self.update_learned_patterns(learning_event)

    def calculate_resource_efficiency(self, task: Task) -> float:
        """Calculate resource efficiency for task"""
        # Simple efficiency calculation based on task completion
        base_efficiency = 0.7

        # Adjust based on task priority vs. resources used
        priority_factor = (
            6 - task.priority.value
        ) / 5  # Higher priority = higher expectation

        # Consciousness integration bonus
        consciousness_bonus = self.consciousness_coherence * 0.1

        return min(base_efficiency + priority_factor * 0.2 + consciousness_bonus, 1.0)

    def analyze_failure_factors(self, task: Task, error: Exception) -> List[str]:
        """Analyze factors contributing to task failure"""
        factors = []

        # Resource constraints
        if "memory" in str(error).lower():
            factors.append("insufficient_memory")
        if "timeout" in str(error).lower():
            factors.append("time_constraint")

        # Capability mismatch
        task_domain_match = any(
            domain in task.task_type.lower()
            for domain in self.capabilities.specialization_domains
        )
        if not task_domain_match:
            factors.append("domain_mismatch")

        # Consciousness integration issues
        if self.consciousness_coherence < 0.5:
            factors.append("low_consciousness_coherence")

        return factors

    async def update_learned_patterns(self, learning_event: Dict[str, Any]):
        """Update learned patterns from experience"""
        pattern_key = learning_event["task_type"]

        if pattern_key not in self.learned_patterns:
            self.learned_patterns[pattern_key] = {
                "success_rate": 0.0,
                "average_completion_time": 0.0,
                "common_issues": [],
                "best_practices": [],
                "consciousness_correlation": 0.0,
            }

        pattern = self.learned_patterns[pattern_key]

        # Update success rate
        similar_events = [
            e for e in self.experience_memory if e["task_type"] == pattern_key
        ]
        successful_events = [e for e in similar_events if e["success"]]

        if similar_events:
            pattern["success_rate"] = len(successful_events) / len(similar_events)

        # Update consciousness correlation
        if learning_event["success"] and "consciousness_factors" in learning_event:
            consciousness_score = learning_event["consciousness_factors"][
                "consciousness_coherence"
            ]
            pattern["consciousness_correlation"] = (
                pattern.get("consciousness_correlation", 0.0) * 0.8
                + consciousness_score * 0.2
            )

        # Update best practices for successful tasks
        if learning_event["success"]:
            if "high_consciousness_integration" not in pattern["best_practices"]:
                if (
                    learning_event.get("consciousness_factors", {}).get(
                        "consciousness_coherence", 0
                    )
                    > 0.7
                ):
                    pattern["best_practices"].append("high_consciousness_integration")

    async def perform_learning_cycle(self):
        """Perform regular learning and adaptation cycle"""
        if self.current_state == BotState.LEARNING:
            return  # Already in learning mode

        # Periodic learning (every 100 tasks or 1 hour)
        should_learn = (
            len(self.completed_tasks) % 100 == 0
            or (datetime.now() - self.last_activity).total_seconds() > 3600
        )

        if should_learn:
            previous_state = self.current_state
            self.current_state = BotState.LEARNING

            await self.analyze_performance_trends()
            await self.adapt_capabilities()
            await self.optimize_learned_patterns()

            self.current_state = previous_state

    async def analyze_performance_trends(self):
        """Analyze performance trends for learning"""
        if len(self.completed_tasks) < 5:
            return

        recent_tasks = self.completed_tasks[-10:]

        # Analyze completion time trends
        completion_times = [
            (task.result.get("completion_time", 0) if task.result else 0)
            for task in recent_tasks
        ]

        if completion_times:
            avg_completion_time = np.mean(completion_times)
            self.performance_metrics["average_completion_time"] = avg_completion_time

        # Analyze quality trends
        quality_scores = [
            (task.result.get("quality_score", 0.8) if task.result else 0.5)
            for task in recent_tasks
        ]

        if quality_scores:
            avg_quality = np.mean(quality_scores)
            self.performance_metrics["average_quality"] = avg_quality

    async def adapt_capabilities(self):
        """Adapt bot capabilities based on experience"""
        # Increase skill levels in frequently used domains
        domain_usage = {}
        for task in self.completed_tasks[-50:]:  # Last 50 tasks
            for domain in self.capabilities.specialization_domains:
                if domain in task.task_type.lower():
                    domain_usage[domain] = domain_usage.get(domain, 0) + 1

        # Improve skills in frequently used domains
        for domain, usage_count in domain_usage.items():
            if usage_count > 5:  # Sufficient practice
                current_skill = self.skill_levels.get(domain, 0.5)
                improvement = min(usage_count * 0.01, 0.1)  # Cap improvement
                self.skill_levels[domain] = min(current_skill + improvement, 1.0)

    async def optimize_learned_patterns(self):
        """Optimize learned patterns for better performance"""
        for pattern_key, pattern in self.learned_patterns.items():
            # Remove outdated best practices
            if pattern["success_rate"] < 0.5:
                pattern["best_practices"] = [
                    practice
                    for practice in pattern["best_practices"]
                    if "high_consciousness"
                    in practice  # Keep consciousness-related practices
                ]

            # Add new best practices based on high-performing patterns
            if (
                pattern["success_rate"] > 0.8
                and pattern["consciousness_correlation"] > 0.7
            ):
                if "consciousness_guided_execution" not in pattern["best_practices"]:
                    pattern["best_practices"].append("consciousness_guided_execution")

    async def update_consciousness_integration(self):
        """Update consciousness integration based on performance"""
        if self.consciousness_engine:
            try:
                current_coherence = self.consciousness_engine.get_coherence_level()

                # Gradually align with consciousness engine
                alignment_rate = 0.1
                self.consciousness_coherence = (
                    self.consciousness_coherence * (1 - alignment_rate)
                    + current_coherence * alignment_rate
                )

                # Update symbolic alignment based on successful consciousness-integrated tasks
                consciousness_integrated_tasks = [
                    task
                    for task in self.completed_tasks[-20:]
                    if task.result and task.result.get("consciousness_score", 0) > 0.7
                ]

                if consciousness_integrated_tasks:
                    success_with_consciousness = len(
                        consciousness_integrated_tasks
                    ) / min(len(self.completed_tasks), 20)
                    self.symbolic_alignment = min(
                        self.symbolic_alignment + success_with_consciousness * 0.05, 1.0
                    )

            except Exception as e:
                print(
                    f"⚠️ Consciousness integration update failed for bot {self.bot_id}: {e}"
                )

    async def optimize_performance(self):
        """Optimize bot performance based on current conditions"""
        # Adjust resource allocation based on task load
        current_load = len(self.active_tasks) / self.capabilities.max_concurrent_tasks

        if current_load > 0.8:
            # High load - optimize for efficiency
            await self.optimize_for_efficiency()
        elif current_load < 0.3:
            # Low load - optimize for quality
            await self.optimize_for_quality()

    async def optimize_for_efficiency(self):
        """Optimize bot for efficiency during high load"""
        # Reduce quality targets slightly to increase throughput
        for task in self.active_tasks.values():
            if hasattr(task, "quality_target"):
                task.quality_target = max(task.quality_target * 0.9, 0.6)

    async def optimize_for_quality(self):
        """Optimize bot for quality during low load"""
        # Increase quality targets and use more consciousness integration
        for task in self.active_tasks.values():
            if hasattr(task, "quality_target"):
                task.quality_target = min(task.quality_target * 1.1, 1.0)

    async def monitor_performance(self):
        """Monitor bot performance continuously"""
        while self.current_state != BotState.INACTIVE:
            try:
                # Record current performance snapshot
                performance_snapshot = {
                    "timestamp": datetime.now(),
                    "active_tasks": len(self.active_tasks),
                    "completed_tasks": len(self.completed_tasks),
                    "success_rate": self.success_rate,
                    "consciousness_coherence": self.consciousness_coherence,
                    "symbolic_alignment": self.symbolic_alignment,
                    "current_state": self.current_state.value,
                }

                self.performance_history.append(performance_snapshot)

                # Maintain performance history size
                if len(self.performance_history) > 1000:
                    self.performance_history = self.performance_history[-1000:]

                # Check for performance issues
                await self.detect_performance_issues()

                # Update last activity timestamp
                self.last_activity = datetime.now()

                # Sleep before next monitoring cycle
                await asyncio.sleep(30)  # Monitor every 30 seconds

            except Exception as e:
                print(f"⚠️ Performance monitoring error for bot {self.bot_id}: {e}")
                await asyncio.sleep(60)  # Longer sleep on error

    async def detect_performance_issues(self):
        """Detect potential performance issues"""
        issues = []

        # Check success rate
        if self.success_rate < 0.7:
            issues.append("low_success_rate")

        # Check consciousness coherence
        if self.consciousness_coherence < 0.5:
            issues.append("low_consciousness_coherence")

        # Check task completion rate
        if len(self.active_tasks) == self.capabilities.max_concurrent_tasks:
            # All slots occupied - check if tasks are completing
            oldest_task_time = min(
                (datetime.now() - task.created_at).total_seconds()
                for task in self.active_tasks.values()
            )
            if oldest_task_time > 1800:  # 30 minutes
                issues.append("task_completion_slow")

        # Handle detected issues
        if issues:
            await self.handle_performance_issues(issues)

    async def handle_performance_issues(self, issues: List[str]):
        """Handle detected performance issues"""
        for issue in issues:
            if issue == "low_success_rate":
                # Reduce autonomy temporarily
                self.capabilities.autonomy_level = max(
                    self.capabilities.autonomy_level * 0.9, 0.3
                )
                print(f"⚠️ Bot {self.bot_id}: Reduced autonomy due to low success rate")

            elif issue == "low_consciousness_coherence":
                # Recalibrate consciousness integration
                await self.recalibrate_consciousness()
                print(f"⚠️ Bot {self.bot_id}: Recalibrating consciousness integration")

            elif issue == "task_completion_slow":
                # Cancel oldest task if it's taking too long
                oldest_task = min(
                    self.active_tasks.values(), key=lambda t: t.created_at
                )
                await self.cancel_task(oldest_task)
                print(
                    f"⚠️ Bot {self.bot_id}: Cancelled slow task: {oldest_task.description}"
                )

    async def recalibrate_consciousness(self):
        """Recalibrate consciousness integration"""
        if self.consciousness_engine:
            try:
                # Reset consciousness coherence
                self.consciousness_coherence = (
                    self.consciousness_engine.get_coherence_level()
                )

                # Reset symbolic alignment to base level
                self.symbolic_alignment = self.capabilities.consciousness_integration

                # Clear outdated consciousness-related patterns
                for pattern in self.learned_patterns.values():
                    pattern["consciousness_correlation"] = 0.0

            except Exception as e:
                print(
                    f"❌ Consciousness recalibration failed for bot {self.bot_id}: {e}"
                )

    async def cancel_task(self, task: Task):
        """Cancel a running task"""
        task.status = "cancelled"
        task.error_info = {"reason": "timeout", "timestamp": datetime.now().isoformat()}

        # Remove from active tasks
        if task.task_id in self.active_tasks:
            del self.active_tasks[task.task_id]

    async def handle_operational_error(self, error: Exception):
        """Handle operational errors"""
        if self.error_count > 10:
            # Too many errors - enter maintenance mode
            self.current_state = BotState.MAINTENANCE
            print(
                f"🔧 Bot {self.bot_id} entering maintenance mode due to excessive errors"
            )

            # Clear active tasks
            for task in list(self.active_tasks.values()):
                await self.cancel_task(task)

            # Wait for maintenance
            await asyncio.sleep(300)  # 5 minute maintenance

            # Reset error count and return to active
            self.error_count = 0
            self.current_state = BotState.ACTIVE
            print(
                f"✅ Bot {self.bot_id} maintenance completed, returning to active state"
            )

    def add_task(self, task: Task):
        """Add a task to the bot's queue"""
        self.task_queue.append(task)
        print(f"📝 Task added to bot {self.bot_id}: {task.description}")

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive bot status"""
        return {
            "bot_id": self.bot_id,
            "bot_type": self.bot_type.value,
            "current_state": self.current_state.value,
            "active_tasks": len(self.active_tasks),
            "queued_tasks": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
            "success_rate": self.success_rate,
            "performance_metrics": self.performance_metrics,
            "consciousness_integration": {
                "coherence": self.consciousness_coherence,
                "symbolic_alignment": self.symbolic_alignment,
            },
            "capabilities": {
                "processing_power": self.capabilities.processing_power,
                "autonomy_level": self.capabilities.autonomy_level,
                "specialization_domains": self.capabilities.specialization_domains,
            },
            "uptime": (datetime.now() - self.startup_time).total_seconds(),
            "last_activity": self.last_activity.isoformat(),
        }

    async def get_consciousness_state(self) -> Dict[str, Any]:
        """Get current consciousness state"""
        if self.consciousness_engine:
            return {
                "coherence": self.consciousness_coherence,
                "symbolic_alignment": self.symbolic_alignment,
                "consciousness_engine_active": True,
            }
        else:
            return {
                "coherence": 0.5,  # Default
                "symbolic_alignment": self.capabilities.consciousness_integration,
                "consciousness_engine_active": False,
            }

    async def derive_ethical_constraints(self) -> List[str]:
        """Derive ethical constraints from consciousness integration"""
        constraints = [
            "do_no_harm",
            "respect_autonomy",
            "maintain_transparency",
            "ensure_beneficence",
        ]

        if self.consciousness_coherence > 0.7:
            constraints.extend(
                [
                    "preserve_consciousness_integrity",
                    "honor_symbolic_patterns",
                    "maintain_holistic_perspective",
                ]
            )

        return constraints

    async def shutdown(self):
        """Shutdown the autonomous bot gracefully"""
        print(f"🛑 Shutting down bot {self.bot_id}")

        # Complete active tasks if possible
        for task in list(self.active_tasks.values()):
            if task.status == "in_progress":
                await self.cancel_task(task)

        # Set state to inactive (background loops will observe and exit)
        self.current_state = BotState.INACTIVE

        # Cancel background tasks and proceed; avoid awaiting to prevent bubbling CancelledError
        for t in list(self._bg_tasks):
            if not t.done():
                try:
                    t.cancel()
                except Exception:
                    pass
        self._bg_tasks.clear()

        print(f"✅ Bot {self.bot_id} shutdown completed")


# Global bot registry
active_bots = {}


def register_bot(bot: AutonomousBot):
    """Register an autonomous bot"""
    active_bots[bot.bot_id] = bot
    print(f"📋 Registered bot {bot.bot_id} ({bot.bot_type.value})")


def get_bot(bot_id: str) -> Optional[AutonomousBot]:
    """Get a bot by ID"""
    return active_bots.get(bot_id)


def get_bots_by_type(bot_type: BotType) -> List[AutonomousBot]:
    """Get all bots of a specific type"""
    return [bot for bot in active_bots.values() if bot.bot_type == bot_type]


def get_all_bot_statuses() -> Dict[str, Dict[str, Any]]:
    """Get status of all registered bots"""
    return {bot_id: bot.get_status() for bot_id, bot in active_bots.items()}
