---
name: task-queue
description: Use to execute tasks from the aiutils task-queue.
---

Use the aiutils api to fetch an unfinished task from the task queue. Fetch the first not-started task that is not blocked by any other task. If the only not-started tasks are blocked, ask the human developer for assistance.

Note: when implementing task-queue, you will almost always be working concurrently alongside other agents in the same project directory. As such, you may encounter unexpected concurrency bugs preventing you from working on a ticket. If that happens, follow 'Resolving Unexpected Dependencies' below.

# Implementing

Create a new worktree and feature branch. Update your ticket to IN_PROGRESS using the aiutils api, and assign your branch name to the 'branch' field of the ticket. Then use the /developer skill to implement the task to completion. When you're done, mark the task as 'COMPLETE' using the aiutils api. Merge the branch back to 'dev' and clean up your worktree when you're done.

Never amend task state by writing to the aiutils sqlite database directly. Never take on work claimed by another agent without express human approval. Only use the aiutils api to modify task state. Ensure that your updates are an honest reflection of your progress. For example, do not mark tasks as COMPLETE unless you are actually done. 

Continue taking tasks and implementing them like this until there are no more NOT_STARTED tasks left to do. If you encounter unresolvable limitations with the aiutils api, ask the human developer for assistance. 

When you're finished, output a summary of what you did. Then, fetch all blocked and orphaned tickets and ask the human developer what to do next. If you encountered difficulties, say what they were and propose process improvements for the future.

# Resolving Unexpected Dependencies

If you can't start work on your ticket because you're waiting on a concurrent agent to finish necessary pre-work, do the following:

1. Commit any changes you've made to your feature branch.
2. Release the ticket using aiutils release_ticket tool.
3. Remove your worktree.
4. Take a new unblocked ticket from aiutils and begin work on that.

# Claim credentials

Claiming a ticket issues a secret credential proving that you are the ticket's current holder. The ticket's credential, not its name, authorizes you to update the ticket. Only the credential's hash is stored; you will not be able to request the same credential again, so make sure to hold it for the life of the ticket.

Claim with `--json` and keep what it returns:

    aiutils ticket-next --claimed-by <your-agent-id> --json

Pass the credential on every write to that ticket, including the one that completes it:

    aiutils ticket-update <id> --status COMPLETE --notes "..." --claim-credential <secret>
    aiutils ticket-release <id> --reason "..." --claim-credential <secret>

Never write a credential into ticket notes, a commit message, a branch name, or any file. Whoever holds the credential can write to your ticket.

A write refused with a claim conflict means you are either not passing the credential or you are no longer the ticket's holder. If you get a claim conflict, simply take a different ticket.

A ticket claimed before credentials existed carries no credential and accepts writes without one until it is claimed.

You cannot change a ticket's owner with `ticket-update`.

A lost credential cannot be recovered. If you lose your credential, the ticket will become orphaned in an hour, and then you or another agent can claim it again.

# Taking over abandoned work

`aiutils tickets-orphans` lists IN_PROGRESS tickets nobody has updated for over an hour. Updating your ticket as you work resets its clock. You can claim an orphaned ticket with the following command:

    aiutils ticket-claim-orphan <id> --claimed-by <your-agent-id> --json