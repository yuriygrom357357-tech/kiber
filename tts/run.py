import asyncio, json, os, edge_tts
job = json.load(open("tts/job.json"))
os.makedirs("audio", exist_ok=True)
async def main():
    out = {}
    for it in job["items"]:
        c = edge_tts.Communicate(it["text"], job.get("voice","uk-UA-OstapNeural"), rate=job.get("rate","+0%"))
        words = []
        with open("audio/"+it["f"], "wb") as fh:
            async for ch in c.stream():
                if ch["type"] == "audio": fh.write(ch["data"])
                elif ch["type"] == "WordBoundary": words.append([ch["offset"]/1e7, ch["text"]])
        out[it["f"]] = words
        print("ok", it["f"], len(words))
    json.dump(out, open("tts/timing.json","w"), ensure_ascii=False)
asyncio.run(main())
