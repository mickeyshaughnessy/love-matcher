import boto3, redis, logging, time, os, json, gzip, io
from datetime import datetime, timezone
from botocore.exceptions import ClientError

"""
🤔 Love Matcher Backup Service
- Hourly snapshots of user/match data
- Compressed backups to S3
- Retains 7 days of history
- Basic encryption of sensitive data
<Flow>
1. Check last backup state
2. Compress Redis dump
3. Upload to S3 with encryption
4. Cleanup old backups
"""

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class BackupService:
    def __init__(self, bucket, aws_profile='default'):
        session = boto3.Session(profile_name=aws_profile)
        self.s3 = session.client('s3')
        self.redis = redis.Redis(port=6378)
        self.bucket = bucket
        self.state = self._load_state()

    def _load_state(self):
        try:
            response = self.s3.get_object(
                Bucket=self.bucket, 
                Key='backup-state.json'
            )
            return json.loads(response['Body'].read())
        except:
            return {
                'last_backup': 0,
                'total_size': 0,
                'backup_count': 0,
                'last_error': None
            }

    def _save_state(self):
        state_buffer = io.BytesIO(json.dumps(self.state).encode())
        self.s3.upload_fileobj(
            state_buffer, 
            self.bucket, 
            'backup-state.json'
        )

    def backup_redis(self):
        try:
            if not self.redis.save():
                raise Exception("Redis SAVE failed")

            # Get Redis dump file
            dump_file = '/var/lib/redis/dump.rdb'
            timestamp = int(time.time())
            
            # Compress dump file in memory
            with open(dump_file, 'rb') as f, io.BytesIO() as compressed:
                with gzip.GzipFile(fileobj=compressed, mode='wb') as gz:
                    gz.write(f.read())
                compressed.seek(0)
                
                # Upload to S3 with server-side encryption
                key = f'redis/dump-{timestamp}.rdb.gz'
                self.s3.upload_fileobj(
                    compressed,
                    self.bucket,
                    key,
                    ExtraArgs={
                        'ServerSideEncryption': 'AES256',
                        'Metadata': {
                            'timestamp': str(timestamp),
                            'type': 'redis-dump'
                        }
                    }
                )
            
            size = os.path.getsize(dump_file)
            self.state.update({
                'last_backup': timestamp,
                'total_size': self.state['total_size'] + size,
                'backup_count': self.state['backup_count'] + 1,
                'last_error': None
            })
            self._save_state()
            
            logger.info(
                f'Redis backup uploaded: {key} ({size/1024/1024:.1f}MB)')
            return True

        except Exception as e:
            error = f'Redis backup failed: {str(e)}'
            logger.error(error)
            self.state['last_error'] = error
            self._save_state()
            return False

    def backup_metrics(self):
        try:
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
            
            # Get current metrics
            metrics = self.redis.hgetall('love:metrics')
            if not metrics:
                logger.info('No metrics to backup')
                return False

            # Compress metrics JSON
            metrics_data = {k.decode(): int(v) for k,v in metrics.items()}
            with io.BytesIO() as compressed:
                with gzip.GzipFile(fileobj=compressed, mode='wb') as gz:
                    gz.write(json.dumps(metrics_data).encode())
                
                compressed.seek(0)
                key = f'metrics/love-metrics-{timestamp}.json.gz'
                
                self.s3.upload_fileobj(
                    compressed,
                    self.bucket,
                    key,
                    ExtraArgs={
                        'ServerSideEncryption': 'AES256',
                        'Metadata': {
                            'timestamp': str(int(time.time())),
                            'type': 'metrics'
                        }
                    }
                )
            
            logger.info(f'Metrics backup uploaded: {key}')
            return True

        except Exception as e:
            error = f'Metrics backup failed: {str(e)}'
            logger.error(error)
            self.state['last_error'] = error
            self._save_state()
            return False

    def cleanup_old_backups(self, days=7):
        try:
            cutoff = int(time.time() - days * 86400)
            total_cleaned = 0

            paginator = self.s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket):
                for obj in page.get('Contents', []):
                    # Skip state file and recent backups
                    if obj['Key'] == 'backup-state.json':
                        continue
                        
                    if obj['LastModified'].timestamp() < cutoff:
                        self.s3.delete_object(
                            Bucket=self.bucket,
                            Key=obj['Key']
                        )
                        total_cleaned += 1

            if total_cleaned:
                logger.info(f'Cleaned up {total_cleaned} old backups')
            return total_cleaned

        except Exception as e:
            error = f'Cleanup failed: {str(e)}'
            logger.error(error)
            self.state['last_error'] = error
            self._save_state()
            return 0

    def check_health(self):
        try:
            # Check Redis
            info = self.redis.info()
            used_memory = info['used_memory_human']
            connected_clients = info['connected_clients']
            
            # Check API
            import requests
            r = requests.get('http://localhost:42069/ping', timeout=0.5)
            api_healthy = r.status_code == 200
            
            # Log health status
            logger.info(
                f'Health: Redis OK (Memory: {used_memory}, '
                f'Clients: {connected_clients}), '
                f'API {"OK" if api_healthy else "ERROR"}'
            )
            
            return True

        except Exception as e:
            error = f'Health check failed: {str(e)}'
            logger.error(error)
            self.state['last_error'] = error
            self._save_state()
            return False

    def run_backup(self):
        if self.check_health():
            self.backup_redis()
            self.backup_metrics()
            self.cleanup_old_backups()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Love Matcher Backup Service')
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--profile', default='default', help='AWS profile')
    args = parser.parse_args()

    backup = BackupService(args.bucket, args.profile)
    
    while True:
        try:
            backup.run_backup()
            # Run every hour
            time.sleep(3600)
        except KeyboardInterrupt:
            logger.info("Backup service stopped")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(300)  # Wait 5 min on error

if __name__ == '__main__':
    main()