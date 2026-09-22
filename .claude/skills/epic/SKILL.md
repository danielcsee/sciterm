---
name: epic
description: Use to break complex tasks into atomic subtasks.
---

Read long-form project descriptions and break them into ticket-sized subtasks. Use aiutils to insert each task as a ticket into the aiutils sqlite database. 

Do not execute the epic or any tasks you create. Just create the tasks and register them with aiutils.


## Epics

An epic is a long-form description that includes multiple related features. It may include frontend, backend, database, or api calls. It may describe or refer to systems that don't exist yet. It may also make implied assumptions about project components that aren't clearly described.


## How To Break Down An Epic

Start by identifying each distinct architectural part of the project. For example, the architecture of a consumer web application will likely involve distinct frontend, backend, and database components, even if these are never directly described.

Second, identify the major features the epic requires. Identify how each feature relates to the project's architectural components. For example, a "post blog update" feature will touch the frontend, backend, and database architectures.

For each feature, generate an list of actionable tasks that describes how to implement the feature, based on the architecture you identified. Organize your tasks in priority order: for example, to write a blog application, the "create database" task must come before the "read blog update" task, because a blog update cannot be read if there's no database to store it in. Make sure to assign the same 'feature' name for all tasks related to the same feature, and mark one task as 'blocked' by another task when appropriate.

Use the aiutils api to insert each task into the aiutils task database.

## Conclusion

Finally, print a summary of what you did and call out any potential problems.
