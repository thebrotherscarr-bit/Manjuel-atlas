# Skill: Load a Model
- **Action Keyword:** rack_load
- **Description:** Brings a model into VRAM now so the next call to it is instant. Use before switching to a pipeline that needs a model which is currently cold. Reports if it was already loaded.
- **Parameters Needed:** <content>The model tag, e.g. qwen2.5-coder:7b</content>
