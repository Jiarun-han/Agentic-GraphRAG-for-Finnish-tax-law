"""Extract corpus with shortened filenames to avoid Windows MAX_PATH issues."""
import tarfile
import os
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "raw" / "finland_kb.tar.gz"
OUTPUT = ROOT / "data" / "raw"


def shorten_name(name: str) -> str:
    """Keep directory structure but shorten overly long filenames."""
    parts = name.split("/")
    # Shorten any path component longer than 80 chars
    shortened = []
    for part in parts:
        if len(part) > 80:
            # Keep first 60 chars + hash suffix + extension
            ext = ""
            if "." in part:
                ext = "." + part.rsplit(".", 1)[1]
                base = part.rsplit(".", 1)[0]
            else:
                base = part
            h = hashlib.md5(part.encode()).hexdigest()[:8]
            shortened.append(base[:60] + "_" + h + ext)
        else:
            shortened.append(part)
    return "/".join(shortened)


def main():
    print(f"Archive: {ARCHIVE}")
    print(f"Output:  {OUTPUT}")
    
    os.makedirs(OUTPUT, exist_ok=True)
    
    with tarfile.open(ARCHIVE) as tar:
        members = tar.getmembers()
        total = len(members)
        print(f"Total entries: {total}")
        
        extracted = 0
        skipped = 0
        
        for i, member in enumerate(members):
            if i % 5000 == 0:
                print(f"  Progress: {i}/{total} ({100*i//total}%)")
            
            # Shorten the name
            new_name = shorten_name(member.name)
            target = OUTPUT / new_name
            
            if member.isdir():
                os.makedirs(target, exist_ok=True)
            elif member.isfile():
                os.makedirs(target.parent, exist_ok=True)
                try:
                    f = tar.extractfile(member)
                    if f:
                        with open(target, "wb") as out:
                            out.write(f.read())
                        extracted += 1
                except (OSError, KeyError) as e:
                    skipped += 1
                    if skipped <= 5:
                        print(f"  SKIP: {new_name} ({e})")
        
        print(f"\nDone! Extracted: {extracted}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
