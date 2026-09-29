import sys

INPUT_FILE = "accounts.txt"     # le fichier source
OUTPUT_FILE = "sorted.txt"   # le fichier résultat

with open(INPUT_FILE, "r", encoding="utf-8") as fin, \
     open(OUTPUT_FILE, "w", encoding="utf-8") as fout:

    for line in fin:
        parts = line.strip().split(":")
        if len(parts) >= 5:
            ID = parts[0]
            AUTH = parts[4]
            fout.write(f"{ID}:{AUTH}\n")