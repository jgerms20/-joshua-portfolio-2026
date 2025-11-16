#!/bin/bash
# Automated Portfolio Sourcer Runner
# Run this script manually or via cron for automated portfolio updates

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Portfolio Sourcer Agent"
echo "=========================================="
echo "Started at: $(date)"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3."
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import requests" &> /dev/null; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
fi

# Run the sourcer
echo "Running portfolio sourcer..."
python3 -m portfolio_sourcer.portfolio_sourcer

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Scan completed successfully!"
    echo "Check portfolio_updates/ for reports"
    echo "Finished at: $(date)"
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "Scan completed with errors (exit code: $EXIT_CODE)"
    echo "Check portfolio_sourcer.log for details"
    echo "=========================================="
fi

exit $EXIT_CODE

