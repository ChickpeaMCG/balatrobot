from balatrobot.bots.replay_bot import ReplayBot
import argparse, time

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("replay", help="Path to .replay.json file")
    parser.add_argument("--port", type=int, default=12345)
    args = parser.parse_args()

    bot = ReplayBot(replay_path=args.replay, deck="Blue Deck", stake=1, seed=None, bot_port=args.port)
    bot.start_balatro_instance()
    print("Waiting for game to load...")
    time.sleep(15)
    try:
        bot.run()
    except KeyboardInterrupt:
        pass
    finally:
        if bot.sock:
            bot.sock.close()
        bot.stop_balatro_instance()
