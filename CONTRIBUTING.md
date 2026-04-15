# Contributing to bilibili-hot100

Thank you for your interest in contributing!

## How to Contribute

### Reporting Bugs

- Before creating a bug report, search existing issues to avoid duplicates.
- When filing a bug report, include:
  - A clear, descriptive title
  - Steps to reproduce the issue
  - Expected vs actual behavior
  - Python / Node.js version and operating system
  - Any relevant error logs

### Suggesting Features

- Open a new issue with the label `enhancement`.
- Describe the feature and its potential value.
- Explain any drawbacks or compatibility concerns.

### Pull Requests

1. **Fork** the repository.
2. **Create** a feature branch: `git checkout -b feature/your-feature-name`.
3. **Make** your changes with clear, descriptive commits.
4. **Test** your changes — verify both frontend and backend still run correctly.
5. **Push** to your fork and open a Pull Request against `main`.
6. Fill in the PR template with a description of what changed and why.

### Code Style

- **Python**: Follow [PEP 8](https://pep8.org/).
- **TypeScript/Vue**: Use the existing project conventions. Run `npm run build` in the frontend to verify no type errors before committing.
- **Commit messages**: Use imperative mood, e.g. "Fix image cache deduplication bug" not "Fixed...".

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/bilibili-hot100.git
cd bilibili-hot100

# Start all services (Windows)
.\start-all.bat

# Start all services (macOS / Linux)
./start-all.sh
```

Visit http://localhost:3000 to verify the frontend is running.

### Commit Message Format

```
<type>: <short summary>

<body> (optional)
```

Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `chore`

Examples:
```
feat: add WebSocket log streaming to frontend

fix: correct image cache glob pattern to match saved filenames

docs: add installation troubleshooting section
```

## License

By contributing, you agree that your contributions will be licensed under the Apache License, Version 2.0.
