from balatrobot.bots.replay_bot import ReplayBot
import argparse, time

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("replay", help="Path to .replay.json file")
    parser.add_argument("--port", type=int, default=12345)
    parser.add_argument("--speed", default="watch", choices=["fast", "watch"],
                        help="Game speed profile (default: watch)")
    parser.add_argument("--runs", type=int, default=1,
                        help="Number of times to replay (0 = unlimited)")
    args = parser.parse_args()

    bot = ReplayBot(replay_path=args.replay, deck="Blue Deck", stake=1, seed=None, bot_port=args.port, speed=args.speed)
    bot.start_balatro_instance()
    print("Waiting for game to load...")
    time.sleep(10)
    completed = 0
    try:
        while args.runs == 0 or completed < args.runs:
            bot.run()
            completed += 1
            bot.running = True  # reset for next replay
    except KeyboardInterrupt:
        pass
    finally:
        if bot.sock:
            bot.sock.close()
        bot.stop_balatro_instance()
