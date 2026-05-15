"""Generate a new Fernet key. Run once, store in .env / k8s Secret as FERNET_KEY."""
from cryptography.fernet import Fernet


def main() -> None:
    print(Fernet.generate_key().decode("utf-8"))


if __name__ == "__main__":
    main()
