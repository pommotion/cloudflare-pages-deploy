#!/usr/bin/env python3
"""
pack_deploy_zip.py - Package a web project for Cloudflare Pages Direct Upload

Ensures the folder structure conforms to Cloudflare Pages requirements:
1. Validates that index.html is directly at the root of the archive.
2. Checks that no single file exceeds Cloudflare's 25 MiB per-file limit.
3. Automatically generates/injects a high-performance `_headers` file if absent.
4. Strips OS metadata (.DS_Store, __MACOSX, .git, .orig, .pyc, etc.).
5. Creates a flat, root-aligned .zip ready for drag-and-drop into Cloudflare Dashboard.

Usage:
  python3 pack_deploy_zip.py --source ./my-dist --output ./deploy.zip
"""

import os
import sys
import zipfile
import argparse
from pathlib import Path

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MiB Cloudflare limit

DEFAULT_HEADERS = """# Cloudflare Pages Headers Configuration
# Font caching (1 year immutable)
/*.ttf
  Cache-Control: public, max-age=31536000, immutable
/*.otf
  Cache-Control: public, max-age=31536000, immutable
/*.woff2
  Cache-Control: public, max-age=31536000, immutable

# Media streaming caching
/*.mp4
  Cache-Control: public, max-age=604800
/*.mp3
  Cache-Control: public, max-age=604800
/*.m4a
  Cache-Control: public, max-age=604800

# Images
/*.jpg
  Cache-Control: public, max-age=604800
/*.png
  Cache-Control: public, max-age=604800
/*.webp
  Cache-Control: public, max-age=604800

# HTML never cache stale
/*.html
  Cache-Control: public, max-age=0, must-revalidate
"""

IGNORED_PATTERNS = {
    '.ds_store', '__macosx', '.git', '.gitignore',
    '.pyc', '__pycache__', '.env', '.venv', 'node_modules'
}

def should_ignore(path: Path) -> bool:
    for part in path.parts:
        part_lower = part.lower()
        if part_lower in IGNORED_PATTERNS or part_lower.endswith('.orig'):
            return True
    return False

def main():
    parser = argparse.ArgumentParser(description="Packages a directory into a Cloudflare Pages deployable zip.")
    parser.add_argument("--source", "-s", required=True, help="Directory containing website assets")
    parser.add_argument("--output", "-o", required=True, help="Path to output .zip file")
    parser.add_argument("--skip-size-check", action="store_true", help="Don't error on files > 25MB")
    parser.add_argument("--strict", action="store_true", help="Abort if any file exceeds 25 MiB limit")
    args = parser.parse_args()

    source_dir = Path(args.source).resolve()
    if not source_dir.is_dir():
        sys.exit(f"Error: Source directory not found: {source_dir}")

    # 1. Root verification
    index_html = source_dir / "index.html"
    if not index_html.exists():
        sys.exit(f"Error: index.html not found in {source_dir}. Cloudflare Pages requires index.html at root.")

    # 2. Check if project already has _headers
    has_headers = (source_dir / "_headers").exists()

    output_zip = Path(args.output).resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    print(f"Packaging {source_dir} -> {output_zip}...")

    file_count = 0
    total_uncompressed = 0
    oversized = []

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in source_dir.rglob("*"):
            if p.is_file():
                if should_ignore(p):
                    continue
                size = p.stat().st_size
                if size > MAX_FILE_SIZE_BYTES:
                    oversized.append((p.relative_to(source_dir), size))

                arcname = p.relative_to(source_dir).as_posix()
                zf.write(p, arcname=arcname)
                file_count += 1
                total_uncompressed += size

        # Inject default _headers into zip only (not into source dir) if project lacks one
        if not has_headers:
            zf.writestr("_headers", DEFAULT_HEADERS)
            file_count += 1
            print("Note: Injected default '_headers' into zip (source directory not modified).")

    if oversized:
        print("\n[!] WARNING: The following files exceed Cloudflare Pages 25 MiB direct upload limit:")
        for rel_path, s in oversized:
            print(f"    - {rel_path}: {s / 1024 / 1024:.2f} MiB")
        if args.strict:
            output_zip.unlink(missing_ok=True)
            sys.exit("Aborted: --strict mode enabled and oversized files detected.")
        elif not args.skip_size_check:
            print("These files may cause upload failure or HTTP 400 Bad Request.")
            print("Use --strict to abort, or --skip-size-check to suppress this warning.\n")

    zip_size = output_zip.stat().st_size
    print(f"✓ Successfully created {output_zip.name}:")
    print(f"  - Files packed: {file_count}")
    print(f"  - Uncompressed size: {total_uncompressed / 1024 / 1024:.2f} MB")
    print(f"  - Archive size: {zip_size / 1024 / 1024:.2f} MB")
    print(f"  - Ready for Cloudflare Dashboard drag-and-drop upload!")

if __name__ == '__main__':
    main()

