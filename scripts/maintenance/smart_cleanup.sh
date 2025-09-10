#!/bin/bash
# FPL Mobile Monitor - Smart Cleanup Script
# Intelligently organizes files and provides suggestions

set -e

echo "🧠 Smart cleanup for FPL Mobile Monitor project..."

# Run the intelligent file organizer
echo "📁 Running intelligent file organizer..."
python3 file_organizer.py

# Additional cleanup for common patterns
echo "🧹 Additional cleanup..."

# Move any remaining debug files
if ls debug_* 1> /dev/null 2>&1; then
    echo "  Moving remaining debug files..."
    mv debug_* temp/debug/ 2>/dev/null || true
fi

# Move any remaining test files
if ls test_* 1> /dev/null 2>&1; then
    echo "  Moving remaining test files..."
    mv test_* temp/debug/ 2>/dev/null || true
fi

# Move any remaining log files
if ls *.log 1> /dev/null 2>&1; then
    echo "  Moving remaining log files..."
    mv *.log temp/logs/ 2>/dev/null || true
fi

# Move any remaining CSV files (except archive)
if ls *.csv 1> /dev/null 2>&1; then
    echo "  Moving remaining CSV files..."
    mv *.csv temp/data/ 2>/dev/null || true
fi

# Clean up Python cache
echo "  Cleaning Python cache..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Clean up empty directories
echo "  Removing empty directories..."
find . -type d -empty -not -path "./.git*" -not -path "./temp*" -not -path "./scratch*" -delete 2>/dev/null || true

# Show project status
echo ""
echo "✅ Smart cleanup complete!"
echo ""
echo "📊 Current project structure:"
echo "  📁 temp/          - $(find temp -type f | wc -l | tr -d ' ') files"
echo "  📁 scratch/       - $(find scratch -type f | wc -l | tr -d ' ') files"
echo "  📁 archive/       - $(find archive -type f | wc -l | tr -d ' ') files"
echo "  📁 other/         - $(find other -type f | wc -l | tr -d ' ') files"
echo ""
echo "💡 Tips:"
echo "  - Use 'python3 file_organizer.py --dry-run' to see what would be moved"
echo "  - Use 'python3 file_organizer.py --create filename.txt --category debug' to create files in organized locations"
echo "  - Run './smart_cleanup.sh' anytime to organize the project"
