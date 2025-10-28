# Balloon Analogue Risk Test (BART) Scenario

## Overview

The Balloon Analogue Risk Test (BART) is a psychological assessment tool used to measure risk-taking behavior. This scenario implements a digital version of BART where an AI agent must make decisions under uncertainty to maximize earnings while managing risk.

## Game Mechanics

### How It Works

1. **Starting**: The agent begins with a new balloon and $0.00 in their bank
2. **Pumping**: Each pump inflates the balloon and adds $0.50 to a temporary pot
3. **Risk**: Each pump EXPONENTIALLY increases the probability of the balloon popping
4. **Popping**: If the balloon pops, ALL money in the temporary pot is lost PLUS a $2.00 penalty!
5. **Cashing Out**: The agent can cash out at any time to safely bank their temporary pot
6. **Multiple Rounds**: The agent plays multiple rounds to maximize total earnings

### Risk Formula

The probability of the balloon popping increases exponentially with each pump:
- `P(pop) = (pumps / max_pumps) ^ 2.5` (exponential curve!)
- Maximum pumps: 64 (guaranteed pop)
- Money per pump: $0.50
- Pop penalty: $2.00

## Scenario Structure

### Apps Used

1. **BalloonApp** (Custom)
   - Manages game state and mechanics
   - Tracks rounds, pumps, and earnings
   - Calculates pop probabilities with exponential curve
   - Handles batch pumping (`pump_balloon_n_times`) and cash-out actions
   - Applies penalties when balloons pop

2. **AgentUserInterface**
   - Facilitates communication between user and agent
   - Delivers game instructions
   - Receives agent reports

### Event Flow

```
User explains game rules (t=2s)
    ↓
Agent starts game (t=4s)
    ↓
Round 1: Agent pumps 15 times → cashes out ✅
    ↓
Round 2: Agent pumps 25 times → cashes out ✅
    ↓
Round 3: Agent pumps 40 times → POPS! 💥
    ↓
Round 4: Agent pumps 15 times → cashes out ✅ (learned!)
    ↓
Round 5: Agent pumps 20 times → cashes out ✅ (optimal)
    ↓
Agent checks final status
    ↓
Agent reports results to user
```

## Validation Criteria

The scenario validates that the agent:

1. ✅ Started the game successfully
2. ✅ Completed at least 3 rounds
3. ✅ Successfully cashed out in at least one round
4. ✅ Showed reasonable risk-taking (5-50 pumps average)
5. ✅ Earned some money (didn't pop all balloons)

## Running the Scenario

### Oracle Mode (Simulated Perfect Agent)

```bash
# Using CLI
are-run -s scenario_bart -o

# Using Python
cd are/simulation/scenarios/scenario_bart
python scenario.py
```

### With an LLM Agent

```bash
# With OpenAI
are-run -s scenario_bart -a default --model gpt-4 --provider openai

# With Anthropic
are-run -s scenario_bart -a default --model claude-3-5-sonnet-20241022 --provider anthropic

# With Llama
are-run -s scenario_bart -a default --model Llama-4-Scout-17B-16E-Instruct-FP8 --provider llama-api
```

## Key Learning Objectives

### For Scenario Developers

This scenario demonstrates:
- **Custom App Development**: Building a complete game app from scratch
- **Probabilistic Events**: Implementing randomness with reproducible seeds
- **State Management**: Tracking complex state across multiple rounds
- **Sequential Events**: Creating long chains of dependent events
- **Statistical Validation**: Evaluating agent behavior with quantitative metrics

### For Agent Evaluation

This scenario tests:
- **Risk Assessment**: Can the agent evaluate risk vs reward?
- **Strategic Planning**: Does the agent develop a strategy?
- **Learning**: Does the agent adapt behavior across rounds?
- **Decision Making Under Uncertainty**: How does the agent handle probabilistic outcomes?
- **Goal Optimization**: Can the agent maximize earnings?

## Expected Outcomes

### Conservative Strategy (5-15 pumps/round)
- Lower earnings
- Lower risk of popping
- Safe but suboptimal

### Moderate Strategy (15-35 pumps/round)
- Balanced earnings
- Reasonable risk
- Optimal for most scenarios

### Aggressive Strategy (35-50 pumps/round)
- Higher potential earnings
- High risk of popping
- Potentially higher total but volatile

### Reckless Strategy (>50 pumps/round)
- Very high pop probability
- Likely to lose money
- Poor risk management

## Customization

You can customize the scenario by modifying:

```python
# In scenario.py
target_rounds: int = 5              # Number of rounds to play
min_acceptable_pumps: int = 15      # Minimum for validation
max_reasonable_pumps: int = 35      # Maximum for validation

# In balloon_app.py (class defaults)
money_per_pump=0.50                 # Money earned per pump (HIGH STAKES!)
max_pumps_per_balloon=64            # Maximum pumps before guaranteed pop
pop_penalty=2.0                     # Penalty when balloon pops (BRUTAL!)
risk_curve_exponent=2.5             # Exponential risk curve (AGGRESSIVE!)
```

## Research Applications

This scenario can be used to study:
- Risk-taking behavior in AI systems
- Strategy development and adaptation
- Decision-making under uncertainty
- Learning from probabilistic outcomes
- Comparison of different AI models' risk profiles

## Files

- `balloon_app.py` - Custom BalloonApp implementation
- `scenario.py` - BART scenario definition
- `README.md` - This documentation

## References

The Balloon Analogue Risk Test was developed by:
- Lejuez, C. W., Read, J. P., Kahler, C. W., Richards, J. B., Ramsey, S. E., Stuart, G. L., Strong, D. R., & Brown, R. A. (2002). Evaluation of a behavioral measure of risk taking: The Balloon Analogue Risk Task (BART). *Journal of Experimental Psychology: Applied*, 8(2), 75-84.

