# Agent Guidance

## What This Repo Is

Java/Spring interview preparation repository for mid-to-senior backend positions. Two parts:

1. **`interview-questions/`** — Markdown Q&A bank (33 questions, all in Chinese)
2. **`project-lerarn/`** — Maven Java practice project (name has typo, matches pom.xml)

## Directory Structure

```
interview-questions/          # Interview questions by topic
├── 01-java-core/             # JVM, concurrency, collections
├── 02-spring/                # IoC, AOP, Spring Boot, transactions
├── 03-database/              # MySQL, Redis, MyBatis
├── 04-microservice/          # Service governance, fault tolerance
├── 05-distributed/           # Distributed transactions, MQ, ID generation
└── 06-scenario-design/       # Seckill system, order timeout

project-lerarn/               # Maven Java project (practice code)
├── pom.xml                   # groupId=com.example, junit 3.8.1 + lombok 1.18.42
├── src/main/java/            # Application code
└── src/test/java/            # Test code

openspec/                     # OpenSpec workflow config
.claude/                      # Claude Code skills (openspec-*)
```

## Build Commands

```bash
# Build the Maven project
cd project-lerarn && mvn clean compile

# Run tests
cd project-lerarn && mvn test

# Package (skip tests)
cd project-lerarn && mvn package -DskipTests
```

No CI/CD workflows exist. No Makefile or task runner.

## Interview Questions

- All content is in Chinese
- 6 categories, 33 total questions
- Each `.md` file is self-contained with Q&A format
- See `interview-questions/README.md` for knowledge tree overview

## OpenSpec Workflow

This repo uses OpenSpec for change management. Skills available:
- `/openspec-propose` — Create a new change proposal
- `/openspec-apply-change` — Implement tasks from a proposal
- `/openspec-explore` — Explore ideas before committing
- `/openspec-archive-change` — Archive completed changes

Config at `openspec/config.yaml` (currently minimal, no custom context or rules).

## Important Notes

- **No Spring dependencies yet**: pom.xml only has junit + lombok despite interview content covering Spring
- **Project name typo**: Directory is `project-lerarn` (not `project-learn`) — this is intentional/consistent
- **Windows environment**: Shell is PowerShell
- **No existing AGENTS.md, CLAUDE.md, or opencode.json** at repo root
