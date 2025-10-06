@echo off
REM Day 1 Test Runner - Windows Batch Script

echo ================================================
echo Day 1 Migration Tests - FK Constraints
echo ================================================
echo.

REM Activate virtual environment
echo Activating virtual environment...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found!
    echo Please create venv first: python -m venv venv
    pause
    exit /b 1
)

REM Run the tests
echo.
echo Running automated tests...
echo.
python tests\test_day1_migrations.py

REM Check exit code
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================
    echo SUCCESS: All Day 1 tests passed!
    echo ================================================
    echo.
    echo You can proceed to Day 2 implementation.
    pause
    exit /b 0
) else (
    echo.
    echo ================================================
    echo FAILURE: Some tests failed
    echo ================================================
    echo.
    echo Please review the errors above.
    echo Fix issues before proceeding to Day 2.
    pause
    exit /b 1
)
