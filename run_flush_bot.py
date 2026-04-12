import time
from flush_bot import FlushBot

bot = FlushBot(deck="Blue Deck", stake=1, seed=None, bot_port=12345)
bot.start_balatro_instance()
print("Waiting for game to load...")
time.sleep(15)

try:
    bot.run()
except KeyboardInterrupt:
    print("\nStopped.")
finally:
    if bot.sock:
        bot.sock.close()
    bot.stop_balatro_instance()
