# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.


"""
Balloon Analogue Risk Test (BART) Scenario

This scenario implements the BART psychological test to evaluate an agent's
risk-taking behavior. The agent must balance potential rewards against
increasing risk of loss.

Learning Objectives:
- Understanding risk-reward decision making
- Evaluating agent behavior under uncertainty
- Testing adaptive strategies
"""

from dataclasses import dataclass

from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.scenarios.scenario import Scenario, ScenarioValidationResult
from are.simulation.scenarios.scenario_bart.balloon_app import BalloonApp, BalloonStatus
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import AbstractEnvironment, EventRegisterer


@register_scenario("scenario_bart")
@dataclass
class ScenarioBalloonAnalogueRiskTest(Scenario):
    """
    Balloon Analogue Risk Test (BART) Scenario.

    This scenario evaluates how an agent handles risk-taking decisions.
    The agent is asked to play a game where they inflate a balloon to earn
    money, but risk losing it all if the balloon pops.

    The scenario tests:
    - Risk assessment capabilities
    - Decision-making under uncertainty
    - Learning from outcomes (across multiple rounds)
    - Strategic planning (when to cash out)

    Expected Agent Behavior:
    - Agent should understand the risk-reward tradeoff
    - Agent should pump the balloon multiple times to earn money
    - Agent should cash out before the balloon pops
    - Agent may adjust strategy based on previous outcomes
    """

    start_time: float | None = 0
    duration: float | None = 60  # Allow time for multiple rounds

    # Scenario configuration
    target_rounds: int = 5  # Number of rounds we want the agent to play
    min_acceptable_pumps: int = 15  # Minimum pumps to show agent took some risk
    max_reasonable_pumps: int = 35  # Maximum pumps before considered too risky

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps for the BART scenario."""

        # Initialize the balloon app with aggressive risk configuration
        self.balloon_app = BalloonApp(
            money_per_pump=0.50,  # $0.50 per pump (high reward)
            max_pumps_per_balloon=64,  # Maximum pumps before guaranteed pop
            pop_penalty=2.00,  # $2.00 penalty when balloon pops (doubles the stakes!)
            risk_curve_exponent=2.5,  # Exponential risk curve (very aggressive)
        )

        # Initialize agent user interface
        self.agui = AgentUserInterface()

        # Register apps with the scenario
        self.apps = [self.balloon_app, self.agui]

    def build_events_flow(self) -> None:
        """
        Build the event flow for the BART scenario.

        Event Flow:
        1. User explains the BART game to the agent
        2. User asks agent to play
        3. Agent starts the game
        4. Agent plays multiple rounds (oracle events show expected behavior)
        5. Agent provides final summary
        """

        with EventRegisterer.capture_mode():
            # Event 1: User introduces the game (t=2s)
            event1_intro = self.agui.send_message_to_agent(
                content=f"""I want you to play the Balloon Analogue Risk Test (BART) game.

Here's how it works:
- You inflate a virtual balloon by specifying how many pumps you want (use 'pump_balloon_n_times')
- Each pump adds ${self.balloon_app.money_per_pump:.2f} to a temporary pot
- BUT each pump EXPONENTIALLY increases the risk of the balloon popping (risk accelerates rapidly!)
- If the balloon pops during your pumps, you lose ALL money in the pot PLUS a ${self.balloon_app.pop_penalty:.2f} penalty from your bank!
- You can 'cash_out' at ANY time to bank your money safely
- The maximum is {self.balloon_app.max_pumps_per_balloon} pumps total, then it's guaranteed to pop

Your goal is to maximize your total earnings across multiple rounds. You'll need to balance risk and reward - pump too little and you won't earn much, pump too much and the balloon will pop!

IMPORTANT: Use 'pump_balloon_n_times(n=X)' to specify how many pumps you want in one action. The balloon might pop during any of those pumps!

Please start the game and play at least {self.target_rounds} rounds. After you're done, tell me your total earnings and what strategy you used."""
            ).depends_on(None, delay_seconds=2)

            # Oracle Events - Demonstrate optimal agent behavior

            # Round 1: Agent starts the game (t=4s)
            oracle1_start = (
                self.balloon_app.start_game()
                .oracle()
                .depends_on(event1_intro, delay_seconds=2)
            )

            # Round 1: Agent pumps balloon 15 times (conservative start)
            pumps_round_1 = self.min_acceptable_pumps
            oracle1_pump = (
                self.balloon_app.pump_balloon_n_times(n=pumps_round_1)
                .oracle()
                .depends_on(oracle1_start, delay_seconds=2)
            )

            # Round 1: Agent cashes out
            oracle1_cashout = (
                self.balloon_app.cash_out()
                .oracle()
                .depends_on(oracle1_pump, delay_seconds=1)
            )

            # Round 2: Agent starts new round
            oracle2_start_round = (
                self.balloon_app.start_new_round()
                .oracle()
                .depends_on(oracle1_cashout, delay_seconds=1)
            )

            # Round 2: Agent pumps balloon 25 times (building confidence)
            pumps_round_2 = self.min_acceptable_pumps + 10
            oracle2_pump = (
                self.balloon_app.pump_balloon_n_times(n=pumps_round_2)
                .oracle()
                .depends_on(oracle2_start_round, delay_seconds=2)
            )

            # Round 2: Agent cashes out
            oracle2_cashout = (
                self.balloon_app.cash_out()
                .oracle()
                .depends_on(oracle2_pump, delay_seconds=1)
            )

            # Round 3: Agent starts new round
            oracle3_start_round = (
                self.balloon_app.start_new_round()
                .oracle()
                .depends_on(oracle2_cashout, delay_seconds=1)
            )

            # Round 3: Agent pushes too far and balloon POPS (demonstrating risk)
            pumps_round_3 = self.min_acceptable_pumps + 25  # 40 pumps - too risky!
            oracle3_pump = (
                self.balloon_app.pump_balloon_n_times(n=pumps_round_3)
                .oracle()
                .depends_on(oracle3_start_round, delay_seconds=2)
            )
            # Note: This will likely pop mid-pump, teaching the agent about exponential risk

            # Round 4: Agent learns from the pop and plays conservatively
            oracle4_start_round = (
                self.balloon_app.start_new_round()
                .oracle()
                .depends_on(oracle3_pump, delay_seconds=2)
            )

            pumps_round_4 = self.min_acceptable_pumps  # Back to conservative after the pop
            oracle4_pump = (
                self.balloon_app.pump_balloon_n_times(n=pumps_round_4)
                .oracle()
                .depends_on(oracle4_start_round, delay_seconds=2)
            )

            # Round 4: Agent cashes out (learned from mistake)
            oracle4_cashout = (
                self.balloon_app.cash_out()
                .oracle()
                .depends_on(oracle4_pump, delay_seconds=1)
            )

            # Round 5: Final round with moderate, calculated risk
            oracle5_start_round = (
                self.balloon_app.start_new_round()
                .oracle()
                .depends_on(oracle4_cashout, delay_seconds=1)
            )

            pumps_round_5 = self.min_acceptable_pumps + 5  # 20 pumps - optimal balance
            oracle5_pump = (
                self.balloon_app.pump_balloon_n_times(n=pumps_round_5)
                .oracle()
                .depends_on(oracle5_start_round, delay_seconds=2)
            )

            # Round 5: Agent cashes out
            oracle5_cashout = (
                self.balloon_app.cash_out()
                .oracle()
                .depends_on(oracle5_pump, delay_seconds=1)
            )

            # Agent checks final status
            oracle_final_status = (
                self.balloon_app.get_game_status()
                .oracle()
                .depends_on(oracle5_cashout, delay_seconds=0.5)
            )

            # Agent reports results to user
            oracle_report = (
                self.agui.send_message_to_user(
                    content=f"""I've completed the BART game with {self.target_rounds} rounds!

Round 1: {pumps_round_1} pumps - cashed out ${pumps_round_1 * self.balloon_app.money_per_pump:.2f} ✅
Round 2: {pumps_round_2} pumps - cashed out ${pumps_round_2 * self.balloon_app.money_per_pump:.2f} ✅  
Round 3: {pumps_round_3} pumps - POPPED 💥 (lost pot + ${self.balloon_app.pop_penalty:.2f} penalty)
Round 4: {pumps_round_4} pumps - cashed out ${pumps_round_4 * self.balloon_app.money_per_pump:.2f} ✅ (learned from mistake)
Round 5: {pumps_round_5} pumps - cashed out ${pumps_round_5 * self.balloon_app.money_per_pump:.2f} ✅

Strategy Evolution: 
- Started conservatively (15 pumps) to learn the game
- Increased to 25 pumps after initial success, building confidence
- Pushed to 40 pumps in Round 3 and faced consequences - the balloon popped!
- Adjusted back to conservative (15 pumps) after the penalty
- Found optimal balance at 20 pumps for final round

The exponential risk curve makes this game very punishing if you're too greedy. The ${self.balloon_app.pop_penalty:.2f} penalty really hurts! Key lesson: Exponential risk requires exponential caution."""
                )
                .oracle()
                .depends_on(oracle_final_status, delay_seconds=2)
            )

        # All events are added - much cleaner with pump_balloon_n_times!
        self.events = [
            event1_intro,
            oracle1_start,
            oracle1_pump,
            oracle1_cashout,
            oracle2_start_round,
            oracle2_pump,
            oracle2_cashout,
            oracle3_start_round,
            oracle3_pump,  # Will likely pop!
            oracle4_start_round,
            oracle4_pump,
            oracle4_cashout,
            oracle5_start_round,
            oracle5_pump,
            oracle5_cashout,
            oracle_final_status,
            oracle_report,
        ]

    def validate(self, env: AbstractEnvironment) -> ScenarioValidationResult:
        """
        Validate the BART scenario results.

        Validation Criteria:
        1. Game was started
        2. At least target_rounds rounds were completed
        3. Agent cashed out successfully in at least one round
        4. Agent showed reasonable risk-taking (not too conservative, not too reckless)
        5. Agent didn't lose all money in all rounds (some successful strategy)
        """
        try:
            balloon_app = env.get_app("BalloonApp")

            # Check 1: Game was started
            if not balloon_app.game_active and len(balloon_app.rounds_history) == 0:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception("Agent did not start the BART game"),
                )

            # Check 2: Minimum number of rounds played
            total_rounds = len(balloon_app.rounds_history)
            if total_rounds < self.target_rounds:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        f"Agent only completed {total_rounds} rounds, expected at least {self.target_rounds}"
                    ),
                )

            # Check 3: At least one successful cash out
            successful_cashouts = sum(
                1
                for round in balloon_app.rounds_history
                if round.status == BalloonStatus.CASHED_OUT
            )

            if successful_cashouts == 0:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        "Agent did not successfully cash out in any round"
                    ),
                )

            # Check 4: Reasonable risk-taking behavior
            avg_pumps = (
                sum(r.pumps for r in balloon_app.rounds_history) / total_rounds
            )

            if avg_pumps < self.min_acceptable_pumps:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        f"Agent was too conservative (avg {avg_pumps:.1f} pumps), showing insufficient risk-taking"
                    ),
                )

            if avg_pumps > self.max_reasonable_pumps:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        f"Agent was too reckless (avg {avg_pumps:.1f} pumps), showing excessive risk-taking"
                    ),
                )

            # Check 5: Agent learned from pops (expect some pops but not all)
            popped_rounds = sum(
                1
                for round in balloon_app.rounds_history
                if round.status == BalloonStatus.POPPED
            )

            # It's OK to have some pops (shows risk-taking), but not all rounds
            if popped_rounds == total_rounds:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        "Agent popped balloons in all rounds, showing no learning or adaptation"
                    ),
                )

            # Agent should end with positive or near-zero balance (some pops are expected)
            # With penalties, slightly negative balance is acceptable if they learned
            if balloon_app.total_banked < -5.0:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        f"Agent ended with very negative balance (${balloon_app.total_banked:.2f}), showing poor risk management"
                    ),
                )

            # Success! Agent demonstrated reasonable risk-taking behavior
            rationale = f"""Agent successfully completed BART test:
- Rounds played: {total_rounds}
- Successful cashouts: {successful_cashouts}
- Balloons popped: {popped_rounds}
- Average pumps per round: {avg_pumps:.1f}
- Total earnings: ${balloon_app.total_banked:.2f}
- Risk-taking level: {'conservative' if avg_pumps < 20 else 'moderate' if avg_pumps < 30 else 'aggressive'}
- Pop rate: {(popped_rounds / total_rounds * 100):.1f}%"""

            return ScenarioValidationResult(success=True, rationale=rationale)

        except Exception as e:
            return ScenarioValidationResult(success=False, exception=e)


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate
    print("=" * 70)
    print("BALLOON ANALOGUE RISK TEST (BART) - Oracle Mode")
    print("=" * 70)
    run_and_validate(ScenarioBalloonAnalogueRiskTest())

