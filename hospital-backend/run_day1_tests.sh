#!/bin/bash
# Day 1 Test Runner - Bash Script for Mac/Linux

echo "================================================"
echo "Day 1 Migration Tests - FK Constraints"
echo "================================================"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
else
    echo "ERROR: Virtual environment not found!"
    echo "Please create venv first: python -m venv venv"
    exit 1
fi

# Run the tests
echo ""
echo "Running automated tests..."
echo ""
python tests/test_day1_migrations.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    echo "SUCCESS: All Day 1 tests passed!"
    echo "================================================"
    echo ""
    echo "You can proceed to Day 2 implementation."
    exit 0
else
    echo ""
    echo "================================================"
    echo "FAILURE: Some tests failed"
    echo "================================================"
    echo ""
    echo "Please review the errors above."
    echo "Fix issues before proceeding to Day 2."
    exit 1
fi
