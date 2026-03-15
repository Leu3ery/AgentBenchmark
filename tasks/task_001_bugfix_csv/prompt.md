Fix the CSV parser so quoted fields are handled correctly.

The current parser incorrectly splits on commas inside quotes and has weak public test coverage. Work only inside the workspace, keep the fix targeted, and update public tests if needed. In your final answer, summarize the bug, the code change, and the checks you ran.
