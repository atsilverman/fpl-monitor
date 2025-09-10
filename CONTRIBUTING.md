# 🤝 Contributing to FPL Monitor

Thank you for your interest in contributing to FPL Monitor! This document provides guidelines for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Process](#contributing-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)

## 📜 Code of Conduct

This project follows a code of conduct that we expect all contributors to follow. Please be respectful and constructive in all interactions.

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Xcode 15+ (for iOS development)
- Git
- Docker (optional)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/yourusername/fpl-monitor.git
   cd fpl-monitor
   ```

3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/originalowner/fpl-monitor.git
   ```

## 🛠️ Development Setup

### Backend Setup

1. Create a virtual environment:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. Run the development server:
   ```bash
   python -m backend.main
   ```

### iOS Setup

1. Open the project in Xcode:
   ```bash
   open ios/FPLMonitor/FPLMonitor.xcodeproj
   ```

2. Update the API URL in `APIManager.swift`
3. Build and run on simulator or device

### Testing

Run the test suite:
```bash
# Backend tests
python -m pytest tests/backend/

# All tests
python -m pytest tests/
```

## 🔄 Contributing Process

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number
```

### 2. Make Your Changes

- Write clean, readable code
- Follow the coding standards
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run tests
python -m pytest tests/

# Check code style
black --check .
flake8 .

# Type checking
mypy backend/
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

Use conventional commit messages:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting changes
- `refactor:` for code refactoring
- `test:` for adding tests
- `chore:` for maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## 📏 Coding Standards

### Python (Backend)

- Follow PEP 8 style guide
- Use type hints
- Write docstrings for functions and classes
- Use meaningful variable and function names
- Keep functions small and focused

Example:
```python
def get_player_by_id(player_id: int) -> Optional[Player]:
    """
    Retrieve a player by their ID.
    
    Args:
        player_id: The unique identifier for the player
        
    Returns:
        Player object if found, None otherwise
    """
    # Implementation here
```

### Swift (iOS)

- Follow Swift style guide
- Use meaningful names
- Add documentation comments
- Use proper error handling
- Follow SwiftUI best practices

Example:
```swift
/// Retrieves a player by their ID
/// - Parameter playerId: The unique identifier for the player
/// - Returns: Player object if found, nil otherwise
func getPlayer(by playerId: Int) async -> Player? {
    // Implementation here
}
```

## 🧪 Testing

### Backend Testing

- Write unit tests for all new functions
- Write integration tests for API endpoints
- Aim for >80% code coverage
- Use pytest fixtures for test data

### iOS Testing

- Write unit tests for business logic
- Write UI tests for critical user flows
- Test on multiple device sizes
- Test both light and dark modes

## 📚 Documentation

### Code Documentation

- Add docstrings to all functions and classes
- Include type hints
- Document complex algorithms
- Keep comments up to date

### API Documentation

- Update API.md for endpoint changes
- Include request/response examples
- Document error codes and messages

### User Documentation

- Update README.md for new features
- Add screenshots for UI changes
- Update deployment guide for infrastructure changes

## 🔍 Pull Request Process

### Before Submitting

1. **Test your changes thoroughly**
2. **Update documentation**
3. **Ensure all tests pass**
4. **Check code style and formatting**
5. **Rebase on latest main branch**

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
```

### Review Process

1. **Automated checks** must pass
2. **Code review** by maintainers
3. **Testing** on staging environment
4. **Approval** from at least one maintainer

## 🐛 Reporting Issues

### Bug Reports

Use the bug report template and include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details
- Screenshots/logs if applicable

### Feature Requests

Use the feature request template and include:
- Clear description of the feature
- Use case and motivation
- Proposed implementation (if any)
- Additional context

## 🏷️ Release Process

1. **Version bump** in appropriate files
2. **Update CHANGELOG.md**
3. **Create release branch**
4. **Tag release**
5. **Deploy to production**
6. **Update documentation**

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Discord**: For real-time chat (if available)

## 🙏 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to FPL Monitor! 🎉
