# Contributing Guide

Thank you for your interest in contributing to this project!

## Development Setup

1. Fork the repository
2. Clone your fork: `git clone <your-fork-url>`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Run tests: `pytest tests/ -v`
6. Commit: `git commit -m "Add: your feature description"`
7. Push: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Code Standards

### Python Style
- Follow PEP 8
- Use type hints where possible
- Add docstrings to all functions/classes
- Maximum line length: 100 characters

### Testing
- Write tests for new features
- Maintain > 80% code coverage
- Run `pytest tests/ --cov=src` before committing

### Git Commits
Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `perf:` Performance improvements

## Project Structure

```
src/
├── ingestion/      # Data generation and ingestion
├── processing/     # Stream processing and transformations
├── storage/        # Database models and operations
├── analytics/      # Analytics engines (RFM, cohort, recommendations)
├── visualization/  # Dashboard and UI
└── utils/          # Shared utilities
```

## Adding New Features

### 1. Analytics Module
```python
# src/analytics/your_module.py
"""
Description of the module.
"""

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

class YourAnalyzer:
    """Your analyzer class."""
    
    def __init__(self):
        """Initialize analyzer."""
        logger.info("Analyzer initialized")
    
    def analyze(self, data):
        """Main analysis method."""
        pass
```

### 2. Add Tests
```python
# tests/unit/test_your_module.py
import pytest
from src.analytics.your_module import YourAnalyzer

class TestYourAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return YourAnalyzer()
    
    def test_analyze(self, analyzer):
        result = analyzer.analyze(sample_data)
        assert result is not None
```

### 3. Update Documentation
- Add to relevant docs in `docs/`
- Update README if needed
- Add API documentation

## Running Tests

```bash
# All tests
pytest tests/

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific test file
pytest tests/unit/test_your_module.py -v

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v
```

## Code Review Process

1. All PRs require review
2. Tests must pass
3. Code coverage should not decrease
4. Documentation must be updated
5. Follow the style guide

## Questions?

Open an issue for:
- Bug reports
- Feature requests
- Questions about the codebase
- Suggestions for improvements

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

