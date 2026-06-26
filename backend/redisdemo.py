import redis

REDIS_URL = 'redis://localhost:6379/0'
redis_client = redis.from_url(REDIS_URL, decode_responses=True,encoding='utf-8')
redis_client.set('user:1001:name','Alice')
namevalue = redis_client.get('user:1001:name')
print(namevalue)

is_ex = redis_client.exists('user:1001:name')
print(is_ex)

redis_client.delete('user:1001:name')

namevalue = redis_client.get('user:1001:name')
print(namevalue)