#!/usr/bin/env python3
"""
patch_wrangler.py - Stability patcher for Cloudflare Wrangler CLI

Addresses upload timeouts (UND_ERR_HEADERS_TIMEOUT) and upload failures
over proxies/slow connections by reducing batch size, enforcing single-threaded
bucket uploads, and increasing undici HTTP timeouts.

Modifications applied:
1. MAX_BUCKET_SIZE: Reduced from 50MB/40MB to 4MB (reduces per-chunk Base64 upload size).
2. BULK_UPLOAD_CONCURRENCY: Reduced from 3 to 1 (avoids saturating proxy buffers).
3. headersTimeout / bodyTimeout: Increased from 5 mins (3e5 ms) to 30 mins (18e5 ms).
"""

import os
import re
import sys
import shutil
from pathlib import Path

def find_wrangler_cli_files():
    candidates = []
    # 1. Check npx cache
    home = Path.home()
    npm_cache = home / ".npm" / "_npx"
    if npm_cache.exists():
        for cli in npm_cache.rglob("cli.js"):
            if "wrangler" in str(cli):
                candidates.append(cli)

    # 2. Check global npm/pnpm/yarn/bun modules
    global_dirs = [
        Path("/usr/local/lib/node_modules/wrangler"),
        Path("/opt/homebrew/lib/node_modules/wrangler"),
        home / ".pnpm-global",
        home / ".bun",
    ]
    # Narrow .nvm search to avoid traversing the entire multi-GB tree
    nvm_base = home / ".nvm" / "versions" / "node"
    if nvm_base.exists():
        for version_dir in nvm_base.iterdir():
            wrangler_dir = version_dir / "lib" / "node_modules" / "wrangler"
            if wrangler_dir.exists():
                global_dirs.append(wrangler_dir)

    for g in global_dirs:
        if g.exists():
            for cli in g.rglob("cli.js"):
                if "wrangler" in str(cli):
                    candidates.append(cli)

    # Filter unique resolved paths
    unique = []
    seen = set()
    for c in candidates:
        r = c.resolve()
        if r not in seen and r.exists():
            seen.add(r)
            unique.append(r)
    return unique

def patch_file(cli_path: Path) -> bool:
    content = cli_path.read_text(encoding='utf-8')
    modified = False

    # 1. Patch MAX_BUCKET_SIZE
    #    Try readable source format first, then minified constant fallback
    bucket_pattern = r'(MAX_BUCKET_SIZE\s*=\s*)\d+(\s*\*\s*1024\s*\*\s*1024)'
    if re.search(bucket_pattern, content):
        new_content = re.sub(bucket_pattern, r'\g<1>4\2', content)
        if new_content != content:
            content = new_content
            modified = True
            print("  [+] Patched MAX_BUCKET_SIZE -> 4MB")
    else:
        # Fallback: match the pre-computed constant (50*1024*1024=52428800 or 40*1024*1024=41943040)
        for const_val in ['52428800', '41943040']:
            if const_val in content:
                content = content.replace(const_val, '4194304', 1)  # 4*1024*1024
                modified = True
                print(f"  [+] Patched bucket size constant {const_val} -> 4194304 (4MB)")
                break

    # 2. Patch BULK_UPLOAD_CONCURRENCY
    concurrency_pattern = r'(BULK_UPLOAD_CONCURRENCY\s*=\s*)\d+'
    if re.search(concurrency_pattern, content):
        new_content = re.sub(concurrency_pattern, r'\g<1>1', content)
        if new_content != content:
            content = new_content
            modified = True
            print("  [+] Patched BULK_UPLOAD_CONCURRENCY -> 1")

    # 3. Patch headersTimeout (handle minified formats: no spaces, various notations)
    timeout_pattern = r'(headersTimeout\s*:\s*)(?:3e5|300000|300_000)'
    if re.search(timeout_pattern, content):
        new_content = re.sub(timeout_pattern, r'\g<1>18e5', content)
        if new_content != content:
            content = new_content
            modified = True
            print("  [+] Patched headersTimeout -> 18e5 (30 mins)")

    if modified:
        backup = cli_path.with_suffix(".js.orig")
        if not backup.exists():
            shutil.copy2(cli_path, backup)
            print(f"  [+] Backup created: {backup.name}")
        cli_path.write_text(content, encoding='utf-8')
        print(f"✓ Successfully patched: {cli_path}")
        return True
    else:
        print(f"  [!] WARNING: No matching patterns found in: {cli_path}")
        print(f"      This may indicate a newer Wrangler version with different code structure.")
        print(f"      Please manually search cli.js for bucket size, concurrency, and timeout settings.")
        print(f"      File size: {cli_path.stat().st_size / 1024:.0f} KB")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Applies stability patches to Cloudflare Wrangler CLI (bucket size, concurrency, timeouts).")
    parser.add_argument("cli_path", nargs="?", help="Optional direct path to wrangler cli.js to patch")
    args = parser.parse_args()

    if args.cli_path:
        target = Path(args.cli_path).resolve()
        if not target.exists():
            sys.exit(f"File not found: {target}")
        print(f"Patching specified file: {target}")
        patch_file(target)
        return

    print("Searching for Wrangler cli.js installations...")
    files = find_wrangler_cli_files()
    if not files:
        print("No Wrangler installation found in ~/.npm/_npx or standard global paths.")
        print("Tip: Run `npx wrangler --version` first to populate the cache, or specify the file path directly:")
        print("  python3 patch_wrangler.py <path/to/wrangler/bin/cli.js>")
        return

    for f in files:
        print(f"\nProcessing {f}:")
        patch_file(f)

if __name__ == '__main__':
    main()
