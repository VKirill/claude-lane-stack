# Edge and prohibition probes

Before a piece is accepted, probe the edges a happy-path check misses:

- empty input, one item, the maximum, one over the maximum;
- unicode (Cyrillic, emoji), very long strings, whitespace only;
- the forbidden path: what the code must refuse (no access, wrong owner, secret-shaped input) is refused with a message that says what to do;
- the legit path next to the forbidden one still works;
- concurrency: the same action twice at once;
- the slow or failing dependency: timeout, 500, no network.
