from datetime import datetime
import re
import asyncio
import pytz
class a():
    def __init__(self):
        asyncio.run(self.b())

    async def b(self):
        print(datetime.now().strftime('%d %H'))


text = "本日は{YEAR}年です"
text = re.sub("{YEAR}", "2024", text)
print(datetime.now(tz=pytz.timezone("Asia/Tokyo")))

vo = [123,1324,234,23,423,4]
for e in range(5):
    print(f"{len(vo)}回")