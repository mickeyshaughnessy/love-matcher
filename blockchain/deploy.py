#!/usr/bin/env python3
"""
Deploy LoveMatcherToken to BASE (mainnet or Sepolia testnet).

Usage:
    python3 deploy.py --network sepolia   # testnet first
    python3 deploy.py --network mainnet   # when ready

Requirements:
    pip install web3 py-solc-x
    solc must be installed (py-solc-x handles this automatically)

After deployment, copy the contract address into config.py → SBT_CONTRACT_ADDRESS.
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from web3 import Web3
from solcx import compile_source, install_solc

install_solc("0.8.20")

NETWORKS = {
    "sepolia": config.BASE_SEPOLIA_RPC,
    "mainnet": config.BASE_RPC_URL,
}

MINT_PRICE_WEI = Web3.to_wei(config.SBT_MINT_PRICE_ETH, "ether")

def load_contract_source():
    sol_path = os.path.join(os.path.dirname(__file__), "LoveMatcherToken.sol")
    with open(sol_path) as f:
        return f.read()

def compile_contract(source):
    compiled = compile_source(
        source,
        output_values=["abi", "bin"],
        solc_version="0.8.20",
        base_path=os.path.dirname(__file__),
    )
    key = next(k for k in compiled if "LoveMatcherToken" in k)
    return compiled[key]["abi"], compiled[key]["bin"]

def deploy(network: str):
    rpc = NETWORKS[network]
    w3 = Web3(Web3.HTTPProvider(rpc))
    assert w3.is_connected(), f"Cannot connect to {rpc}"

    account = w3.eth.account.from_key(config.BASE_WALLET_KEY)
    print(f"Deploying from: {account.address}")
    print(f"Network:        {network}  ({rpc})")
    print(f"Mint price:     {config.SBT_MINT_PRICE_ETH} ETH")
    balance = w3.eth.get_balance(account.address)
    print(f"Wallet balance: {Web3.from_wei(balance, 'ether'):.4f} ETH")

    source = load_contract_source()
    abi, bytecode = compile_contract(source)

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(account.address)

    tx = Contract.constructor(MINT_PRICE_WEI).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 2_000_000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Tx sent: {tx_hash.hex()}")
    print("Waiting for confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    contract_address = receipt["contractAddress"]
    print(f"\nContract deployed: {contract_address}")
    print(f"Gas used:          {receipt['gasUsed']}")
    print(f"\nUpdate config.py → SBT_CONTRACT_ADDRESS = '{contract_address}'")

    # Save ABI alongside this script for frontend use
    abi_path = os.path.join(os.path.dirname(__file__), "LoveMatcherToken.abi.json")
    with open(abi_path, "w") as f:
        json.dump(abi, f, indent=2)
    print(f"ABI saved to {abi_path}")

    return contract_address

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", choices=["sepolia", "mainnet"], default="sepolia")
    args = parser.parse_args()
    deploy(args.network)
