---
name: gh-sub-switch
description: Switch the current repository's git identity (name, email, and remote URL) to a saved profile.
---

To switch the account for this repository, provide the **Profile ID** (e.g., 'main', 'sub').

I will:
1. Load the profile from `~/.gh-sub/profiles.json`.
2. Update the local `user.name` and `user.email`.
3. Update the `origin` remote URL to use the correct SSH host alias.
4. Verify the SSH connection.
