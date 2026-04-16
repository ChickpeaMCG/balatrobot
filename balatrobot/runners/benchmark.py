import time

from balatrobot.bots.flush_bot import FlushBot


def benchmark_multi_instance():
    # Benchmark the game states per second for different bot counts
    bot_counts = range(1, 21, 3)
    for bot_count in bot_counts:
        target_t = 50 * bot_count
        t = 0
        bots = []
        for i in range(bot_count):
            mybot = FlushBot(
                deck="Blue Deck",
                stake=1,
                seed=None,
                challenge=None,
                bot_port=12348 + i,
            )
            bots.append(mybot)

        try:
            for bot in bots:
                bot.start_balatro_instance()
            time.sleep(20)

            start_time = time.time()
            while t < target_t:
                for bot in bots:
                    bot.run_step()
                    t += 1
            end_time = time.time()

            t_per_sec = target_t / (end_time - start_time)
            print(f"Bot count: {bot_count}, t/sec: {t_per_sec}")
        finally:
            for bot in bots:
                bot.stop_balatro_instance()


if __name__ == "__main__":
    benchmark_multi_instance()
