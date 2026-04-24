# Love-Matcher Soulbound Token — Blockchain

Non-transferable (soulbound) ERC-721 access token on BASE.  
Users mint one token after signup; it gates access to chat and matching.

---

## Wallet

Deployer / treasury wallet address (safe to share):

```
0x4dEd25244aaF0D7c177EaDB6F789ecC3880296b8
```

**Private key and mnemonic live only in `config.py` (gitignored). Never commit them.**  
Ask Mickey for the credentials file if you need to deploy or withdraw.

---

## Contract: `LoveMatcherToken.sol`

- ERC-721, non-transferable — `transferFrom` and `safeTransferFrom` always revert
- One token per address (`balanceOf == 0` check at mint time)
- Payable mint at `mintPrice` (set at deploy, adjustable by owner)
- `hasToken(address)` view for frontend/backend checks
- `withdraw()` sends treasury balance to owner

---

## Setup

```bash
pip install web3 py-solc-x
```

---

## Deploy

```bash
python3 blockchain/deploy.py --network mainnet
```

Copy the printed contract address into `config.py → SBT_CONTRACT_ADDRESS`.

---

## Integration Plan

```
User flow:
  signup → [token gate] → chat / matching

1. After signup, frontend checks: does this wallet address hold a LMT?
2. If not → show "Buy Access" modal → MetaMask prompt → mint()
3. On mint success → backend marks profile token_verified=True (or check on-chain)
4. Chat and matching APIs check token_verified before responding
```

### Frontend (`public/js/app.js`)
- Add ethers.js (CDN, ~200 KB)
- `connectWallet()` — MetaMask popup, store address in profile
- `checkTokenOwnership(address)` — call `hasToken()` on contract
- `mintToken()` — send `mint()` tx with `mintPrice` value attached
- Show "Buy Access Token" step between signup completion and first chat

### Backend (`handlers.py`)
- New field `wallet_address` on user profile
- New endpoint `POST /verify-token` — calls `hasToken()` on BASE RPC, sets `token_verified=True`
- `chat` and `matching` handlers check `token_verified` before proceeding

### Contract interactions
- Read-only checks (no gas): use BASE public RPC directly from Python/JS
- Mint tx: user pays from their own wallet via MetaMask — we never touch user funds

---

## Files

```
blockchain/
  LoveMatcherToken.sol       — contract source
  deploy.py                  — deployment script
  LoveMatcherToken.abi.json  — generated after first deploy
  README.md                  — this file
```
