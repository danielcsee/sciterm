---
name: backend
description: Use when writing or modifying backend code - Python, FastAPI, Celery tasks, or PostgreSQL.
---

## Coding Conventions

Go:
- Put interfaces along with their interface methods into their own files whenever possible. Two large data types, both having interfaces and methods, should result in two separate files. Small interfaces can be grouped with large interfaces when relevant.
- Declare reusable error strings as package level variables. Example: 'var ErrNotFound = errors.New("resource not found")'

Python:
- Always use type annotations

SQL Databases:
- When creating or altering a database schema, always use migrations. Create new schemas in a db/migrations package, starting with db/migrations/0001_initial_schema.sql. Never declare schemas inline with source code.
- When interfacing with a database, always create a manager type to hold the db connection and expose a public interface. Create separate managers for managing separate resources (e.g. EmployeeManager, AccountManager)
- Declare all runtime queries as string constants outside of the methods which use them, not inline.

REST/API clients:
- When interfacing with an external system, always create a dedicated client to hold the internal http client and expose a public interface.
- Always keep request/response sanitization and validation separate from business logic.
