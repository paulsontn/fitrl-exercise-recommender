import time
import requests

for i in range(20):
    try:
        r = requests.get('http://127.0.0.1:8501', timeout=2)
        print('STATUS:' + str(r.status_code))
        break
    except Exception:
        time.sleep(1)
else:
    print('STATUS:NOT_READY')
