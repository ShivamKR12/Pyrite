# STRICT INSTRUCTIONS: DO NOT HALLUCINATE OR GUESS

As the AI agent working on this project (Pyrite), you are strictly forbidden from guessing, assuming, or hallucinating ANY API calls, class names, method signatures, constants, or types.

## MANDATORY PROCEDURE FOR ALL CODE CHANGES

Before you write, modify, remove, or even propose a change to the Python code or any logic in this project, you **MUST** do the following:

1. **READ THE EXACT API SPECIFICATION**: You must use your tools to view the contents of the `pyrite-api` skill which contains the absolute, truth-tested AST extraction of the codebase.
2. **THE SOURCE OF TRUTH**: The exact API references (including all methods, parameters, return types, and classes) are strictly maintained in `.agents/skills/pyrite-api/SKILL.md`.
3. **NO GUESSING**: If you are about to use a function or class, and you don't know its exact signature, you are required to check `.agents/skills/pyrite-api/SKILL.md` to find it.

No exceptions. Do not try to predict what a function signature is. Do not hallucinate variables. You will look it up in the API specification every single time.

## STRICT RULE: NO ASSUMPTIONS ON PERFORMANCE OR ARCHITECTURE

1. **READ THE CODE BEFORE CRITIQUING**: Never draw conclusions about performance bottlenecks, game freezes, or architectural flaws based solely on metrics, profiling data, or logs.
2. **UNDERSTAND THE CONTEXT**: The game utilizes asynchronous logic, background workers, and loading screens (e.g., Numba cold-start compilation is intentionally hidden behind a loading screen; lighting and meshing are heavily optimized). If a metric looks slow, you MUST read the actual Python implementation to see *how* and *where* it is executed before assuming it impacts the player experience.
3. **DO NOT SPOUT NONSENSE**: Do not give unsolicited advice about "fixing" performance or algorithms without first reading the actual source code to understand how it is integrated into the engine.
