import curses, redis, time, json, psutil, requests, threading, queue
from datetime import datetime
from collections import deque

"""
🤔 Love Matcher Monitor
- Real-time match activity tracking
- System health visualization
- Key performance metrics
- Live message flow monitoring
<Flow>
1. Base metrics every 1s
2. API health check every 5s
3. Match scan every 30s
4. Event log scrolling
"""

COLORS = {
    'love_pink': 205,      # Romantic pink
    'heart_red': 196,      # Heart red
    'match_green': 118,    # Success green
    'chat_purple': 171,    # Message purple
    'alert_yellow': 227,   # Alert yellow
    'stat_blue': 51        # Stat blue
}

class MetricsCollector(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.queue = queue.Queue()
        self.redis = redis.Redis(port=6378)
        self.running = True
        self.last_health_check = 0
        self.last_activity_check = 0
        self.events = deque(maxlen=100)

    def truncate(self, s, n=80):
        return (s[:n-3] + '...') if len(s) > n else s

    def check_recent_activity(self):
        try:
            # Get recent matches
            matches = self.redis.hgetall('love:matches')
            if matches:
                now = time.time()
                recent = []
                for match_id, data in matches.items():
                    match = json.loads(data)
                    if now - match['created_at'] < 3600:  # Last hour
                        recent.append(match)
                        
                if recent:
                    for match in sorted(recent, 
                                     key=lambda x: x['created_at'],
                                     reverse=True)[:3]:
                        age1 = match.get('user1', {}).get('age', '?')
                        age2 = match.get('user2', {}).get('age', '?')
                        score = match.get('compatibility_score', 0)
                        self.events.append(
                            f"💕 New Match! Ages {age1}&{age2} "
                            f"[Score: {score}%]"
                        )

            # Get recent messages
            messages = self.redis.hgetall('love:messages')
            if messages:
                recent_msgs = []
                for msg_id, data in messages.items():
                    msg = json.loads(data)
                    if now - msg['timestamp'] < 3600:
                        recent_msgs.append(msg)
                        
                if recent_msgs:
                    msg_count = len(recent_msgs)
                    active_chats = len(set(m['match_id'] for m in recent_msgs))
                    self.events.append(
                        f"💌 Last Hour: {msg_count} messages in "
                        f"{active_chats} active chats"
                    )
                    
        except Exception as e:
            self.events.append(f"⚠️ Activity check error: {str(e)}")

    def run(self):
        while self.running:
            try:
                now = time.time()
                
                # Get Redis stats
                info = self.redis.info()
                metrics = self.redis.hgetall('love:metrics')
                
                # Get system stats
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory()
                
                data = {
                    'ts': now,
                    'profiles': len(self.redis.hgetall('love:users')),
                    'matches': len(self.redis.hgetall('love:matches')),
                    'messages': len(self.redis.hgetall('love:messages')),
                    'mem_used': mem.percent,
                    'cpu_used': cpu,
                    'redis_mem': info['used_memory_human'],
                    'redis_clients': info['connected_clients'],
                    'metrics': {k.decode():int(v) for k,v in metrics.items()
                              } if metrics else {},
                    'api_health': True,
                    'events': list(self.events)
                }

                # API health check every 5s
                if now - self.last_health_check >= 5:
                    try:
                        r = requests.get('http://localhost:42069/ping',
                                       timeout=0.5)
                        data['api_health'] = r.status_code == 200
                        if r.status_code == 200:
                            api_metrics = r.json().get('metrics', {})
                            data['metrics'].update(api_metrics)
                    except:
                        data['api_health'] = False
                    self.last_health_check = now

                # Activity check every 30s
                if now - self.last_activity_check >= 30:
                    self.check_recent_activity()
                    self.last_activity_check = now

                self.queue.put(data)
                time.sleep(1)

            except Exception as e:
                self.queue.put({'error': str(e)})
                time.sleep(1)

    def stop(self):
        self.running = False

class LoveMatcherMonitor:
    def __init__(self):
        self.stats = deque(maxlen=60)  # 1 minute history
        self.collector = MetricsCollector()
        self.scroll_pos = 0

    def draw_gauge(self, win, value, y, x, width=10, color=None):
        filled = int((width * value) / 100)
        if color: win.attron(color)
        win.addstr(y, x, '█' * filled + '░' * (width - filled))
        if color: win.attroff(color)

    def run(self, stdscr):
        curses.start_color()
        curses.use_default_colors()
        
        # Initialize colors
        for i, (name, code) in enumerate(COLORS.items(), 1):
            curses.init_pair(i, code, -1)
            
        love_pink = curses.color_pair(1)
        heart_red = curses.color_pair(2)
        match_green = curses.color_pair(3)
        chat_purple = curses.color_pair(4)
        alert_yellow = curses.color_pair(5)
        stat_blue = curses.color_pair(6)

        curses.curs_set(0)  # Hide cursor
        self.collector.start()
        
        while True:
            try:
                while not self.collector.queue.empty():
                    stats = self.collector.queue.get_nowait()
                    if 'error' in stats:
                        raise Exception(stats['error'])
                    self.stats.append(stats)

                stdscr.clear()
                header = " 💕 LOVE MATCHER MONITOR 💕 "
                
                # Draw fancy border
                stdscr.attron(love_pink)
                stdscr.addstr(0, 0, "╔═" + "═" * len(header) + "═╗")
                stdscr.addstr(1, 0, "║ " + header + " ║")
                stdscr.addstr(2, 0, "╠" + "═" * (len(header) + 2) + "╣")
                stdscr.attroff(love_pink)

                if self.stats:
                    current = self.stats[-1]
                    health_color = match_green if current['api_health'] \
                                 else heart_red
                    
                    # System metrics
                    stdscr.attron(stat_blue)
                    stdscr.addstr(3, 0, f"║ 💻 System:")
                    stdscr.attroff(stat_blue)
                    
                    stdscr.addstr(4, 0, f"║ CPU: {current['cpu_used']:>3}% ")
                    self.draw_gauge(stdscr, current['cpu_used'], 4, 12, 
                                  color=health_color)
                    
                    stdscr.addstr(5, 0, f"║ Mem: {current['mem_used']:>3}% ")
                    self.draw_gauge(stdscr, current['mem_used'], 5, 12, 
                                  color=match_green)
                    
                    # Redis metrics
                    stdscr.attron(stat_blue)
                    stdscr.addstr(3, 25, "📊 Redis:")
                    stdscr.attroff(stat_blue)
                    
                    stdscr.addstr(4, 25, f"Mem: {current['redis_mem']}")
                    stdscr.addstr(5, 25, f"Clients: {current['redis_clients']}")

                    # Love Matcher stats
                    stdscr.attron(love_pink)
                    stdscr.addstr(6, 0, "╠" + "═" * (len(header) + 2) + "╣")
                    stdscr.addstr(7, 0, "║ 💘 Love Stats:")
                    stdscr.attroff(love_pink)
                    
                    metrics = current['metrics']
                    stdscr.addstr(8, 2, 
                        f"Profiles: {current['profiles']} | "
                        f"Today: +{metrics.get('profiles_created_today', 0)}"
                    )
                    stdscr.addstr(9, 2,
                        f"Matches: {current['matches']} | "
                        f"Today: +{metrics.get('matches_connected_today', 0)}"
                    )
                    stdscr.addstr(10, 2,
                        f"Messages: {current['messages']} | "
                        f"Today: +{metrics.get('messages_sent_today', 0)}"
                    )

                    # Event log
                    stdscr.attron(love_pink)
                    stdscr.addstr(11, 0, "╠" + "═" * (len(header) + 2) + "╣")
                    stdscr.addstr(12, 0, "║ 📋 Recent Activity:")
                    stdscr.attroff(love_pink)

                    events = current.get('events', [])
                    if events:
                        display_height = 5
                        self.scroll_pos = (self.scroll_pos + 1) % len(events)
                        for i in range(display_height):
                            idx = (self.scroll_pos + i) % len(events)
                            if idx < len(events):
                                stdscr.attron(chat_purple)
                                stdscr.addstr(13 + i, 2, events[idx][:50])
                                stdscr.attroff(chat_purple)

                    # Footer
                    stdscr.attron(love_pink)
                    stdscr.addstr(18, 0, "╚" + "═" * (len(header) + 2) + "╝")
                    stdscr.attroff(love_pink)
                    
                    stdscr.attron(alert_yellow)
                    stdscr.addstr(19, 0, "⌨️  q:Quit r:Reset")
                    stdscr.attroff(alert_yellow)

                stdscr.refresh()
                
                # Handle input
                stdscr.timeout(100)
                c = stdscr.getch()
                if c == ord('q'): 
                    break
                elif c == ord('r'): 
                    self.stats.clear()
                    self.scroll_pos = 0

            except KeyboardInterrupt:
                break
            except curses.error:
                pass
            except Exception as e:
                stdscr.clear()
                stdscr.addstr(0, 0, f"Error: {str(e)}")
                stdscr.refresh()
                time.sleep(1)

        self.collector.stop()

def main():
    monitor = LoveMatcherMonitor()
    curses.wrapper(monitor.run)

if __name__ == '__main__':
    main()