from arcaina_bot import ArcainaBot
from datetime import datetime, timedelta
import os
import json

# Mock Gemini for testing
class MockGemini:
    def __init__(self, *args): pass
    def generate_response(self, m, context_data=None): return f"Mock Response to: {m}"
    def get_daily_quest(self, context_data=None): return "Mock Daily Quest"
    def get_level_up_praise(self, lvl, context_data=None): return f"Mock Praise for Lvl {lvl}"

def test_leveling():
    if os.path.exists('stats.json'): os.remove('stats.json')
    
    bot = ArcainaBot(api_key="mock")
    bot.ai = MockGemini()
    
    # Simulate 5 days of logins
    start_time = datetime.now().replace(hour=5, minute=0)
    for i in range(5):
        test_time = start_time + timedelta(days=i)
        print(f"Testing Day {i+1} at {test_time}")
        # Patching datetime.now for the bot
        import arcaina_bot
        original_now = arcaina_bot.datetime
        class MockDateTime:
            @classmethod
            def now(cls): return test_time
            @classmethod
            def strptime(cls, *args): return datetime.strptime(*args)
            @classmethod
            def fromisoformat(cls, *args): return datetime.fromisoformat(*args)
        arcaina_bot.datetime = MockDateTime
        
        resp = bot.process_message("test", has_image=True)
        print(resp)
        arcaina_bot.datetime = original_now

    # Check stats
    with open('stats.json', 'r') as f:
        stats = json.load(f)["user_stats"]
        print(f"\nFinal Stats: {stats}")
        assert stats["exp"] == 5
        assert stats["total_logins"] == 5

def test_penalty():
    if os.path.exists('stats.json'): os.remove('stats.json')
    bot = ArcainaBot(api_key="mock")
    bot.ai = MockGemini()
    
    # Week 1: Login only 3 days (4 missed, 1 excused = 3 unexcused * 2 = 6 EXP penalty)
    # But wait, we need some EXP first to see the penalty
    bot.db.update_stats(exp=10, days_logged_this_week=3)
    
    # Trigger penalty check by simulating time pass (8 days later)
    future_now = datetime.now() + timedelta(days=8)
    import arcaina_bot
    original_now = arcaina_bot.datetime
    class MockDateTime:
        @classmethod
        def now(cls): return future_now
        @classmethod
        def strptime(cls, *args): return datetime.strptime(*args)
        @classmethod
        def fromisoformat(cls, *args): return datetime.fromisoformat(*args)
    arcaina_bot.datetime = MockDateTime
    
    bot.process_message("trigger penalty check")
    
    with open('stats.json', 'r') as f:
        stats = json.load(f)["user_stats"]
        print(f"\nPenalty Stats: {stats}")
        # 10 EXP - 6 Penalty = 4 EXP
        assert stats["exp"] == 4
    
    arcaina_bot.datetime = original_now

if __name__ == "__main__":
    print("Running Tests...")
    test_leveling()
    test_penalty()
    print("Tests Passed!")
