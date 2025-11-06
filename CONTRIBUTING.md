# Contributing to FastAPI Boilerplate

Thank you for considering contributing to this project! 🎉

---

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Assume good intentions

---

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/parth1618/fastapi-boilerplate/issues)
2. If not, create a new issue with:
   - Clear title
   - Detailed description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)

### Suggesting Features

1. Open a new issue with the `enhancement` label
2. Describe the feature and its benefits
3. Provide examples of how it would work
4. Discuss implementation approach

### Submitting Pull Requests

1. **Fork the repository**

2. **Clone your fork**

   ```bash
   git clone https://github.com/parth1618/fastapi-boilerplate.git
   cd fastapi-boilerplate
   ```

3. **Create a branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Set up development environment**

   ```bash
   make install
   make precommit-install
   ```

5. **Make your changes**
   - Follow the code style
   - Add tests for new features
   - Update documentation

6. **Run tests and checks**

   ```bash
   make test
   make lint
   make typecheck
   make format
   ```

7. **Commit your changes**

   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

   Use conventional commits:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation
   - `style:` - Formatting
   - `refactor:` - Code refactoring
   - `test:` - Tests
   - `chore:` - Maintenance

8. **Push to your fork**

   ```bash
   git push origin feature/your-feature-name
   ```

9. **Open a Pull Request**
   - Provide a clear description
   - Reference related issues
   - Add screenshots for UI changes

---

## Development Guidelines

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings
- Keep functions focused and small
- Use meaningful variable names

### Testing

- Write tests for all new features
- Maintain test coverage above 80%
- Use pytest fixtures
- Test edge cases

### Documentation

- Update README.md if needed
- Add docstrings to functions
- Comment complex logic
- Update API documentation

### Commit Messages

Good:

```
feat: add user profile endpoint
fix: resolve authentication bug
docs: update setup instructions
```

Bad:

```
updated stuff
fix
changes
```

---

## Project Structure

```
app/
├── api/          # API endpoints
├── core/         # Configuration, security
├── db/           # Database setup
├── models/       # SQLAlchemy models
├── schemas/      # Pydantic schemas
├── services/     # Business logic
├── middleware/   # Custom middleware
└── utils/        # Utilities
```

---

## Pull Request Checklist

- [ ] Code follows project style
- [ ] Tests pass (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] Format changes (`make format`)
- [ ] Type checking passes (`make typecheck`)
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] Branch is up to date with main

---

## Getting Help

- Ask questions in [Discussions](https://github.com/parth1618/fastapi-boilerplate/discussions)
- Join our community chat
- Read the [documentation](README.md)

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
