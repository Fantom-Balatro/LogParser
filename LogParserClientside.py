import re

def parse_log_file(log_path, output_path):
    lines_out = []
    last_lives = 4

    # Persistent variables
    host = guest = host_mods = guest_mods = None
    deck = seed = seed_type = None
    is_host = None

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_lower = line.lower()

            if "enemyinfo" in line_lower:
                match = re.search(r"lives:(\d+)", line)
                if match:
                    new_lives = int(match.group(1))
                    if new_lives < last_lives:
                        lines_out.append("Lost a life")
                    last_lives = new_lives
                continue

            if "lobbyinfo message" in line_lower:
                if "host:" in line:
                    host = re.search(r"host: ([^ )]+)", line)
                    guest = re.search(r"guest: ([^ )]+)", line)
                    host = host.group(1) if host else None
                    guest = guest.group(1) if guest else None
                    host_mods = re.search(r"hostHash: ([^ )]+)", line)
                    guest_mods = re.search(r"guestHash: ([^ )]+)", line)
                    host_mods = host_mods.group(1) if host_mods else ""
                    guest_mods = guest_mods.group(1) if guest_mods else ""
                    is_host = "isHost: true" in line
                continue

            if "lobbyoptions" in line_lower:
                deck_match = re.search(r"\(back: ([^)]+)\)", line)
                seed_type_match = re.search(r"\(custom_seed: ([^)]+)\)", line)
                if deck_match:
                    deck = deck_match.group(1).strip()
                if seed_type_match:
                    seed_type = seed_type_match.group(1).strip()
                continue

            if "startgame message" in line_lower:
                seed_match = re.search(r"seed:\s*([^) ]+)", line)
                seed = seed_match.group(1) if seed_match else None

                enemy_line = f"Guest: {guest} (cached) (Enemy)" if is_host else f"Host: {host} (cached) (Enemy)"
                guest_line = f"Host: {host} (cached)" if is_host else f"Guest: {guest} (cached)"
                lines_out.extend([
                    enemy_line,
                    f"Host Mods: {host_mods}",
                    guest_line,
                    f"Guest Mods: {guest_mods}",
                    f"Deck: {deck if deck else 'None'}",
                    f"Seed: {seed if seed else 'Unknown'}",
                    f"custom_seed: {seed_type if seed_type else 'unknown'}"
                ])
                continue

            # Only process "Client sent" messages for this version
            if "client sent" not in line_lower:
                continue

            if "moneymoved" in line_lower:
                match = re.search(r"amount: *(-?\d+)", line)
                if match:
                    amount = int(match.group(1))
                    if amount >= 0:
                        lines_out.append(f"Gained ${amount}")
                    else:
                        lines_out.append(f"Spent ${abs(amount)}")
            elif "spentlastshop" in line_lower:
                match = re.search(r"amount: *(\d+)", line)
                if match:
                    lines_out.append(f"Spent ${match.group(1)} last shop")
            elif "usedcard" in line_lower:
                match = re.search(r"card:([^,\n]+)", line, re.IGNORECASE)
                if match:
                    raw = match.group(1).strip()
                    # Remove known prefixes like c_mp_ or j_mp_
                    clean = re.sub(r"^(c_mp_|j_mp_)", "", raw)
                    # Replace underscores with spaces, title-case the result
                    pretty = clean.replace("_", " ").title()
                    lines_out.append(f"Used {pretty}")

            elif "playhand" in line_lower:
                    continue  # Ignore this

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines_out))

# Run from command line
if __name__ == "__main__":
    input_file = input("Enter the path to the input log file: ").strip()
    output_file = input("Enter the path to the output text file: ").strip()
    parse_log_file(input_file, output_file)
    print(f"Log parsed and saved to {output_file}")
