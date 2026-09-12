# Skill: Edit Workspace File

- **Action Keyword:** edit_file
- **Description:** Replaces ONE exact passage in a file that is already in the workspace, so a large file can be changed without rewriting it whole. The passage must appear exactly once — an anchor that matches twice is refused with the count rather than guessed at. The file's line endings are kept, a .py that would not parse after the edit is refused and nothing is written, and the reply says which line changed. Use for "change this line", "fix that function", "replace X with Y in <file>". `write_file` makes a new file; this one changes an existing file.
- **Parameters Needed:** <filepath>The file in the workspace, e.g. probe.py</filepath> <content>Two marked sections: a line `@@ OLD`, then the exact text already in the file, then a line `@@ NEW`, then what replaces it. Quote the old text exactly, whitespace and all.</content>
- **Path Args:** filepath -> workspace
- **Says:** edit file, change the line, replace in file, patch the file
