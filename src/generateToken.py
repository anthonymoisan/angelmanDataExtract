# src/scripts/hash_password.py
import argparse
import getpass
import bcrypt

def main():
    p = argparse.ArgumentParser(description="Génère un hash bcrypt pour un mot de passe.")
    p.add_argument("--password", help="Mot de passe (optionnel). Si absent, demandé de façon sécurisée.")
    p.add_argument("--rounds", type=int, default=12, help="Work factor (cost), default 12")
    args = p.parse_args()

    pwd = args.password
    if not pwd:
        pwd = getpass.getpass("Password: ")

    hashed = bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt(args.rounds))
    print(hashed.decode("utf-8"))  # copier/coller dans l'INI ou variable d'env

if __name__ == "__main__":
    main()
