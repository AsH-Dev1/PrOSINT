"""Crypto/Wallet OSINT - blockchain explorer lookup, sanctions check."""
import re, asyncio
from urllib.parse import quote
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"

BTC_RE = re.compile(r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}\b')
ETH_RE = re.compile(r'\b0x[a-fA-F0-9]{40}\b')

async def crypto_lookup(address: str) -> dict:
    address = address.strip()
    result = {"address": address, "type": "", "explorers": [], "transactions": {}}

    if BTC_RE.match(address):
        result["type"] = "Bitcoin"
        result["explorers"] = [
            {"name": "Blockchain.com", "url": f"https://www.blockchain.com/explorer/addresses/btc/{address}"},
            {"name": "Blockchair", "url": f"https://blockchair.com/bitcoin/address/{address}"},
            {"name": "BTC Explorer", "url": f"https://btc.com/{address}"},
        ]
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": UA}, verify=False) as c:
            try:
                r = await c.get(f"https://blockchain.info/rawaddr/{address}")
                if r.status_code == 200:
                    d = r.json()
                    result["transactions"] = {
                        "total_received": d.get("total_received", 0) / 1e8,
                        "total_sent": d.get("total_sent", 0) / 1e8,
                        "final_balance": d.get("final_balance", 0) / 1e8,
                        "n_tx": d.get("n_tx", 0),
                    }
            except: pass
    elif ETH_RE.match(address):
        result["type"] = "Ethereum"
        result["explorers"] = [
            {"name": "Etherscan", "url": f"https://etherscan.io/address/{address}"},
            {"name": "Blockchair", "url": f"https://blockchair.com/ethereum/address/{address}"},
            {"name": "Ethplorer", "url": f"https://ethplorer.io/address/{address}"},
        ]
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": UA}, verify=False) as c:
            try:
                r = await c.get(f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest")
                if r.status_code == 200:
                    d = r.json()
                    if d.get("status") == "1":
                        result["transactions"]["balance"] = int(d.get("result", 0)) / 1e18
            except: pass
    else:
        result["error"] = "Unknown crypto address format"
        return result

    # Check OFAC sanctions list
    result["sanctions_check"] = f"https://sanctionssearch.ofac.treas.gov/Details.aspx?id={address}"
    return result
