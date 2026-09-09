# Skill: Unload a Model
- **Action Keyword:** rack_unload
- **Description:** Frees VRAM by evicting a loaded model. Use when the card is full and a large model is no longer needed. Refuses to unload a model this ground does not declare, because that model belongs to another client and evicting it would cost them a reload.
- **Parameters Needed:** <content>The model tag to unload</content>
