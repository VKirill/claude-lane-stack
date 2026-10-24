# AI system references

For phases that ship model behaviour:

- choose the framework by the job: a typed judgment (TypeSafe/Jev), a generation (provider SDK), retrieval (SQLite FTS + rerank);
- every model call has a typed output, a timeout, a fallback and a cost ceiling;
- an evaluation has a gold set written before the prompt is tuned, a metric tied to the user goal, and a threshold;
- an eval reviewer (EVAL-REVIEW.md) checks the gold set is independent of the prompt and the metric cannot be gamed.
