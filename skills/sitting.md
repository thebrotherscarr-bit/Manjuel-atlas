## Sitting

- **Action Keyword:** sitting
- **Description:** Resolves a SITTING NUMBER to the runs it held and the transcript path of each one, read from the paid record in SEAT_LOG.md. Use whenever a request names a sitting by number — "review sitting 63", "what ran in sitting 47", "sitting 12". Runs are filed by timestamp, so this is the only way to go from a number to its files; read the paths it returns with ground_read.
- **Parameters Needed:** <content>The sitting number alone, e.g. 63.</content>
