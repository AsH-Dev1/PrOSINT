"""Twitter/X Intelligence - historical tweets, followers, bio via snscrape."""
import re, asyncio, subprocess, json

async def twitter_lookup(username: str) -> dict:
    username = username.strip().lstrip("@")
    result = {"username": username, "profile": {}, "recent_tweets": [], "error": ""}

    try:
        proc = await asyncio.create_subprocess_exec(
            "snscrape", "--jsonl", "--max-results", "5", "twitter-user", username,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0 and stdout:
            lines = stdout.decode().strip().split("\n")
            if lines and lines[0]:
                try:
                    d = json.loads(lines[0])
                    result["profile"] = {
                        "display_name": d.get("displayname", ""),
                        "description": d.get("description", ""),
                        "followers": d.get("followersCount", 0),
                        "following": d.get("friendsCount", 0),
                        "tweets_count": d.get("statusesCount", 0),
                        "created": d.get("created", ""),
                        "location": d.get("location", ""),
                        "verified": d.get("verified", False),
                        "profile_url": d.get("url", ""),
                        "avatar": d.get("profileImageUrl", ""),
                    }
                except: pass
        if stderr:
            result["error"] = stderr.decode()[:200]
    except FileNotFoundError:
        result["error"] = "snscrape not installed. Run: pip install snscrape"
    except Exception as e:
        result["error"] = str(e)

    return result


async def twitter_timeline(username: str, max_results: int = 20) -> list[dict]:
    tweets = []
    try:
        proc = await asyncio.create_subprocess_exec(
            "snscrape", "--jsonl", "--max-results", str(max_results),
            "twitter-user", username.strip().lstrip("@"),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if stdout:
            for line in stdout.decode().strip().split("\n"):
                try:
                    d = json.loads(line)
                    tweets.append({
                        "date": d.get("date", ""),
                        "content": d.get("content", "")[:300],
                        "url": d.get("url", ""),
                        "likes": d.get("likeCount", 0),
                        "retweets": d.get("retweetCount", 0),
                        "replies": d.get("replyCount", 0),
                        "hashtags": d.get("hashtags", []),
                        "mentions": d.get("mentionedUsers", []),
                    })
                except: pass
    except: pass
    return tweets[:max_results]
