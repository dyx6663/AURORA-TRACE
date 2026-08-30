# AURORA TRACE Design Decisions

## ADR-001 · Evidence is a first-class domain object

**Decision:** Store causal event metadata together with human-readable details, rather than treating logging as an optional print statement.

**Reason:** A reviewer should be able to answer which decision caused a tool call, which files were affected, and which verification result supports completion.

**Trade-off:** Event records are larger and require schema discipline. This is accepted because auditability is the project’s defining research direction.

## ADR-002 · Completion is a local policy decision

**Decision:** A model `finish` request is only a proposal. `complete_run()` evaluates the Acceptance Contract and either emits a completion event or blocks it.

**Reason:** Language output is not a substitute for test execution.

**Trade-off:** Some legitimate tasks without a failing baseline need a richer contract. The current prototype intentionally uses a bug-repair contract and should extend the contract by task type rather than weakening the global rule.

## ADR-003 · Each Run receives a copied workspace

**Decision:** Never mutate the selected source project directly. Copy it into `.runs/<run_id>/` first.

**Reason:** This makes repeated demonstrations independent and allows the original fixture to remain a trustworthy baseline.

**Trade-off:** Copying consumes storage and is not a complete OS-level sandbox. The current safety boundary is explicit filesystem and command policy, not a claim of hostile-code isolation.

## ADR-004 · Exact replacement is the default patch primitive

**Decision:** `replace_text` requires exactly one match and returns a unified Diff.

**Reason:** A small, deterministic change is easier to review, attribute and replay than unconstrained text generation.

**Trade-off:** Complex refactors require a richer patch format in a future version. The restriction is intentional for the evaluation fixture.

## ADR-005 · Mock and Live share the factual executor

**Decision:** Mock mode changes the decision source, not the executor, event format or completion policy.

**Reason:** The no-key demo must demonstrate the same engineering claims as Live mode wherever possible.

**Trade-off:** Mock steps are deterministic rather than model-generated. This is disclosed in the UI and documentation; it is used for repeatability, not presented as autonomous planning.

## ADR-006 · Framework depth follows evaluation value

**Decision:** Prioritize Registry, Run persistence, Evidence Graph, verification gates and tests before Subagents, Plugins and MCP.

**Reason:** The former directly supports the project’s research question and can be demonstrated with local evidence. The latter would increase feature count without necessarily improving the central claim.

## ADR-007 · No historical fabrication

**Decision:** The repository records real commits and real verification results. It does not manufacture a staged development history, alter timestamps or invent a public repository address.

**Reason:** Reproducibility and academic integrity are part of the project evaluation, not post-processing decoration.
