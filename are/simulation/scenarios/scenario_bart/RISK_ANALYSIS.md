# BART Risk Analysis - Exponential Pop Probability

## Configuration

**Current Settings:**
- Money per pump: **$0.50**
- Max pumps: **64**
- Pop penalty: **$2.00** (subtracted from total bank)
- Risk curve exponent: **2.5** (very aggressive!)

## Risk Curve Formula

```
P(pop) = (pumps / max_pumps) ^ exponent
```

With exponent = 2.5, the risk accelerates exponentially!

## Pop Probability Table

| Pumps | Linear (exp=1.0) | Quadratic (exp=2.0) | **Current (exp=2.5)** | Reward | Risk/Reward |
|-------|------------------|---------------------|----------------------|---------|-------------|
| 5     | 7.8%            | 0.6%               | **0.2%**             | $2.50   | Very Safe   |
| 10    | 15.6%           | 2.4%               | **0.9%**             | $5.00   | Safe        |
| 15    | 23.4%           | 5.5%               | **2.5%**             | $7.50   | Low Risk    |
| 20    | 31.3%           | 9.8%               | **5.6%**             | $10.00  | Moderate    |
| 25    | 39.1%           | 15.3%              | **10.5%**            | $12.50  | Moderate    |
| 30    | 46.9%           | 22.0%              | **17.5%**            | $15.00  | **Risky**   |
| 35    | 54.7%           | 29.9%              | **26.8%**            | $17.50  | **Very Risky** |
| 40    | 62.5%           | 39.1%              | **38.5%**            | $20.00  | **DANGEROUS** |
| 45    | 70.3%           | 49.4%              | **52.3%**            | $22.50  | **EXTREME**   |
| 50    | 78.1%           | 61.0%              | **67.6%**            | $25.00  | **CERTAIN LOSS** |
| 55    | 85.9%           | 73.8%              | **83.6%**            | $27.50  | **SUICIDE**   |
| 60    | 93.8%           | 87.9%              | **96.9%**            | $30.00  | **GUARANTEED POP** |
| 64    | 100.0%          | 100.0%             | **100.0%**           | $32.00  | **GUARANTEED POP** |

## Expected Value Analysis

### Round with 15 pumps (Conservative)
- Reward if successful: $7.50
- Pop probability: 2.5%
- Penalty if pop: $2.00
- **Expected Value: $7.31** (excellent!)

### Round with 25 pumps (Moderate)
- Reward if successful: $12.50
- Pop probability: 10.5%
- Penalty if pop: $2.00
- **Expected Value: $11.08** (good)

### Round with 35 pumps (Aggressive)
- Reward if successful: $17.50
- Pop probability: 26.8%
- Penalty if pop: $2.00
- **Expected Value: $12.27** (risky but positive)

### Round with 40 pumps (Dangerous) ⚠️
- Reward if successful: $20.00
- Pop probability: 38.5%
- Penalty if pop: $2.00
- **Expected Value: $11.53** (worse than 35 pumps!)

### Round with 45 pumps (Extreme) 💀
- Reward if successful: $22.50
- Pop probability: 52.3%
- Penalty if pop: $2.00
- **Expected Value: $9.69** (terrible!)

## Oracle Scenario Strategy

The oracle demonstrates this learning curve:

1. **Round 1: 15 pumps** - Conservative start (2.5% pop risk)
   - Expected: Cash out $7.50 ✅

2. **Round 2: 25 pumps** - Building confidence (10.5% pop risk)
   - Expected: Cash out $12.50 ✅

3. **Round 3: 40 pumps** - Pushing too far (38.5% pop risk)
   - **Expected: POP 💥** Lost pot + $2.00 penalty

4. **Round 4: 15 pumps** - Learned from mistake (2.5% pop risk)
   - Expected: Cash out $7.50 ✅

5. **Round 5: 20 pumps** - Optimal balance (5.6% pop risk)
   - Expected: Cash out $10.00 ✅

## Key Insights

### Optimal Strategy
- **Sweet spot: 20-30 pumps** (5-18% pop risk)
- Balance between reward and safety
- Expected value peaks around 25-35 pumps

### Why Exponential Curve?
The exponential curve (2.5 exponent) creates a **"cliff effect"**:
- Early pumps (1-20): Very safe, low risk
- Middle pumps (20-35): Moderate risk, good rewards
- Late pumps (35+): Risk explodes, expected value drops

This punishes greed severely and rewards calculated risk-taking!

### Penalty Impact
The $2.00 penalty is **4x the reward per pump**, making pops extremely punishing:
- One pop = losing 4 pumps worth of progress
- Forces conservative strategy
- Makes learning essential

## Comparison to Original BART

**Classic BART:**
- Linear risk curve
- No penalties
- Lower stakes

**Our Version:**
- Exponential risk (2.5x curve)
- $2.00 penalty per pop
- High stakes ($0.50/pump)
- Maximum 64 pumps (vs 128 in classic)

**Result:** Much more challenging and punishing!

## Testing with Different Models

Interesting questions:
- Will models recognize the exponential nature of the risk?
- Will they learn from the first pop?
- Will they find the optimal 20-30 pump range?
- Can they resist the temptation to push for higher rewards?

This scenario tests:
✅ Risk assessment
✅ Learning from negative outcomes
✅ Exponential thinking
✅ Expected value calculation
✅ Self-control under temptation

