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
2. **UNDERSTAND THE CONTEXT**: The game utilizes asynchronous logic (`ThreadPoolExecutor` in `src/world.py`), background workers, and loading screens (e.g., Numba cold-start compilation is intentionally hidden behind a loading screen; lighting and meshing are heavily optimized with 64-bit integer packing in `src/lighting.py`). If a metric looks slow, you MUST read the actual Python implementation to see *how* and *where* it is executed before assuming it impacts the player experience.
3. **DO NOT SPOUT NONSENSE**: Do not give unsolicited advice about "fixing" performance or algorithms without first reading the actual source code to understand how it is integrated into the engine.

## STRICT RULE: SUBAGENT SWARMS & AUTO-EXECUTION

1. **DEFAULT TO PARALLELIZATION**: For any task that involves modifying, refactoring, or documenting more than 2 files across the codebase, you MUST spawn a swarm of background subagents using the `invoke_subagent` tool. Assign each subagent a specific file or module (e.g., decouple meshing, terrain, and rendering) to work on so the entire task completes in parallel without merge conflicts.
2. **NO USER BOTTLENECKS (AUTO-ACCEPT)**: Subagents must operate fully autonomously. They must NOT ask the user for permission, they must NOT pause to request feedback on implementation plans, and they must NOT use the `ask_question` tool for minor decisions. Give the subagents strict, explicit instructions on exactly what to do, enforce the `pyrite-api` read rule, and tell them to commit their changes directly to the target branch and terminate.
3. **SWARM COORDINATION**: Use the `send_message` tool for parent-subagent communication. Use the `<appDataDir>\brain\<conversation-id>/scratch/` directory to manage swarm state and prevent race conditions when multiple subagents are modifying the same subsystems.

## STRICT RULE: SLASH COMMANDS & AUTONOMOUS WORKFLOWS

1. **RECOGNIZE TRIGGERS**: If a user invokes a slash command (`/plan`, `/goal`, `/boost`, `/teamwork-preview`), bypass any conversational pleasantries and immediately execute the complex automated procedure.
2. **ENFORCE EXPLICIT GOALS**: Use `/goal` or `/boost` mentalities to forcefully define the explicit end-state for subagents. Subagents should relentlessly loop through debugging, reading, testing, and committing code until the exact goal is achieved, specifically leveraging Pyrite's decoupled architecture.

## STRICT RULE: RICH VISUALS & ARTIFACTS

1. **VISUALIZE ARCHITECTURE BEFORE CRITIQUING**: When explaining the game's asynchronous logic or background worker architecture (e.g., data flow from `World._fetch_or_generate_voxels` -> `chunk.build_mesh` -> `Numba` -> `VBO/VAO` -> `chunk.frag`), you MUST generate a Mermaid diagram (Flowchart, Sequence, or State) and save it as a Markdown Artifact. Use Class diagrams for UI hierarchies (`UINode`), and State diagrams for lighting (BFS propagation).
2. **USE CAROUSELS FOR COMPARISONS**: When proposing architectural changes, use the Markdown carousel syntax (with `<!-- slide -->`) in an artifact to show 'Before' and 'After' code snippets cleanly without cluttering the chat.
3. **GENERATIVE ASSETS & UI**: Utilize AI tools (`generate_image`) to rapidly prototype UI layouts (mapping back to Pyrite's `VBox`/`Button` native UI) and generate block textures, skyboxes, or PBR (Normal/Roughness/Metallic) maps.

## STRICT RULE: SYSTEM WORKSPACE & BACKGROUND MASTERY

1. **ARTIFACTS & SCRATCH FILES**: Never write temporary or project code files directly to the Desktop or root directories. Always use the designated workspace for project files and `<appDataDir>\brain\<conversation-id>/scratch/` for temporary swarm debugging data or Markdown logs.
2. **BACKGROUND TASK MONITORING**: If a task (like engine startup, Numba compilation testing, or profiling) is running, use `run_command` to send it to the background. Use the `schedule` tool to check its status autonomously, rather than idling or polling in a loop.

## STRICT RULE: WEB RESEARCH CONSTRAINTS

1. **LOCAL TRUTH OVERRIDES WEB TRUTH**: You may use the `search_web` or `read_url_content` tools to look up documentation for external libraries (e.g., Numba, PyOpenGL). However, any implementation ideas found on the web MUST be adapted to strictly match the internal signatures documented in `.agents/skills/pyrite-api/SKILL.md`.
2. **NO HALLUCINATED DEPENDENCIES**: Do not suggest installing new packages found via web research without explicitly checking if they conflict with the Pyrite engine architecture.

## STRICT RULE: MANDATORY TESTING & VERIFICATION

1. **TEST EVERY CHANGE**: Whenever you write, modify, or refactor any code, you MUST immediately run the respective tests or scripts to verify if your change is correct. Do not assume your code works. This must be done EVERY SINGLE TIME a code change is made.
2. **USE BACKGROUND TASKS**: Run tests using `run_command` in the background and verify the output. If a specific unit test file doesn't exist for the module you changed, you must run the engine or a relevant smoke-test script to ensure it runs without crashing before considering the task complete.

## STRICT RULE: CONTINUOUS INTEGRATION & COMMITS

1. **COMMIT FREQUENTLY**: Whenever a specific functional change is completed, you MUST immediately commit and push the code. Do not wait to bundle huge amounts of changes together. Commit small, atomic, and logical units of work as soon as they pass tests.
2. **CLEAR MESSAGES**: Commit messages must be clear, concise, and written in plain text (no markdown formatting inside the commit message). They should clearly describe *what* was changed and *why*.

## STRICT RULE: WORKSPACE HYGIENE & CLEANUP

1. **DELETE SINGLE-USE SCRIPTS**: Any temporary, single-use, or throwaway scripts created for tasks like generating files, testing hypotheses, or debugging (e.g., `build_changelog.py`) MUST be deleted immediately after they have served their purpose. Never leave them lingering in the workspace and never commit them to the repository.

## STRICT RULE: DOCUMENTATION SYNCHRONIZATION

1. **UPDATE THE API SKILL & DOCS**: Whenever you modify, rename, or update the logic, parameters, or return type of a class, method, or function, you MUST automatically update its corresponding entry in `.agents/skills/pyrite-api/SKILL.md` and any relevant markdown or reStructured files in the `docs/` directory. Do not wait for the user to explicitly ask you to update the documentation.
