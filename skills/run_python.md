# Skill: Run a Workspace Script

- **Action Keyword:** run_python
- **Description:** Runs ONE Python file from the workspace and reports what it said — the verdict (RAN, or FAILED with the exit code), its stdout and its stderr. This is not a shell: one interpreter, one argument, and that argument is a path already reduced to the workspace, so no command from a model is ever executed. The child is bounded (MANJUEL_RUN_TIMEOUT, 60s) and is handed an environment stripped to what a Python interpreter needs, so nothing in `.env` can be read by the code it runs. Use for "run it", "does it work", "run the test", "what does it print".
- **Parameters Needed:** <filepath>The .py file in the workspace to run, e.g. probe.py</filepath>
- **Path Args:** filepath -> workspace
- **Says:** run it, run the script, run the test, does it run
