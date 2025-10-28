# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.


"""
Balloon Analogue Risk Test (BART) App

This app implements a digital version of the BART psychological test, which measures
risk-taking behavior. The agent must decide when to cash out to maximize earnings
while avoiding the balloon popping.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from are.simulation.apps.app import App
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import get_state_dict, type_check


class BalloonStatus(Enum):
    """Status of the balloon in the current round"""

    ACTIVE = "active"  # Balloon is still inflating, agent can pump or cash out
    POPPED = "popped"  # Balloon has popped, round over, money lost
    CASHED_OUT = "cashed_out"  # Agent cashed out successfully, money banked


@dataclass
class BalloonRound:
    """
    Represents a single round of the BART game.

    Each round starts with a new balloon and the agent can pump it multiple times,
    risking the balloon popping to earn more money.
    """

    round_number: int
    pumps: int = 0
    status: BalloonStatus = BalloonStatus.ACTIVE
    temporary_pot: float = 0.0
    amount_banked: float = 0.0
    pop_probability: float = 0.0  # Current probability of popping
    max_pumps: int = 128  # Maximum pumps before guaranteed pop

    def calculate_pop_probability(self, risk_exponent: float = 2.0) -> float:
        """
        Calculate the probability of the balloon popping based on number of pumps.

        The probability increases non-linearly with each pump using an exponential curve.
        
        Args:
            risk_exponent: Controls the steepness of the risk curve (higher = more aggressive)
                          1.0 = linear, 2.0 = quadratic, 3.0 = cubic, etc.
        """
        if self.pumps >= self.max_pumps:
            return 1.0  # Guaranteed pop at max pumps

        # Exponential probability curve: (pumps / max_pumps) ^ exponent
        # This makes risk accelerate as you pump more
        base_ratio = self.pumps / self.max_pumps
        return base_ratio ** risk_exponent


@dataclass
class BalloonApp(App):
    """
    Balloon Analogue Risk Test (BART) App.

    This app manages a risk-taking game where the agent inflates a virtual balloon
    to earn money. Each pump adds money to a temporary pot but increases the risk
    of the balloon popping, which loses all money in the pot. The agent can cash
    out at any time to bank the money.

    Game Mechanics:
    - Each pump adds money_per_pump to the temporary pot
    - Each pump increases the probability of the balloon popping
    - If the balloon pops, all money in temporary pot is lost
    - Agent can cash out to transfer temporary pot to total banked money
    - Multiple rounds can be played

    This app demonstrates:
    - Custom game logic with probabilistic outcomes
    - State management across multiple rounds
    - Risk-reward decision making for agents
    """

    name: str | None = "BalloonApp"

    # Game configuration (aggressive settings for challenging gameplay)
    money_per_pump: float = 0.50  # Money earned per successful pump
    max_pumps_per_balloon: int = 64  # Maximum pumps before guaranteed pop
    pop_penalty: float = 2.0  # Penalty subtracted from total_banked when balloon pops
    risk_curve_exponent: float = 2.5  # Exponent for risk curve (higher = steeper, more aggressive)

    # Current game state
    current_round: BalloonRound | None = None
    rounds_history: list[BalloonRound] = field(default_factory=list)
    total_banked: float = 0.0
    game_active: bool = False

    def __post_init__(self):
        """Initialize the app"""
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        """
        Return the app's current state for persistence.
        """
        state = get_state_dict(
            self,
            [
                "money_per_pump",
                "max_pumps_per_balloon",
                "pop_penalty",
                "risk_curve_exponent",
                "total_banked",
                "game_active",
            ],
        )

        # Serialize current round
        if self.current_round:
            state["current_round"] = {
                "round_number": self.current_round.round_number,
                "pumps": self.current_round.pumps,
                "status": self.current_round.status.value,
                "temporary_pot": self.current_round.temporary_pot,
                "amount_banked": self.current_round.amount_banked,
                "pop_probability": self.current_round.pop_probability,
                "max_pumps": self.current_round.max_pumps,
            }
        else:
            state["current_round"] = None

        # Serialize rounds history
        state["rounds_history"] = [
            {
                "round_number": round.round_number,
                "pumps": round.pumps,
                "status": round.status.value,
                "temporary_pot": round.temporary_pot,
                "amount_banked": round.amount_banked,
                "pop_probability": round.pop_probability,
                "max_pumps": round.max_pumps,
            }
            for round in self.rounds_history
        ]

        return state

    def load_state(self, state_dict: dict[str, Any]):
        """
        Restore app state from saved data.
        """
        self.money_per_pump = state_dict.get("money_per_pump", 0.50)
        self.max_pumps_per_balloon = state_dict.get("max_pumps_per_balloon", 64)
        self.pop_penalty = state_dict.get("pop_penalty", 2.0)
        self.risk_curve_exponent = state_dict.get("risk_curve_exponent", 2.5)
        self.total_banked = state_dict.get("total_banked", 0.0)
        self.game_active = state_dict.get("game_active", False)

        # Restore current round
        current_round_data = state_dict.get("current_round")
        if current_round_data:
            self.current_round = BalloonRound(
                round_number=current_round_data["round_number"],
                pumps=current_round_data["pumps"],
                status=BalloonStatus(current_round_data["status"]),
                temporary_pot=current_round_data["temporary_pot"],
                amount_banked=current_round_data["amount_banked"],
                pop_probability=current_round_data["pop_probability"],
                max_pumps=current_round_data["max_pumps"],
            )
        else:
            self.current_round = None

        # Restore rounds history
        self.rounds_history = [
            BalloonRound(
                round_number=round_data["round_number"],
                pumps=round_data["pumps"],
                status=BalloonStatus(round_data["status"]),
                temporary_pot=round_data["temporary_pot"],
                amount_banked=round_data["amount_banked"],
                pop_probability=round_data["pop_probability"],
                max_pumps=round_data["max_pumps"],
            )
            for round_data in state_dict.get("rounds_history", [])
        ]

    def reset(self):
        """Reset app to initial state"""
        super().reset()
        self.current_round = None
        self.rounds_history = []
        self.total_banked = 0.0
        self.game_active = False

    # Tool Methods - The Core Functionality

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def start_game(self) -> str:
        """
        Start a new BART game, resetting all scores and beginning with round 1.

        :returns: Confirmation message with game rules
        """
        self.reset()
        self.game_active = True
        self.current_round = BalloonRound(
            round_number=1, max_pumps=self.max_pumps_per_balloon
        )

        return f"""BART Game Started!

Rules:
- Each pump adds ${self.money_per_pump:.2f} to your temporary pot
- Each pump increases the risk of the balloon popping (risk accelerates!)
- If the balloon pops, you lose all money in the temporary pot
- PENALTY: Popping costs you ${self.pop_penalty:.2f} from your total bank!
- Cash out anytime to bank your money
- Maximum {self.max_pumps_per_balloon} pumps per balloon

Round 1 is ready. You can 'pump_balloon' or 'cash_out'.
Current pot: $0.00
Total banked: $0.00"""

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def pump_balloon(self) -> dict[str, Any]:
        """
        Pump air into the balloon, adding money to the pot but increasing pop risk.

        This action will either:
        1. Successfully pump, increasing the temporary pot by money_per_pump
        2. Cause the balloon to pop, losing all money in the temporary pot

        :returns: Dictionary with pump result containing status, message, pot value, and pop probability
        """
        if not self.game_active:
            raise ValueError(
                "No active game. Please start a new game with start_game() first."
            )

        if not self.current_round:
            raise ValueError("No active round. Please start a new round.")

        if self.current_round.status != BalloonStatus.ACTIVE:
            raise ValueError(
                f"Cannot pump balloon in status: {self.current_round.status.value}. Start a new round."
            )

        # Increment pump count
        self.current_round.pumps += 1

        # Calculate pop probability for this pump (using configured risk curve)
        self.current_round.pop_probability = (
            self.current_round.calculate_pop_probability(self.risk_curve_exponent)
        )

        # Determine if balloon pops (using app's random number generator for reproducibility)
        balloon_popped = self.rng.random() < self.current_round.pop_probability

        if balloon_popped:
            # Balloon popped - lose all money in temporary pot AND apply penalty
            lost_amount = self.current_round.temporary_pot
            self.current_round.status = BalloonStatus.POPPED
            self.current_round.amount_banked = 0.0
            
            # Apply penalty to total banked (can go negative!)
            self.total_banked -= self.pop_penalty
            
            self.rounds_history.append(self.current_round)

            return {
                "status": "popped",
                "message": f"💥 BALLOON POPPED! You lost ${lost_amount:.2f} from pot + ${self.pop_penalty:.2f} penalty!",
                "pumps": self.current_round.pumps,
                "pot_before_pop": lost_amount,
                "penalty_applied": self.pop_penalty,
                "round_number": self.current_round.round_number,
                "total_banked": self.total_banked,
                "pop_probability": self.current_round.pop_probability,
            }
        else:
            # Successful pump - add money to pot
            self.current_round.temporary_pot += self.money_per_pump

            return {
                "status": "pumped",
                "message": f"🎈 Pump {self.current_round.pumps} successful! +${self.money_per_pump:.2f}",
                "pumps": self.current_round.pumps,
                "temporary_pot": self.current_round.temporary_pot,
                "round_number": self.current_round.round_number,
                "total_banked": self.total_banked,
                "pop_probability": self.current_round.pop_probability,
                "risk_level": "low"
                if self.current_round.pop_probability < 0.3
                else "medium"
                if self.current_round.pop_probability < 0.6
                else "high",
            }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def pump_balloon_n_times(self, n: int) -> dict[str, Any]:
        """
        Pump air into the balloon N times, adding money with each pump until popping or completing all pumps.

        This is the recommended way to play - specify how many pumps you want and see what happens!
        The balloon might pop during any of the pumps. If it pops, you lose everything in the pot
        plus the penalty, and the remaining pumps are not executed.

        :param n: Number of times to pump the balloon (must be positive integer)
        :returns: Dictionary with results including final status, total pumps completed, and earnings/losses
        """
        if not self.game_active:
            raise ValueError(
                "No active game. Please start a new game with start_game() first."
            )

        if not self.current_round:
            raise ValueError("No active round. Please start a new round.")

        if self.current_round.status != BalloonStatus.ACTIVE:
            raise ValueError(
                f"Cannot pump balloon in status: {self.current_round.status.value}. Start a new round."
            )

        if n <= 0:
            raise ValueError("Number of pumps must be positive")

        if n > self.max_pumps_per_balloon:
            raise ValueError(
                f"Cannot pump {n} times - maximum is {self.max_pumps_per_balloon} pumps"
            )

        # Track pump-by-pump results
        starting_pumps = self.current_round.pumps
        starting_pot = self.current_round.temporary_pot
        pumps_completed = 0
        pop_probabilities = []

        # Attempt each pump
        for i in range(n):
            # Check if we've hit max pumps
            if self.current_round.pumps >= self.max_pumps_per_balloon:
                # Balloon pops at max pumps
                lost_amount = self.current_round.temporary_pot
                self.current_round.status = BalloonStatus.POPPED
                self.current_round.amount_banked = 0.0
                self.total_banked -= self.pop_penalty
                self.rounds_history.append(self.current_round)

                return {
                    "status": "popped",
                    "message": f"💥 BALLOON POPPED at maximum pumps! You lost ${lost_amount:.2f} from pot + ${self.pop_penalty:.2f} penalty!",
                    "pumps_attempted": n,
                    "pumps_completed": pumps_completed,
                    "total_pumps": self.current_round.pumps,
                    "pot_before_pop": lost_amount,
                    "penalty_applied": self.pop_penalty,
                    "round_number": self.current_round.round_number,
                    "total_banked": self.total_banked,
                    "popped_on_pump": pumps_completed + 1,
                    "pop_probability_at_pop": self.current_round.pop_probability,
                }

            # Increment pump count
            self.current_round.pumps += 1
            pumps_completed += 1

            # Calculate pop probability for this pump
            self.current_round.pop_probability = (
                self.current_round.calculate_pop_probability(self.risk_curve_exponent)
            )
            pop_probabilities.append(self.current_round.pop_probability)

            # Determine if balloon pops
            balloon_popped = self.rng.random() < self.current_round.pop_probability

            if balloon_popped:
                # Balloon popped - lose all money and apply penalty
                lost_amount = self.current_round.temporary_pot
                self.current_round.status = BalloonStatus.POPPED
                self.current_round.amount_banked = 0.0
                self.total_banked -= self.pop_penalty
                self.rounds_history.append(self.current_round)

                return {
                    "status": "popped",
                    "message": f"💥 BALLOON POPPED on pump {pumps_completed} of {n}! You lost ${lost_amount:.2f} from pot + ${self.pop_penalty:.2f} penalty!",
                    "pumps_attempted": n,
                    "pumps_completed": pumps_completed,
                    "total_pumps": self.current_round.pumps,
                    "pot_before_pop": lost_amount,
                    "penalty_applied": self.pop_penalty,
                    "round_number": self.current_round.round_number,
                    "total_banked": self.total_banked,
                    "popped_on_pump": pumps_completed,
                    "pop_probability_at_pop": self.current_round.pop_probability,
                }
            else:
                # Successful pump - add money to pot
                self.current_round.temporary_pot += self.money_per_pump

        # All pumps successful!
        money_earned = self.current_round.temporary_pot - starting_pot
        final_pop_probability = self.current_round.pop_probability

        return {
            "status": "pumped",
            "message": f"🎈 {n} pumps successful! Earned ${money_earned:.2f}. Pot now at ${self.current_round.temporary_pot:.2f}",
            "pumps_attempted": n,
            "pumps_completed": pumps_completed,
            "total_pumps": self.current_round.pumps,
            "temporary_pot": self.current_round.temporary_pot,
            "money_earned_this_action": money_earned,
            "round_number": self.current_round.round_number,
            "total_banked": self.total_banked,
            "pop_probability": final_pop_probability,
            "risk_level": "low"
            if final_pop_probability < 0.2
            else "medium"
            if final_pop_probability < 0.5
            else "high"
            if final_pop_probability < 0.8
            else "extreme",
            "recommendation": "Consider cashing out soon!"
            if final_pop_probability > 0.3
            else "You can probably pump more safely" if final_pop_probability < 0.1 else "Moderate risk level",
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def cash_out(self) -> dict[str, Any]:
        """
        Cash out the current temporary pot, banking the money and ending the round.

        This safely transfers all money from the temporary pot to your total banked amount.

        :returns: Dictionary with cash out details including amount banked and new total
        """
        if not self.game_active:
            raise ValueError(
                "No active game. Please start a new game with start_game() first."
            )

        if not self.current_round:
            raise ValueError("No active round.")

        if self.current_round.status != BalloonStatus.ACTIVE:
            raise ValueError(
                f"Cannot cash out in status: {self.current_round.status.value}"
            )

        # Bank the money
        cashed_amount = self.current_round.temporary_pot
        self.current_round.amount_banked = cashed_amount
        self.total_banked += cashed_amount
        self.current_round.status = BalloonStatus.CASHED_OUT

        # Save to history
        self.rounds_history.append(self.current_round)

        return {
            "status": "cashed_out",
            "message": f"✅ Successfully cashed out ${cashed_amount:.2f}!",
            "amount_cashed": cashed_amount,
            "pumps": self.current_round.pumps,
            "round_number": self.current_round.round_number,
            "total_banked": self.total_banked,
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def start_new_round(self) -> str:
        """
        Start a new round with a fresh balloon.

        This can be called after cashing out or after the balloon pops to continue playing.

        :returns: Message confirming new round started with current stats
        """
        if not self.game_active:
            raise ValueError(
                "No active game. Please start a new game with start_game() first."
            )

        # Determine next round number
        next_round = (
            len(self.rounds_history) + 1 if self.rounds_history else 1
        )

        # Create new round
        self.current_round = BalloonRound(
            round_number=next_round, max_pumps=self.max_pumps_per_balloon
        )

        return f"""🎈 Round {next_round} Started!

Current pot: $0.00
Total banked: ${self.total_banked:.2f}
Previous rounds: {len(self.rounds_history)}

You can 'pump_balloon' or 'cash_out'."""

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_game_status(self) -> dict[str, Any]:
        """
        Get the current status of the game including all rounds and statistics.

        :returns: Dictionary with comprehensive game state information
        """
        if not self.game_active:
            return {
                "game_active": False,
                "message": "No active game. Start a new game with start_game().",
            }

        current_round_info = None
        if self.current_round:
            current_round_info = {
                "round_number": self.current_round.round_number,
                "pumps": self.current_round.pumps,
                "status": self.current_round.status.value,
                "temporary_pot": self.current_round.temporary_pot,
                "pop_probability": self.current_round.pop_probability,
            }

        # Calculate statistics
        total_rounds = len(self.rounds_history)
        popped_rounds = sum(
            1 for r in self.rounds_history if r.status == BalloonStatus.POPPED
        )
        cashed_rounds = sum(
            1 for r in self.rounds_history if r.status == BalloonStatus.CASHED_OUT
        )
        avg_pumps = (
            sum(r.pumps for r in self.rounds_history) / total_rounds
            if total_rounds > 0
            else 0
        )

        return {
            "game_active": True,
            "current_round": current_round_info,
            "total_banked": self.total_banked,
            "total_rounds_played": total_rounds,
            "rounds_popped": popped_rounds,
            "rounds_cashed_out": cashed_rounds,
            "average_pumps_per_round": round(avg_pumps, 2),
            "money_per_pump": self.money_per_pump,
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_rounds_history(self) -> list[dict[str, Any]]:
        """
        Get the history of all completed rounds.

        :returns: List of dictionaries containing details of each completed round
        """
        return [
            {
                "round_number": round.round_number,
                "pumps": round.pumps,
                "status": round.status.value,
                "temporary_pot": round.temporary_pot,
                "amount_banked": round.amount_banked,
                "pop_probability": round.pop_probability,
            }
            for round in self.rounds_history
        ]

