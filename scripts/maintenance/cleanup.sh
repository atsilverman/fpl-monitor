#!/bin/bash
# FPL Mobile Monitor - Cleanup Script
# Removes temporary files and organizes project structure

set -e

echo "🧹 Cleaning up FPL Mobile Monitor project..."

# Create organized directory structure
mkdir -p temp/debug
mkdir -p temp/logs
mkdir -p temp/data
mkdir -p temp/backups
mkdir -p scratch/experiments
mkdir -p scratch/notes

# Move temporary files to organized locations
echo "📁 Organizing temporary files..."

# Move debug files
if ls debug_* 1> /dev/null 2>&1; then
    echo "  Moving debug files..."
    mv debug_* temp/debug/ 2>/dev/null || true
fi

# Move test files
if ls test_* 1> /dev/null 2>&1; then
    echo "  Moving test files..."
    mv test_* temp/debug/ 2>/dev/null || true
fi

# Move log files
if ls *.log 1> /dev/null 2>&1; then
    echo "  Moving log files..."
    mv *.log temp/logs/ 2>/dev/null || true
fi

# Move CSV data files (except archive)
if ls *.csv 1> /dev/null 2>&1; then
    echo "  Moving CSV files..."
    mv *.csv temp/data/ 2>/dev/null || true
fi

# Move backup files
if ls *.bak 1> /dev/null 2>&1; then
    echo "  Moving backup files..."
    mv *.bak temp/backups/ 2>/dev/null || true
fi

# Move temporary Python files
if ls *.pyc 1> /dev/null 2>&1; then
    echo "  Removing Python cache files..."
    rm -f *.pyc
fi

if ls __pycache__ 1> /dev/null 2>&1; then
    echo "  Removing Python cache directories..."
    rm -rf __pycache__
fi

# Move scratch files
if ls scratch_* 1> /dev/null 2>&1; then
    echo "  Moving scratch files..."
    mv scratch_* scratch/ 2>/dev/null || true
fi

# Clean up empty directories
find . -type d -empty -not -path "./.git*" -not -path "./temp*" -not -path "./scratch*" -delete 2>/dev/null || true

# Show cleanup summary
echo "✅ Cleanup complete!"
echo ""
echo "📊 Project structure:"
echo "  📁 temp/          - Temporary files organized by type"
echo "  📁 scratch/       - Development experiments and notes"
echo "  📁 archive/       - Historical data (kept)"
echo "  📁 other/         - Static assets (kept)"
echo ""
echo "🗑️  Removed:"
echo "  - Python cache files"
echo "  - Temporary debug files"
echo "  - Empty directories"
echo ""
echo "💡 To clean up again, run: ./cleanup.sh"
