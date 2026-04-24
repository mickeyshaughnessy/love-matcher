// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * LoveMatcherToken — soulbound access token for love-matcher.com
 *
 * - Non-transferable (soulbound): transfers are blocked after mint
 * - One token per address
 * - Payable mint: user pays MINT_PRICE to get access
 * - Owner can update price and withdraw treasury
 */
contract LoveMatcherToken is ERC721, Ownable {

    uint256 public mintPrice;
    uint256 private _nextTokenId;

    event Minted(address indexed to, uint256 tokenId);

    constructor(uint256 _mintPrice)
        ERC721("LoveMatcherToken", "LMT")
        Ownable(msg.sender)
    {
        mintPrice = _mintPrice;
    }

    // ----------------------------------------------------------------
    // Mint
    // ----------------------------------------------------------------

    function mint() external payable {
        require(msg.value >= mintPrice, "Insufficient payment");
        require(balanceOf(msg.sender) == 0, "Already has token");

        uint256 tokenId = _nextTokenId++;
        _safeMint(msg.sender, tokenId);
        emit Minted(msg.sender, tokenId);

        // Refund any overpayment
        if (msg.value > mintPrice) {
            payable(msg.sender).transfer(msg.value - mintPrice);
        }
    }

    // ----------------------------------------------------------------
    // Soulbound: block all transfers
    // ----------------------------------------------------------------

    function transferFrom(address, address, uint256) public pure override {
        revert("Soulbound: non-transferable");
    }

    function safeTransferFrom(address, address, uint256, bytes memory) public pure override {
        revert("Soulbound: non-transferable");
    }

    // ----------------------------------------------------------------
    // Owner controls
    // ----------------------------------------------------------------

    function setMintPrice(uint256 _price) external onlyOwner {
        mintPrice = _price;
    }

    function withdraw() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }

    // ----------------------------------------------------------------
    // View helpers
    // ----------------------------------------------------------------

    function hasToken(address addr) external view returns (bool) {
        return balanceOf(addr) == 0 ? false : true;
    }

    function totalMinted() external view returns (uint256) {
        return _nextTokenId;
    }
}
