import re

def parse_log_file(log_path, output_path):
    lines_out = []
    last_lives = 4

    # Persistent variables
    host = guest = host_mods = guest_mods = None
    deck = seed = seed_type = None
    is_host = None

    # Enemy location mapping and tracking
    enemy_location_map = {
        "bl_small": "Small blind",
        "bl_big": "Big blind",
        "bl_mp_nemesis": "Nemesis Blind",
    }
    known_enemy_locations = set(enemy_location_map.values())

    # Function to handle final jokers for client sent and got messages
    def handle_final_jokers(line, lines_out, sender):
        # Client sent format: "action:receiveEndGameJokers,keys:j_mp_conjoined_joker;j_mp_conjoined_joker;j_card_sharp;j_bloodstone;"
        # Client got format: "keys: j_mp_hanging_chad;j_photograph;j_mp_hanging_chad;j_bloodstone;"
        if "Client sent message" in line:
            match = re.search(r"keys:([a-zA-Z0-9_;]+)", line)
        elif "Client got" in line:
            match = re.search(r"keys: ([a-zA-Z0-9_;]+)", line)
        else:
            return

        if match:
            jokers = match.group(1).split(';')
            # Count joker occurrences
            joker_counts = {}
            for joker in jokers:
                clean_joker = re.sub(r"^(j_mp_|j_)", "", joker).replace("_", " ").title()
                joker_counts[clean_joker] = joker_counts.get(clean_joker, 0) + 1
            # Format output to show count
            final_jokers = [f"{joker} x{count}" if count > 1 else joker for joker, count in joker_counts.items()]
            lines_out.append(f"Final {sender} Jokers: {', '.join(final_jokers)}")

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if "enemyInfo" in line:
                match = re.search(r"lives:(\d+)", line)
                if match:
                    new_lives = int(match.group(1))
                    if new_lives < last_lives:
                        lines_out.append("Lost a life")
                    last_lives = new_lives
                continue

            if "lobbyInfo message" in line:
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

            if "lobbyOptions" in line:
                # Extract the final seen value each time
                deck_match = re.search(r"\(back: ([^)]+)\)", line)
                seed_type_match = re.search(r"\(custom_seed: ([^)]+)\)", line)
                if deck_match:
                    deck = deck_match.group(1).strip()
                if seed_type_match:
                    seed_type = seed_type_match.group(1).strip()
                continue

            if "startGame message" in line:
                # Extract the seed value from the startGame message
                seed_match = re.search(r"seed:\s*([^) ]+)", line)
                seed = seed_match.group(1) if seed_match else None

                # Output full block of relevant information
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

            # Only process these if it's a received line
            if "Client got" not in line and "Client sent" not in line:
                continue

            if "Client got" in line:
                if "soldJoker" in line:
                    lines_out.append("Sold Joker")
                elif "loc_shop" in line:
                    lines_out.append("Shop")
                elif "loc_selecting" in line:
                    continue  # Ignore this
                elif "spentLastShop" in line:
                    amount_match = re.search(r"amount: (\d+)", line)
                    if amount_match:
                        lines_out.append(f"Spent ${amount_match.group(1)}")
                elif "endPvP" in line:
                    lines_out.append("Enemy Lost PvP" if "lost:false" in line else "Enemy Won PvP")
                elif "enemyLocation" in line:
                    loc_match = re.search(r"loc_playing-([a-zA-Z0-9_]+)", line)
                    if loc_match:
                        loc_code = loc_match.group(1)
                        if loc_code in enemy_location_map:
                            readable = enemy_location_map[loc_code]
                        else:
                            if loc_code.startswith("bl_"):
                                readable = loc_code[3:].replace("_", " ").title()
                            else:
                                readable = loc_code.replace("_", " ").title()
                            if readable not in known_enemy_locations:
                                known_enemy_locations.add(readable)
                        lines_out.append(readable)

                # Handle the "Client got" final jokers messages
                if "Client got message" in line and "receiveEndGameJokers" in line:
                    handle_final_jokers(line, lines_out, "Received")

                # Handle the "Client got magnet" usage
                if "magnet" in line:
                    lines_out.append("Used Magnet")

            # Handle the "Client sent" final jokers messages
            if "Client sent message" in line:
                if "receiveEndGameJokers" in line:
                    handle_final_jokers(line, lines_out, "Sent")

                # Handle the magnetResponse for jokers
                if "magnetResponse" in line:
                    match = re.search(r"key: ?([a-zA-Z0-9_]+)", line)
                    if match:
                        joker_raw = match.group(1)
                        clean_joker = re.sub(r"^(j_mp_|j_)", "", joker_raw).replace("_", " ").title()
                        lines_out.append(f"Magnet Got {clean_joker}")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines_out))

# Run from command line
if __name__ == "__main__":
    input_file = input("Enter the path to the input log file: ").strip()
    output_file = input("Enter the path to the output text file: ").strip()
    parse_log_file(input_file, output_file)
    print(f"Log parsed and saved to {output_file}")
