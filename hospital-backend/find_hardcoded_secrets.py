"""
Search for hardcoded secrets and credentials in the codebase
"""
import os
import re
from pathlib import Path

# Patterns to search for
PATTERNS = {
    'Database URLs': [
        r'postgresql://[^"\']+',
        r'postgres://[^"\']+',
        r'mongodb://[^"\']+',
    ],
    'Passwords': [
        r'password\s*=\s*["\']([^"\']+)["\']',
        r'PASSWORD\s*=\s*["\']([^"\']+)["\']',
        r'pwd\s*=\s*["\']([^"\']+)["\']',
    ],
    'API Keys': [
        r'api[_-]?key\s*=\s*["\']([^"\']+)["\']',
        r'API[_-]?KEY\s*=\s*["\']([^"\']+)["\']',
        r'apiKey\s*=\s*["\']([^"\']+)["\']',
    ],
    'Secret Keys': [
        r'secret[_-]?key\s*=\s*["\']([^"\']+)["\']',
        r'SECRET[_-]?KEY\s*=\s*["\']([^"\']+)["\']',
        r'secretKey\s*=\s*["\']([^"\']+)["\']',
    ],
    'JWT Secrets': [
        r'jwt[_-]?secret\s*=\s*["\']([^"\']+)["\']',
        r'JWT[_-]?SECRET\s*=\s*["\']([^"\']+)["\']',
    ],
    'Tokens': [
        r'token\s*=\s*["\']([a-zA-Z0-9_\-\.]{20,})["\']',
        r'TOKEN\s*=\s*["\']([a-zA-Z0-9_\-\.]{20,})["\']',
    ],
}

EXCLUDE_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build'}
EXCLUDE_FILES = {'.pyc', '.pyo', '.so', '.dll', '.exe', '.bin'}


def should_check_file(file_path):
    """Determine if file should be checked"""
    # Skip binary files
    if file_path.suffix in EXCLUDE_FILES:
        return False

    # Check if file is in excluded directory
    for part in file_path.parts:
        if part in EXCLUDE_DIRS:
            return False

    # Only check code files
    allowed_extensions = {'.py', '.js', '.ts', '.tsx', '.json', '.yml', '.yaml', '.env', '.conf', '.config'}
    return file_path.suffix in allowed_extensions or file_path.name in {'.env', '.env.example'}


def search_file(file_path, patterns):
    """Search a file for patterns"""
    findings = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    # Get line number
                    line_num = content[:match.start()].count('\n') + 1

                    # Get the matched line
                    lines = content.split('\n')
                    matched_line = lines[line_num - 1] if line_num <= len(lines) else ''

                    findings.append({
                        'category': category,
                        'file': str(file_path),
                        'line': line_num,
                        'matched_line': matched_line.strip(),
                        'pattern': pattern
                    })

    except Exception as e:
        pass  # Skip files that can't be read

    return findings


def search_directory(root_dir):
    """Search directory recursively"""
    root_path = Path(root_dir)
    all_findings = []

    for file_path in root_path.rglob('*'):
        if file_path.is_file() and should_check_file(file_path):
            findings = search_file(file_path, PATTERNS)
            all_findings.extend(findings)

    return all_findings


def main():
    print("=" * 80)
    print("HARDCODED SECRETS SCAN")
    print("=" * 80)

    # Search both backend and frontend
    backend_dir = Path(__file__).parent
    frontend_dir = backend_dir.parent / 'hospital-display-app'

    print("\nSearching backend...")
    backend_findings = search_directory(backend_dir)

    print("Searching frontend...")
    frontend_findings = search_directory(frontend_dir)

    all_findings = backend_findings + frontend_findings

    # Group by category
    by_category = {}
    for finding in all_findings:
        category = finding['category']
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(finding)

    # Print results
    print("\n" + "=" * 80)
    print("SCAN RESULTS")
    print("=" * 80)

    if not all_findings:
        print("\n[SUCCESS] No hardcoded secrets found!")
    else:
        print(f"\n[WARNING] Found {len(all_findings)} potential hardcoded secrets\n")

        for category, findings in sorted(by_category.items()):
            print(f"\n{category} ({len(findings)} found):")
            print("-" * 80)

            for finding in findings:
                rel_path = Path(finding['file']).relative_to(Path(__file__).parent.parent)
                print(f"\nFile: {rel_path}")
                print(f"Line {finding['line']}: {finding['matched_line'][:100]}")

    print("\n" + "=" * 80)
    print(f"Total potential secrets found: {len(all_findings)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
