
@echo off
echo Installing test dependencies...
pip install pytest pytest-mock pytest-cov pandas numpy pillow

echo.
echo Running Tests...
pytest tests/ --cov=dataset-platform/app --cov=training --cov-report=term-missing
pause
