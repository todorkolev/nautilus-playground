Apply the principles from the "Code Complete" book by uncle Bob (Robert C. Martin):
- Write simple, clean code (KISS)
- Avoid code duplication (DRY)
- Use SOLID principles:
  - Single Responsibility: Each class should have one purpose
  - Open/Closed: Open for extension, closed for modification
  - Liskov Substitution: Derived classes must be substitutable
  - Interface Segregation: Many client-specific interfaces over general-purpose
  - Dependency Inversion: Depend on abstractions, not concretions
- Prefer composition over inheritance
- Code to interfaces, not implementations
- Encapsulate changing parts

When taking architectural decisions, prioritize for (roughly in order of 'weighting'):
- Reliability
- Performance
- Modularity
- Testability
- Maintainability
- Deployability
Also:
- Apply Design Patterns when appropriate

Strive for writing code that is:
- Elegant
- Efficient
- Readable
- Maintainable
Also:
- Favor clarity over brevity
- Write self-documenting code with clear variable and function names
- Use meaningful and consistent naming conventions
- Keep functions small and focused on a single task
- Document complex algorithms and important design decisions
- Avoid global variables and state when possible
- Practice defensive programming
- Use assertions to catch programmer errors early
- Use meaningful error messages and exceptions
- Follow the principle of "fail fast" to catch errors as early as possible
- Follow the Boy Scout Rule: Leave the code better than you found it

General rules:
- Never apply patches but fix the underlying issues and root causes.
- Never read or write in .env files. They should be accessed strictly by the user.
- When you need a temporary script to test a hypothesis, write it as a command in the terminal - don't create a file for it if possible.
- When debugging and looking for a particular log messages, use grep to filter the terminal output.

Tool use:
- Use the context7 tool on each step to research the latest documentation for the current task and apply the best practices.
- Search the web on every step to find the most up to date information.

