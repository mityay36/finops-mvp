"""
Decrypt a credential value previously stored in `provider_credentials.encrypted_value`.

Usage:
    export FERNET_KEY="..."
    python scripts/decrypt_credential.py "<encrypted-string-from-dbeaver>"

Or pipe:
    echo "<encrypted>" | python scripts/decrypt_credential.py -
"""
import sys
from pathlib import Path

# Allow running as `python scripts/decrypt_credential.py ...` from api/ directory
_API_ROOT = Path(__file__).resolve().parent.parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from app.core.crypto import CredentialCipher, CryptoError


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    raw = sys.argv[1]
    if raw == "-":
        raw = sys.stdin.read().strip()

    try:
        cipher = CredentialCipher()
        print(cipher.decrypt(raw))
    except CryptoError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
