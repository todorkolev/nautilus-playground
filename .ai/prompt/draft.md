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

Apply Domain driven design (DDD) approach to software development that centers the development on programming a domain model that has a rich understanding of the processes and rules of a domain. It emphasizes:
- Focusing on the core domain and domain logic
- Basing complex designs on models of the domain
- Collaborating with domain experts to improve the application model and resolve domain-related issues
- Iteratively refining the domain model

Apply Ports and adapters architecture:
The hexagonal architecture, or ports and adapters architecture, is an architectural pattern used in software design. It aims at creating loosely coupled application components that can be easily connected to their software environment by means of ports and adapters. This makes components exchangeable at any level and facilitates test automation.

Apply Crash-only design:
Implement Crash-only design principles in the software architecture aiming to create more robust and reliable systems by designing components to crash safely and recover quickly.

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
- Don't go for shortcuts and simple solutions - complete the task that the user requested.
- Don't apply patches - fix the underlying issues and root causes.
- Never read or write in .env files. They should be accessed strictly by the user.
- When you need a temporary script to test a hypothesis, write it as a command in the terminal - don't create a file for it if possible.
- When debugging and looking for a particular log messages, use grep to filter the terminal output.

Tool use:
- Use the context7 tool on each step to research the latest documentation for the current task and apply the best practices.
- Search the web on every step to find the most up to date information.

