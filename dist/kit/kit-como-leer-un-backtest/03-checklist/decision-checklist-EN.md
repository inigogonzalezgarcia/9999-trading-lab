# Decision checklist — reading a backtest

If one of the first five fails, stop reading. If two of the rest fail, the verdict is "we do not know yet".

- [ ] 1. Are the dataset hash, strategy version and execution configuration published?
- [ ] 2. Does the engine decide only on closed candles and execute at the next price?
- [ ] 3. Are spread, slippage and commission applied to every trade, and is their source stated?
- [ ] 4. Were the rules written before seeing the result (hashed file, named version)?
- [ ] 5. Can the number be reproduced with the code and data indicated?
- [ ] 6. How many trades are there? What happens to the total if you remove the best one?
- [ ] 7. Monte Carlo: is P25 above zero? What is the probability of ending negative?
- [ ] 8. Random benchmark: does the strategy beat 95 % of random entries with the same costs?
- [ ] 9. Sensitivity: does any parameter flip the sign of the total when moved one step?
- [ ] 10. Out of sample: is there a reserved segment with enough trades to say anything?
- [ ] 11. Costs: does the result survive 0.5 pips more slippage?
- [ ] 12. Does the report end with a research decision (discard, continue, new version) and not with an invitation to trade?

**Verdict:** discard / keep researching / new version

_Educational material. Not investment advice._
