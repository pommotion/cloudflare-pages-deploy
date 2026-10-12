#!/usr/bin/env python3
"""
subset_fonts.py - Automatic Font Subsetting Tool for Web Projects

Scans source code files (.js, .html, .json, .txt, .lrc, etc.) to extract all
unique characters used in the project, plus standard ASCII printable chars,
and subsets large CJK fonts using fonttools.

Usage:
  python3 subset_fonts.py --project-dir ./my-web-project --font NotoSerifSC.ttf
  python3 subset_fonts.py --project-dir ./my-web-project --all-fonts
"""

import os
import sys
import argparse
from pathlib import Path

try:
    from fontTools import subset
except ImportError:
    sys.exit("Error: fonttools is required. Install it with: pip install fonttools [brotli]")

# Common text and code extensions to scan
TEXT_EXTS = {'.html', '.js', '.mjs', '.ts', '.jsx', '.tsx', '.json', '.txt', '.lrc', '.css', '.md'}

# Basic ASCII printable range (32-126) + standard typographic punctuation
BASIC_CHARS = set(" 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                  "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
                  "“”‘’—…·《》【】「」『』、。，；：！？（）")

def extract_project_chars(root_dir: Path) -> set:
    chars = set(BASIC_CHARS)
    for p in root_dir.rglob('*'):
        if p.is_file() and p.suffix.lower() in TEXT_EXTS:
            try:
                content = p.read_text(encoding='utf-8', errors='ignore')
                chars.update(content)
            except Exception as e:
                print(f"Warning: Failed reading {p}: {e}")
    # Remove control characters except newline and tab
    return {c for c in chars if c >= ' ' or c in '\n\t'}

def subset_font(font_path: Path, chars: set, output_path: Path = None):
    if not font_path.exists():
        print(f"Error: Font file not found: {font_path}")
        return

    if output_path is None:
        backup_path = font_path.with_suffix(font_path.suffix + '.orig')
        if backup_path.exists():
            # Restore original font before re-subsetting to prevent progressive degradation
            import shutil
            shutil.copy2(backup_path, font_path)
            print(f"Restored original font from {backup_path.name} before re-subsetting")
        else:
            import shutil
            shutil.copy2(font_path, backup_path)
            print(f"Backed up original font to {backup_path.name}")
        output_path = font_path

    # Read original size AFTER potential restore from .orig
    orig_size = font_path.stat().st_size

    # Prepare subset options
    # Retain layout features and variable font tables to preserve rendering fidelity
    options = subset.Options()
    options.layout_features = ["*"]
    options.drop_tables = []
    options.passthrough_tables = True
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.name_languages = ["*"]

    font = subset.load_font(str(font_path), options)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text="".join(chars))
    subsetter.subset(font)
    subset.save_font(font, str(output_path), options)

    new_size = output_path.stat().st_size
    ratio = (1 - (new_size / orig_size)) * 100
    print(f"✓ Subsetting {font_path.name}: {orig_size / 1024 / 1024:.2f} MB -> {new_size / 1024 / 1024:.2f} MB (-{ratio:.1f}%)")

def main():
    parser = argparse.ArgumentParser(description="Subsets CJK fonts based on project text content.")
    parser.add_argument("--project-dir", "-d", default=".", help="Project directory to scan for text")
    parser.add_argument("--font", "-f", help="Specific font file to subset")
    parser.add_argument("--all-fonts", action="store_true", help="Subset all .ttf/.otf files found in project")
    parser.add_argument("--output", "-o", help="Output path (default: in-place replacement with .orig backup)")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    print(f"Scanning {project_dir} for characters...")
    chars = extract_project_chars(project_dir)
    print(f"Extracted {len(chars)} unique glyphs.")

    if args.font:
        target = Path(args.font)
        if not target.is_absolute():
            target = project_dir / target
        out = Path(args.output).resolve() if args.output else None
        subset_font(target, chars, out)
    elif args.all_fonts:
        fonts = [p for p in project_dir.rglob('*') if p.suffix.lower() in {'.ttf', '.otf'} and not p.name.endswith('.orig')]
        if not fonts:
            print("No .ttf or .otf fonts found in project directory.")
            return
        for f in fonts:
            subset_font(f, chars)
    else:
        print("Please specify --font <path> or --all-fonts")

if __name__ == '__main__':
    main()
