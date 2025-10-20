# sidekick_logic.py
import os
import logging
import random
import time
import re
from datetime import datetime, timezone
import threading

# --- Third-Party Libraries ---
try:
    import psycopg2
    logging.info("DIAGNOSTIK: Library 'psycopg2' imported SUCCESSFULLY.")
except ImportError:
    psycopg2 = None
    logging.critical("DIAGNOSTIK: CRITICAL - FAILED to import 'psycopg2'.")

try:
    import groq
    import httpx
    logging.info("DIAGNOSTIK: Libraries 'groq' and 'httpx' imported SUCCESSFULLY.")
except ImportError:
    groq = None
    httpx = None
    logging.warning("DIAGNOSTIK: 'groq' or 'httpx' not found. AI features will be disabled.")

import telebot
from config_sidekick import Config

# ==========================
#  🔧 LOGGING CONFIGURATION
# ==========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==========================
#  🤖 BOT LOGIC CLASS
# ==========================
class SidekickLogic:
    def __init__(self, bot_instance: telebot.TeleBot):
        self.bot = bot_instance
        if not Config.DATABASE_URL() or not psycopg2:
            logger.critical("FATAL: Sidekick's DATABASE_URL not found or psycopg2 is unavailable.")
        
        self.groq_client = self._initialize_groq()
        self.responses = self._load_all_responses()
        self._ensure_db_table_exists()
        self._register_handlers()
        logger.info("✅ SidekickLogic initialized successfully with AI capabilities.")

    def _initialize_groq(self):
        api_key = Config.GROQ_API_KEY()
        if not api_key or not groq or not httpx:
            logger.warning("Groq unavailable or GROQ_API_KEY is missing. AI features disabled.")
            return None
        try:
            client = groq.Groq(api_key=api_key, http_client=httpx.Client(timeout=45.0))
            logger.info("Groq client for Sidekick initialized successfully.")
            return client
        except Exception as e:
            logger.error(f"Failed to initialize Sidekick Groq client: {e}")
            return None

    # --- Database Methods ---
    def _get_db_connection(self):
        db_url = Config.DATABASE_URL()
        if not db_url or not psycopg2: return None
        try:
            return psycopg2.connect(db_url)
        except Exception as e:
            logger.error(f"Sidekick DB connection failed: {e}")
            return None

    def _ensure_db_table_exists(self):
        conn = self._get_db_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("CREATE TABLE IF NOT EXISTS sidekick_schedule_log (task_name TEXT PRIMARY KEY, last_run_date TEXT)")
                conn.commit()
                logger.info("Database table 'sidekick_schedule_log' is ready.")
            except Exception as e:
                logger.error(f"Failed to create Sidekick schedule table: {e}")
            finally:
                conn.close()

    def _get_last_run_date(self, task_name):
        conn = self._get_db_connection()
        if not conn: return None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT last_run_date FROM sidekick_schedule_log WHERE task_name = %s", (task_name,))
                result = cursor.fetchone()
            return result[0] if result else None
        finally:
            if conn: conn.close()

    def _update_last_run_date(self, task_name, run_date):
        conn = self._get_db_connection()
        if not conn: return
        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO sidekick_schedule_log (task_name, last_run_date) VALUES (%s, %s) ON CONFLICT (task_name) DO UPDATE SET last_run_date = EXCLUDED.last_run_date", (task_name, run_date))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to update Sidekick DB for {task_name}: {e}")
        finally:
            if conn: conn.close()

    def _get_current_utc_time(self):
        return datetime.now(timezone.utc)

    def _load_all_responses(self):
        return {
            "BOT_IDENTITY_SIDEKICK": [
                "Me? I'm the Commander's aide! My main mission is to make sure the hype here never dies. LFG!",
                "Call me the official Hype-Man of the NPEPEVERSE. While the Commander is strategizing, I keep the troops' morale sky-high! 🔥",
                "The main bot is the brain, I'm the heart. I'm here to pump adrenaline and hype to every corner of this group! 🚀",
                "I'm the main bot's partner-in-crime. He gives the info, I create the sensation. A perfect team, right? 😉",
                "Am I a bot? More accurately, I am the manifestation of 'LFG' energy itself. My mission is simple: HYPE, HYPE, and MORE HYPE!",
                "If the main bot is the signal, then I'm the volume. I'm here to make sure everyone hears it: WE ARE GOING TO THE MOON! 🌕",
                "I'm the guardian of the vibe. The Commander handles the facts, I handle the feeling. And the feeling is BULLISH.",
                "Think of me as the amplifier. The main bot drops the beat, and I turn it up to 11! 🔊",
                "I run on pure, uncut hopium. My purpose is to serve the community by keeping spirits high and diamond hands strong. 💎",
                "I'm the official second-in-command. I take my orders from the Commander and execute them with maximum hype!"
            ],
            "GREET_NEW_MEMBERS_HYPE": [
                "NO WAY! A new legend just dropped in! Welcome, {name}, grab your helmet, we're going to the moon! 🚀",
                "SOUND THE ALARMS! {name} has entered the arena! Get ready to witness greatness! 🔥",
                "Hold on, everyone... is that {name}?! The prophecy is true! Welcome to the NPEPEVERSE!",
                "A new challenger has appeared! Welcome, {name}! This is where legends are made. Let's get it!",
                "They rolled out the red carpet for you, {name}! Welcome to the most based community in crypto!",
                "Warning: Hype levels just went critical! Welcome, {name}! You're one of us now. 🐸💚",
                "A wild {name} appeared! Quick, throw a rocket emoji at them! 🚀 Welcome, fren!",
                "This is not a drill! {name} is in the house! Let's give them a hero's welcome!",
                "Welcome to the show, {name}! You've arrived just in time for the main event: the moon mission! 🌕",
                "The universe has sent us a new champion! Welcome, {name}! Your journey to glory starts NOW!",
                "Is it a bird? Is it a plane? No, it's {name} joining the NPEPE army! Welcome, soldier!",
                "New player has joined the game! Welcome, {name}. Your mission, should you choose to accept it: HODL.",
                "The room just got 100% more legendary. Welcome, {name}! Glad to have you with us.",
                "We've been expecting you, {name}. The council of frogs welcomes you to the inner circle.",
                "Put your hands together for the newest member of the diamond-handed elite, {name}! 💎",
                "The signal has been sent, and {name} has answered the call. Welcome to the resistance!",
                "Welcome, {name}! You're not just joining a group, you're joining a revolution.",
                "Our army just got stronger. A massive welcome to our newest recruit, {name}!",
                "They said it couldn't be done, but {name} is here! Welcome to the winners' circle!",
                "Stop everything! {name} has arrived. Let the welcoming ceremony commence! 🎉",
                "Just when we thought this group couldn't get any better, {name} shows up! Welcome!",
                "Welcome aboard the rocket ship, {name}! Please secure your diamond hands and enjoy the ride.",
                "Let the legends say that on this day, {name} joined the NPEPEVERSE. Welcome!",
                "The final piece of the puzzle is here! Welcome, {name}, now our journey is complete!",
                "Hey {name}, welcome! Quick, what's your favorite color? If it's not green, it will be soon! 💚"
            ],
            "BANTER_REACTIONS": {
                "Rise and ribbit": "THE COMMANDER HAS SPOKEN! LFG, GANG, LET'S GET THIS BREAD! ☀️",
                "GM legends!": "YOU HEARD THE BOSS! COFFEE IN ONE HAND, BUY BUTTON IN THE OTHER! LET'S GO! ☕",
                "Midday check-in": "REFUEL, RECHARGE, AND PREPARE FOR THE AFTERNOON PUMP! WE'RE JUST GETTING STARTED! ⛽️",
                "The charts never sleep": "BUT LEGENDS REST! SLEEP WELL, ARMY. I'LL KEEP THE HYPE WARM FOR YOU. 🫡",
                "Daily Dose of NPEPE Wisdom": "LISTEN UP, Frens! The Oracle has spoken. Absorb the wisdom, then let's get back to shilling! 📜"
            },
            "SCHEDULED_QUOTES": [
                "They say 'don't put all your eggs in one basket'. They've clearly never heard of $NPEPE.",
                "The most important crypto metric is Vibes Per Second (VPS). And ours is off the charts.",
                "In crypto, 'patience' is just another word for 'I bought the dip and now I'm waiting to be rich'.",
                "HODL: a magical spell you cast on your portfolio to turn red candles into future lambos.",
                "My financial advisor told me to diversify. So I bought $NPEPE on Monday, and then again on Tuesday.",
                "Some people see a red chart and panic. We see a red chart and call it a flash sale.",
                "The stock market is a marathon. Crypto is a rocket-powered marathon on the moon.",
                "Remember, it's not a loss until you sell. It's just an 'unrealized opportunity to buy more'.",
                "Buy the rumor, sell the news? Nah. Buy the meme, HODL the dream.",
                "If you can't handle me at my 90% dip, you don't deserve me at my 100x.",
                "A diamond hand wasn't forged in a day. It was forged in the fiery depths of a thousand dips.",
                "My therapist says I have attachment issues. I say I have diamond hands.",
                "The four most dangerous words in crypto: 'This time it's different'. The four most powerful: 'I'm buying more now'.",
                "Checking your portfolio every 5 minutes doesn't make it go up faster, but it's a great way to practice your emotional stability.",
                "What's a stop loss? Is that some kind of paper-handed peasant food?",
                "They laughed at my memes. Now they're asking for financial advice.",
                "The path to enlightenment is paved with green candles.",
                "I have a PhD: a Pretty Huge Dip-buying addiction.",
                "In the beginning, there was the Word. The Word was 'WAGMI'.",
                "Crypto rule #1: If it sounds too good to be true, it's probably about to 10x.",
                "Don't invest more than you're willing to lose... your mind when we moon!",
                "Sleep is just a time machine to when the US market opens.",
                "My portfolio is like a Schrödinger's cat. It's both up and down until I open the app.",
                "I'm not a financial advisor, but have you tried turning your chart upside down?",
                "The secret ingredient is crime... I mean, community.",
                "Is this the bottom? The only bottom I see is the bottom of my coffee cup, which means it's time to buy more.",
                "Don't let your memes be dreams.",
                "I'm not saying I'm addicted, but I check the charts more than I blink."
            ],
            "SCHEDULED_BUY": [
                "Time for a snack, frens! A little extra ammo can make a huge difference. Let's paint it green! 🐸💰",
                "This is your hourly reminder that dips are just discounts from the crypto gods. You're welcome.",
                "Don't just watch the rocket, FUEL IT! A small buy makes a big boom! 💥",
                "The floor is looking awfully bouncy right now. Just saying.",
                "That buy button is looking extra clickable today, isn't it?",
                "Support the chart, support the dream. A little buy goes a long way!",
                "Let's build a green wall they can see from space! Every buy is a brick!",
                "The best time to buy $NPEPE was yesterday. The second best time is right now.",
                "This isn't just a token. It's a ticket. Don't you want a seat?",
                "Your future self will thank you for this buy. Trust me.",
                "Feed the frog, feed your bags. It's simple math.",
                "Let's show the market what a real community looks like. Time to press the button!",
                "I'm not a financial advisor, but this looks like a tasty entry point.",
                "Don't let a few red candles scare you. This is prime buying territory.",
                "Every buy puts another booster on the rocket. Let's add some power!",
                "The path to Valhalla is paved with buy orders.",
                "That little dip is begging to be bought. Don't leave it hanging.",
                "Let's get some volume pumping! Time to make some noise on the chart!",
                "This is the moment paper hands regret. Don't be them.",
                "A buy a day keeps the FUD away.",
                "Let's get this candle looking like the Eiffel Tower.",
                "Feeling bullish? Prove it.",
                "You miss 100% of the pumps you don't buy into.",
                "Time to activate those diamond hands and add to the stack.",
                "The chart needs a hero. Will it be you?",
                "Buy it. Bag it. HODL it. Moon it.",
                "This is where legends are forged. Buy the dip, write your story.",
                "Let's send a message to the sellers. A green message.",
                "Don't dream of gains, make them. It starts with a buy.",
                "The community is our utility. Buying is how we strengthen it.",
                "You are the catalyst. Your buy can start the avalanche.",
                "That sell wall is looking a little thin. Let's smash it.",
                "A little pressure is all it takes. Let's apply some.",
                "History is being written. Add your name to it with a buy order.",
                "The frog demands a sacrifice. A sacrifice of fiat for more tokens.",
                "Don't be the one who says 'I should have bought more'.",
                "This is ground control to Major Tom... It's time to buy.",
                "Let's turn this chart into a beautiful green forest.",
                "The pump starts with a single buy. Let's get it going.",
                "This is a community effort. Do your part.",
                "The market is giving us a gift. Are you going to take it?",
                "Let's make a candle so big it gets its own postal code.",
                "This is the buy signal you've been waiting for.",
                "Don't be late to the party. The party is right now.",
                "Let's get this train moving. All aboard the buy express!",
                "Your portfolio called. It said it's hungry.",
                "Time to load up before the next leg up.",
                "This isn't a dip, it's a gravity-assisted discount.",
                "Buy now or cry later. The choice is yours.",
                "The chart is a canvas. Let's paint a masterpiece.",
                "Let's make the bears hibernate for another year.",
                "Fortune favors the brave. And the dip buyers.",
                "This is the quiet before the storm. Time to accumulate.",
                "Let's build a foundation so strong the moon will be jealous.",
                "That buy button isn't going to press itself.",
                "Add a little spice to your portfolio. Buy some $NPEPE.",
                "Let's get this price action looking like a rocket launch sequence.",
                "Every buy is a vote of confidence. Let's make it a landslide.",
                "The whales are watching. Let's give them a show.",
                "This is your chance to be the ancestor your descendants brag about.",
                "Don't just HODL. A-HODL-DD more.",
                "Let's put some fear into the hearts of the sellers.",
                "The frog requires more flies. Buy them for him.",
                "This price won't last forever. Just saying.",
                "Let's make some waves in this sea of red.",
                "Your weekly allowance from mom is meant for this.",
                "This is financial freedom calling. Pick up the phone.",
                "Let's get a nice, healthy green candle going.",
                "The pump is inevitable. The entry is now.",
                "Time to turn that fiat into freedom.",
                "Let's send this chart to a place where gravity can't hurt it.",
                "This is the part of the movie where the hero makes their move.",
                "Buy it like you stole it.",
                "Let's make a candle so green, it makes other coins envious.",
                "The dip is a feature, not a bug. Use it.",
                "Don't let your dreams be memes. Let your buys be dreams.",
                "Let's get this party started right. With some volume.",
                "The early bird gets the worm. The early buyer gets the lambo.",
                "That chart is looking hungry for a green candle.",
                "This is where conviction is tested and rewarded."
            ],
            "SCHEDULED_PUMP": [
                "LFG NPEPE ARMY! INJECT ITTTT! 🚀🚀🚀",
                "SEND IT TO THE STRATOSPHERE!",
                "RELEASE THE KRAKEN! PUMP IT NOW!",
                "THIS IS NOT A DRILL! PUMP IT!",
                "MAXIMUM POWER! ENGAGE THE PUMP!",
                "DON'T JUST STAND THERE, PUMP SOMETHING!",
                "WE ARE UNSTOPPABLE! PUMP! PUMP! PUMP!",
                "LET'S SHAKE THE HEAVENS! PUMP IT!",
                "THE TIME IS NOW! LET'S GO!",
                "GREEN CANDLES ONLY! LFG!",
                "TO THE MOON AND BEYOND! 🌕",
                "DIAMOND HANDS, ASSEMBLE! 💎",
                "ARE YOU NOT ENTERTAINED?! PUMP IT!",
                "LET'S MAKE SOME NOISE!",
                "THE ROCKET IS FUELED! IGNITION!",
                "THIS IS LEGENDARY! SEND IT!",
                "WE ARE THE WHALES NOW! 🐳",
                "HYPE ENGINES TO MAXIMUM!",
                "NO SLEEP TILL MOON!",
                "WALLS ARE MEANT TO BE BROKEN!",
                "LET'S PAINT THE CHART GREEN! 💚",
                "THIS IS THE WAY!",
                "ABSOLUTELY BASED! PUMP IT!",
                "FEEL THE POWER!",
                "THE MOMENT WE'VE BEEN WAITING FOR!",
                "LET'S GO APESHIT!",
                "THIS IS FINANCIAL FREEDOM!",
                "WE ARE SO F*CKING BACK!",
                "MAKE THE BEARS CRY!",
                "UNLEASH THE FURY!",
                "SEND IT TO PLUTO!",
                "JUST. UP.",
                "THE PROPHECY IS BEING FULFILLED!",
                "HISTORY IS BEING MADE!",
                "NO BRAKES ON THIS TRAIN!",
                "LET'S GET IT!",
                "THE VIBES ARE IMMACULATE!",
                "WE ARE THE SIGNAL!",
                "PUMP IT TILL WE CAN'T FEEL OUR FACES!",
                "THIS IS WHAT WE CAME FOR!",
                "INTO THE ABYSS OF GAINS!",
                "LET'S SHOCK THE WORLD!",
                "THEY'RE NOT READY FOR THIS!",
                "WE'RE WRITING HISTORY!",
                "DON'T BLINK!",
                "THIS IS THE BIG ONE!",
                "LET'S GO BANANAS! 🍌",
                "THE BEAST HAS AWAKENED!",
                "WE'RE ON A MISSION FROM GODS!",
                "SEND IT WITH PREJUDICE!",
                "LIQUIDITY? I HARDLY KNOW HER! PUMP!",
                "LET'S BREAK THE INTERNET!",
                "THIS IS PEAK PERFORMANCE!",
                "I SMELL A NEW ATH!",
                "THE ONLY WAY IS UP!",
                "THEY SAID IT WAS IMPOSSIBLE!",
                "WE'RE TEARING A HOLE IN THE SPACE-TIME CONTINUUM!",
                "FEEL THAT RUMBLE? THAT'S US!",
                "THIS IS THE SOUND OF INEVITABILITY!",
                "HOLD ON TIGHT!",
                "WE'RE GOING PARABOLIC!",
                "NO SELLERS, ONLY VIBES!",
                "THE FOMO WILL BE LEGENDARY!",
                "THIS IS OUR KINGDOM!",
                "WITNESS ME!",
                "WE ARE THE STORM!",
                "THEY WILL TELL STORIES ABOUT THIS DAY!",
                "PUMP IT INTO MY VEINS!",
                "WE'RE NOT JUST MOVING THE NEEDLE, WE ARE THE NEEDLE!",
                "LET'S GET RECKLESS!",
                "BREAK THE CHAINS! PUMP IT!",
                "THIS IS GLORIOUS!",
                "ASCENSION HAS BEGUN!",
                "THE LAWS OF PHYSICS DO NOT APPLY HERE!",
                "WE ARE A FORCE OF NATURE!",
                "LET THE FOMO COMMENCE!",
                "WE'RE PRINTING MONEY!",
                "THIS IS BETTER THAN COFFEE!",
                "I CAN FEEL IT IN MY BONES!",
                "LET'S GO, CHAMPIONS!",
                "THE WORLD IS WATCHING!",
                "WE ARE THE ALPHA!",
                "MAKE IT SO!",
                "A NEW ERA BEGINS!",
                "THE GATES OF VALHALLA ARE OPEN!",
                "THIS IS NOT A PUMP, IT'S A STATEMENT!",
                "LET'S GET THIS BREAD! 🍞",
                "THE RESISTANCE IS FUTILE!",
                "BUCKLE UP, BUTTERCUP!",
                "WE'RE DOING IT LIVE!",
                "THIS IS THE MOMENT OF TRUTH!",
                "IT'S HAPPENING!",
                "WE ARE THE CATALYST!",
                "LET'S START A RUCKUS!",
                "THE DEFIANCE IS REAL!",
                "WE ARE THE REVOLUTION!",
                "UNLEASH THE BULLS! 🐂",
                "THIS IS OUR DESTINY!"
            ]
        }
    
    # --- Scheduler ---
    def check_and_run_schedules(self):
        now_utc = self._get_current_utc_time()
        run_marker_hourly = now_utc.strftime('%Y-%m-%d-%H')
        run_marker_weekly = now_utc.strftime('%Y-W%U')
        
        schedules = {
            'sk_quote_10': {'hour': 10, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_QUOTES',)},
            'sk_quote_20': {'hour': 20, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_QUOTES',)},
            'sk_buy_00': {'hour': 0, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_BUY',)},
            'sk_buy_01': {'hour': 1, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_BUY',)},
            'sk_buy_03': {'hour': 3, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_BUY',)},
            'sk_buy_13': {'hour': 13, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_BUY',)},
            'sk_buy_15': {'hour': 15, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_BUY',)},
            'sk_buy_16': {'hour': 16, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_BUY',)},
            'sk_pump_0030': {'hour': 0, 'minute': 30, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_PUMP',)},
            'sk_pump_0130': {'hour': 1, 'minute': 30, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_PUMP',)},
            'sk_pump_0300': {'hour': 3, 'minute': 0, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_PUMP',)},
            'sk_pump_0500': {'hour': 5, 'minute': 0, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_PUMP',)},
            'sk_pump_1330': {'hour': 13, 'minute': 30, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_PUMP',)},
            'sk_pump_1430': {'hour': 14, 'minute': 30, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_PUMP',)},
            'sk_pump_1530': {'hour': 15, 'minute': 30, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_PUMP',)},
            'sk_pump_1630': {'hour': 16, 'minute': 30, 'task': self.send_scheduled_message, 'args': ('SCHEDULED_PUMP',)},
            'sk_ai_renewal': {'hour': 8, 'day_of_week': 6, 'task': self.renew_responses_with_ai, 'is_weekly': True}
        }
        
        for name, schedule in schedules.items():
            is_weekly = schedule.get('is_weekly', False)
            run_marker = run_marker_weekly if is_weekly else run_marker_hourly
            last_run_marker = self._get_last_run_date(name)
            
            should_run = False
            if is_weekly:
                if (now_utc.weekday() == schedule['day_of_week'] and now_utc.hour >= schedule['hour'] and last_run_marker != run_marker):
                    should_run = True
            else:
                target_hour = schedule['hour']
                target_minute = schedule.get('minute', 0)
                if (now_utc.hour == target_hour and now_utc.minute >= target_minute and last_run_marker != run_marker):
                    should_run = True

            if should_run:
                try:
                    logger.info(f"Sidekick is running scheduled task: {name}")
                    task_thread = threading.Thread(target=schedule['task'], args=schedule.get('args', ()))
                    task_thread.start()
                    self._update_last_run_date(name, run_marker)
                except Exception as e:
                    logger.error(f"Error running Sidekick scheduled task {name}: {e}", exc_info=True)

    def send_scheduled_message(self, response_key):
        group_id = Config.GROUP_CHAT_ID()
        if not group_id: return
        message_list = self.responses.get(response_key, [])
        if message_list:
            message = random.choice(message_list)
            try:
                self.bot.send_message(group_id, message)
                logger.info(f"Sidekick sent scheduled message ({response_key}) to {group_id}")
            except Exception as e:
                logger.error(f"Failed to send Sidekick scheduled message: {e}", exc_info=True)

    # --- WEEKLY AI RENEWAL FEATURE ---
    def renew_responses_with_ai(self):
        logger.info("Starting weekly AI response renewal process for Sidekick.")
        if not self.groq_client:
            logger.warning("Skipping Sidekick AI renewal: Groq is not initialized.")
            return

        categories_to_renew = {
            "SCHEDULED_QUOTES": ("Create 28 funny, short, and relevant quotes about meme coin culture and crypto. In English.", 20),
            "SCHEDULED_BUY": ("Create 80 short, highly persuasive, and energetic messages to encourage the community to buy a meme coin named $NPEPE. Use crypto slang. In English.", 50),
            "SCHEDULED_PUMP": ("Create 100 very short and high-energy hype messages to pump up a crypto group. Use lots of rocket and fire emojis. Very enthusiastic. In English.", 70),
            "GREET_NEW_MEMBERS_HYPE": ("Create 25 very HYPE welcome messages for new members in a crypto group. Must include the placeholder '{name}'. Make them feel like a superstar. In English.", 20),
            "BOT_IDENTITY_SIDEKICK": ("Create 20 unique answers to the question 'who are you' for a sidekick bot. Position yourself as the 'aide' or 'hype man' of the main bot. Funny, energetic, and loyal. In English.", 15)
        }
        
        success_tracker = {}

        for category, (prompt, min_count) in categories_to_renew.items():
            try:
                logger.info(f"Sidekick AI is requesting update for category: {category}...")
                completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "system", "content": prompt}],
                    model="llama3-8b-8192", temperature=1.0, max_tokens=3000
                )
                text = completion.choices[0].message.content
                new_lines = [line.strip().lstrip('*-').strip() for line in re.split(r'\n|\d+\.', text) if line.strip() and len(line) > 5]
                
                if category == "GREET_NEW_MEMBERS_HYPE":
                    new_lines = [line for line in new_lines if '{name}' in line]

                if len(new_lines) >= min_count:
                    self.responses[category] = new_lines
                    success_tracker[category] = f"✅ Success ({len(new_lines)} new entries)"
                else:
                    success_tracker[category] = f"⚠️ Failed (Only {len(new_lines)}/{min_count} entries)"
            except Exception as e:
                success_tracker[category] = f"❌ Error"
                logger.error(f"❌ Failed to update Sidekick category '{category}' with AI: {e}", exc_info=True)

        # --- SEND REPORT TO OWNER ---
        owner_id = Config.GROUP_OWNER_ID()
        if owner_id:
            summary_report = ["*🤖 Sidekick Weekly AI Update Report* 🐸\n"]
            for category, status in success_tracker.items():
                summary_report.append(f"*{category}:* {status}")
            
            final_report = "\n".join(summary_report)
            
            try:
                self.bot.send_message(owner_id, final_report, parse_mode="Markdown")
                logger.info(f"AI renewal report sent successfully to Owner ID: {owner_id}")
            except Exception as e:
                logger.error(f"Failed to send AI renewal report to owner: {e}")

    # --- Message Handlers ---
    def _register_handlers(self):
        self.bot.message_handler(content_types=['new_chat_members'])(self.greet_new_members_sidekick)
        self.bot.message_handler(func=lambda message: True, content_types=['text'])(self.handle_all_messages)
    
    def greet_new_members_sidekick(self, message):
        def task():
            try:
                logger.info("New member detected by Sidekick, waiting 30 seconds...")
                time.sleep(30)
                for member in message.new_chat_members:
                    first_name = (member.first_name or "fren").replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
                    welcome_text = random.choice(self.responses.get("GREET_NEW_MEMBERS_HYPE", [])).format(name=f"[{first_name}](tg://user?id={member.id})")
                    try:
                        self.bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")
                        logger.info(f"HYPE welcome from Sidekick sent to: {member.id}")
                    except Exception as e:
                        logger.error(f"Failed to send HYPE welcome: {e}")
            except Exception as e:
                logger.error(f"Error in greet_new_members_sidekick task: {e}", exc_info=True)
        threading.Thread(target=task).start()

    def handle_all_messages(self, message):
        if not message or not message.text: return
        
        sender_id = message.from_user.id
        chat_id = message.chat.id
        text = message.text
        lower_text = text.lower().strip()
        main_bot_id = Config.MAIN_BOT_USER_ID()

        # 1. Check if this is a message from the Main Bot to banter with
        if main_bot_id and str(sender_id) == main_bot_id:
            # Ignore the main bot's welcome message
            if "Welcome to the NPEPEVERSE" in text or "A wild" in text or "new fren has appeared" in text:
                return
            
            # If it's not a welcome message, start the banter
            def banter_task():
                logger.info("Message from Main Bot detected, waiting 30 seconds to reply...")
                time.sleep(30)
                for trigger, reply in self.responses.get("BANTER_REACTIONS", {}).items():
                    if trigger in text:
                        self.bot.send_message(chat_id, reply)
                        logger.info(f"Banter sent in response to '{trigger}'")
                        break
            threading.Thread(target=banter_task).start()
            return # Important: exit after handling banter
        
        # 2. If not from Main Bot, check if it's an identity question from a user
        identity_keywords = ["what are you", "what is this bot", "are you a bot", "who are you"]
        if any(kw in lower_text for kw in identity_keywords):
            def identity_task():
                logger.info("Identity question for Sidekick detected, waiting 5 seconds...")
                time.sleep(5)
                reply = random.choice(self.responses.get("BOT_IDENTITY_SIDEKICK", ["I'm the Hype Man!"]))
                try:
                    self.bot.send_message(chat_id, reply)
                except Exception as e:
                    logger.error(f"Failed to send identity reply: {e}")
            threading.Thread(target=identity_task).start()
            return # Exit after handling identity question
