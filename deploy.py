import argparse, subprocess, sys, os, time
from datetime import datetime

"""
🤔 Love Matcher Deployment Script
- Environment setup
- Service management
- Health monitoring
- Logging setup
<Flow>
1. Parse environment and options
2. Start/check Redis
3. Launch API server
4. Start backup service
5. Launch monitoring
"""

def run_cmd(cmd, check=True):
    """Run shell command and return output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return None

def check_redis():
    """Verify Redis is running with correct config"""
    try:
        import redis
        r = redis.Redis(port=6378)
        info = r.info()
        print(f"✅ Redis running (version {info['redis_version']})")
        print(f"   Memory used: {info['used_memory_human']}")
        print(f"   Connected clients: {info['connected_clients']}")
        return True
    except:
        return False

def setup_env(env):
    """Setup environment and directory structure"""
    # Create required directories
    dirs = ['logs', 'data', 'data/redis']
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    
    # Set environment variable
    os.environ['LOVE_MATCHER_ENV'] = env
    
    # Create env-specific Redis config
    redis_conf = f"""
port 6378
daemonize yes
dir ./data/redis
dbfilename dump-{env}.rdb
logfile ./logs/redis-{env}.log
    """
    with open(f'data/redis/redis-{env}.conf', 'w') as f:
        f.write(redis_conf)

def start_redis(env):
    """Start Redis with environment config"""
    if not check_redis():
        print("Starting Redis...")
        run_cmd(f"redis-server data/redis/redis-{env}.conf")
        time.sleep(2)
        if check_redis():
            print("Redis started successfully")
        else:
            print("Failed to start Redis")
            sys.exit(1)

def start_api():
    """Start API server"""
    print("Starting API server...")
    api_proc = subprocess.Popen(
        ["python", "api_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)
    
    # Check if API is responding
    try:
        import requests
        r = requests.get('http://localhost:42068/ping')
        if r.status_code == 200:
            print("✅ API server running")
            return api_proc
        else:
            print("API server health check failed")
            api_proc.kill()
            sys.exit(1)
    except:
        print("Failed to connect to API server")
        api_proc.kill()
        sys.exit(1)

def start_backup(env, bucket):
    """Start backup service"""
    print("Starting backup service...")
    backup_proc = subprocess.Popen(
        ["python", "backup_service.py", "--bucket", bucket],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(1)
    if backup_proc.poll() is None:
        print("✅ Backup service running")
        return backup_proc
    else:
        print("Failed to start backup service")
        sys.exit(1)

def start_monitor():
    """Start monitoring dashboard"""
    print("Starting monitoring dashboard...")
    monitor_proc = subprocess.Popen(
        ["python", "monitor.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(1)
    if monitor_proc.poll() is None:
        print("✅ Monitor running")
        return monitor_proc
    else:
        print("Failed to start monitor")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Love Matcher Deployment')
    parser.add_argument(
        '--env',
        choices=['dev', 'staging', 'prod'],
        default='dev',
        help='Deployment environment'
    )
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Start monitoring dashboard'
    )
    args = parser.parse_args()

    print(f"\n💕 Love Matcher Deployment - {args.env.upper()}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Setup environment
    setup_env(args.env)
    
    # Import config after env is set
    from config import backup_config
    bucket = backup_config['bucket']

    try:
        # Start services
        start_redis(args.env)
        api_proc = start_api()
        backup_proc = start_backup(args.env, bucket)
        
        # Start monitor if requested
        monitor_proc = start_monitor() if args.monitor else None
        
        print("\n✨ Deployment complete!")
        print("\nPress Ctrl+C to shut down...\n")
        
        # Keep running until interrupted
        try:
            while True:
                time.sleep(1)
                # Check if any process died
                for name, proc in [
                    ('API', api_proc),
                    ('Backup', backup_proc),
                    ('Monitor', monitor_proc)
                ]:
                    if proc and proc.poll() is not None:
                        print(f"{name} service died!")
                        raise KeyboardInterrupt
                        
        except KeyboardInterrupt:
            print("\nShutting down...")
            
            # Kill processes
            for proc in [api_proc, backup_proc, monitor_proc]:
                if proc:
                    proc.kill()
                    proc.wait()
                    
            # Stop Redis gracefully
            run_cmd("redis-cli -p 6378 shutdown", check=False)
            print("Shutdown complete")

    except Exception as e:
        print(f"Deployment failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
