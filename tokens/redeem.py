import os
from solana.rpc.api import Client
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.transaction import Transaction
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (
    get_associated_token_address,
    transfer_checked,
    TransferCheckedParams,
    create_associated_token_account,
    CreateAssociatedTokenAccountParams
)

# Configuration
RPC_ENDPOINT = "https://api.mainnet-beta.solana.com"
MINT_ADDRESS = "5jriAd8yM9fRzuisg54Ch1k8sAmmbqRUfWKu87tRpump"
DEST_OWNER_ADDRESS = "HU22vPJUU36SrKzLfmq77ci3mzSQWwWUkkmbNjT8GEN4"
DECIMALS = 6
MEMBERS_FILE = "members.txt"

def main():
    # Prompt for user's private key (base58 encoded)
    private_key_str = input("Enter your wallet private key (base58): ").strip()
    try:
        keypair = Keypair.from_base58_string(private_key_str)
        print(f"Loaded wallet: {keypair.public_key}")
    except Exception as e:
        print(f"Error loading keypair: {e}")
        return

    # Prompt for name
    name = input("Enter your name for membership: ").strip()
    if not name:
        print("Name is required.")
        return

    client = Client(RPC_ENDPOINT)

    mint = PublicKey(MINT_ADDRESS)
    dest_owner = PublicKey(DEST_OWNER_ADDRESS)
    source_ata = get_associated_token_address(keypair.public_key, mint)
    dest_ata = get_associated_token_address(dest_owner, mint)

    # Get source balance
    balance_resp = client.get_token_account_balance(source_ata)
    if balance_resp.value is None:
        print("No token account found or no balance.")
        return

    amount = int(balance_resp.value.amount)
    if amount == 0:
        print("No tokens to transfer.")
        return

    print(f"Transferring {amount / (10 ** DECIMALS)} tokens...")

    # Prepare transaction
    tx = Transaction()

    # Check if destination ATA exists
    dest_balance_resp = client.get_token_account_balance(dest_ata)
    if dest_balance_resp.value is None:
        # Create destination ATA
        create_ix = create_associated_token_account(
            CreateAssociatedTokenAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                associated_token=dest_ata,
                payer=keypair.public_key,  # User pays for creation
                owner=dest_owner,
            )
        )
        tx.add(create_ix)
        print("Creating destination token account...")

    # Add transfer instruction
    transfer_ix = transfer_checked(
        TransferCheckedParams(
            program_id=TOKEN_PROGRAM_ID,
            source=source_ata,
            mint=mint,
            dest=dest_ata,
            owner=keypair.public_key,
            amount=amount,
            decimals=DECIMALS,
            signers=[],
        )
    )
    tx.add(transfer_ix)

    # Send transaction
    try:
        sig = client.send_transaction(tx, keypair)
        print(f"Transaction sent! Signature: {sig.value}")
        print("Tokens transferred successfully.")

        # Add name to members file
        with open(MEMBERS_FILE, "a") as f:
            f.write(f"{name}\n")
        print(f"Membership granted! Name '{name}' added to {MEMBERS_FILE}.")

    except Exception as e:
        print(f"Error sending transaction: {e}")

if __name__ == "__main__":
    print("WARNING: This script will transfer ALL your tokens of this mint to the specified address.")
    print("Ensure you have enough SOL for transaction fees.")
    print("Your private key will be read from input and not stored.")
    main()