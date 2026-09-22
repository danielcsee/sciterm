---
name: ci
description: Use for advancing code from dev to stage.
---

If you change any code during the ci process, use the `developer` skill to make your changes. This means checking out a dedicated branch from dev to contain your changes (name it ci/<change_description>) and merging it back to dev when you're done.

## Review

First, check git and ensure you're on the latest commit on the dev branch.

Using git, diff dev/HEAD and stage/HEAD to find all files which changed. Review all files to ensure they correspond to the project's style guidelines, and alter them to match those guidelines as needed. If you alter any files, be sure not to change the i/o behavior of any functions.

Next, advance to Test (below).

## Test

Use the /test skill: add unit tests to extend coverage where needed, then run all unit tests and ensure there are no failures.

When done, move on to Advance (below).

## Advance

If you've made any changes, merge them back to dev. Then, merge the latest commit from dev into stage. After that, increment the version number by creating a tag on the new stage commit with the updated version number.

NEVER push stage to the github remote without human approval. Doing so would trigger a github action which deploys the code to production, and human approval is REQUIRED before that happens!

Finally, print a summary of what you did and call out any potential problems.
