#!/usr/bin/env python3
"""
FPL Mobile Monitor - Intelligent File Organizer
==============================================

Automatically organizes files as they're created and provides
intelligent suggestions for file placement.
"""

import os
import shutil
import re
from pathlib import Path
from typing import Optional, List
import logging

class FileOrganizer:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.setup_directories()
        self.setup_logging()
        
        # File patterns and their destinations
        self.file_patterns = {
            # Debug and test files
            r'debug_.*': 'temp/debug/',
            r'test_.*': 'temp/debug/',
            r'.*_debug\.py': 'temp/debug/',
            r'.*_test\.py': 'temp/debug/',
            
            # Log files
            r'.*\.log$': 'temp/logs/',
            r'.*\.log\..*': 'temp/logs/',
            
            # Data files
            r'.*\.csv$': 'temp/data/',
            r'.*\.json$': 'temp/data/',
            r'.*\.xlsx$': 'temp/data/',
            
            # Backup files
            r'.*\.bak$': 'temp/backups/',
            r'.*_backup.*': 'temp/backups/',
            r'.*\.backup$': 'temp/backups/',
            
            # Temporary files
            r'.*\.tmp$': 'temp/',
            r'.*\.temp$': 'temp/',
            r'temp_.*': 'temp/',
            
            # Scratch files
            r'scratch_.*': 'scratch/experiments/',
            r'experiment_.*': 'scratch/experiments/',
            r'playground_.*': 'scratch/experiments/',
            
            # Notes
            r'notes_.*': 'scratch/notes/',
            r'todo_.*': 'scratch/notes/',
            r'ideas_.*': 'scratch/notes/',
        }
    
    def setup_directories(self):
        """Create organized directory structure"""
        directories = [
            'temp/debug',
            'temp/logs', 
            'temp/data',
            'temp/backups',
            'scratch/experiments',
            'scratch/notes'
        ]
        
        for directory in directories:
            (self.project_root / directory).mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self):
        """Setup logging for file operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('temp/logs/file_organizer.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def suggest_location(self, filename: str) -> Optional[str]:
        """Suggest where a file should be placed based on its name"""
        for pattern, destination in self.file_patterns.items():
            if re.match(pattern, filename, re.IGNORECASE):
                return destination
        return None
    
    def organize_file(self, filepath: str, dry_run: bool = False) -> bool:
        """Organize a single file to its appropriate location"""
        filepath = Path(filepath)
        
        if not filepath.exists():
            self.logger.warning(f"File does not exist: {filepath}")
            return False
        
        # Skip if already in organized location
        if any(str(filepath).startswith(str(self.project_root / dir_name)) 
               for dir_name in ['temp/', 'scratch/', 'archive/', 'other/']):
            return True
        
        # Get suggested location
        suggested_location = self.suggest_location(filepath.name)
        
        if not suggested_location:
            self.logger.info(f"No specific location suggested for: {filepath.name}")
            return False
        
        # Create destination path
        dest_path = self.project_root / suggested_location / filepath.name
        
        # Handle name conflicts
        counter = 1
        original_dest = dest_path
        while dest_path.exists():
            stem = original_dest.stem
            suffix = original_dest.suffix
            dest_path = original_dest.parent / f"{stem}_{counter}{suffix}"
            counter += 1
        
        if dry_run:
            self.logger.info(f"Would move: {filepath} -> {dest_path}")
            return True
        
        try:
            # Move the file
            shutil.move(str(filepath), str(dest_path))
            self.logger.info(f"Moved: {filepath} -> {dest_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to move {filepath}: {e}")
            return False
    
    def organize_project(self, dry_run: bool = False) -> dict:
        """Organize all files in the project"""
        results = {
            'moved': [],
            'skipped': [],
            'errors': []
        }
        
        # Get all files in project root (excluding organized directories)
        exclude_dirs = {'temp', 'scratch', 'archive', 'other', '.git', '__pycache__'}
        
        for file_path in self.project_root.iterdir():
            if file_path.is_file() and file_path.parent.name not in exclude_dirs:
                suggested_location = self.suggest_location(file_path.name)
                
                if suggested_location:
                    if self.organize_file(str(file_path), dry_run):
                        results['moved'].append(str(file_path))
                    else:
                        results['errors'].append(str(file_path))
                else:
                    results['skipped'].append(str(file_path))
        
        return results
    
    def create_file_in_location(self, filename: str, content: str = "", 
                               category: str = "temp") -> Path:
        """Create a file in the appropriate location based on category"""
        location_map = {
            'debug': 'temp/debug/',
            'log': 'temp/logs/',
            'data': 'temp/data/',
            'backup': 'temp/backups/',
            'experiment': 'scratch/experiments/',
            'notes': 'scratch/notes/',
            'temp': 'temp/',
            'scratch': 'scratch/'
        }
        
        location = location_map.get(category, 'temp/')
        file_path = self.project_root / location / filename
        
        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.logger.info(f"Created file in organized location: {file_path}")
        return file_path

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Organize FPL Mobile Monitor project files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be moved without actually moving')
    parser.add_argument('--file', help='Organize a specific file')
    parser.add_argument('--create', help='Create a file in appropriate location')
    parser.add_argument('--category', default='temp', help='Category for file creation')
    
    args = parser.parse_args()
    
    organizer = FileOrganizer()
    
    if args.file:
        # Organize specific file
        organizer.organize_file(args.file, args.dry_run)
    elif args.create:
        # Create file in appropriate location
        organizer.create_file_in_location(args.create, category=args.category)
    else:
        # Organize entire project
        results = organizer.organize_project(args.dry_run)
        
        print(f"\n📊 Organization Results:")
        print(f"  ✅ Moved: {len(results['moved'])} files")
        print(f"  ⏭️  Skipped: {len(results['skipped'])} files")
        print(f"  ❌ Errors: {len(results['errors'])} files")
        
        if results['moved']:
            print(f"\n📁 Files moved:")
            for file in results['moved']:
                print(f"  - {file}")
        
        if results['errors']:
            print(f"\n❌ Errors:")
            for file in results['errors']:
                print(f"  - {file}")

if __name__ == "__main__":
    main()
