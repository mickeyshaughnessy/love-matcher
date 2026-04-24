// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * LoveMatcherToken — soulbound access token for love-matcher.com
 *
 * Self-contained ERC-721 (no external imports).
 * Non-transferable: transferFrom/safeTransferFrom always revert.
 * One token per address. Payable mint. Owner can set price and withdraw.
 */
contract LoveMatcherToken {

    // ----------------------------------------------------------------
    // ERC-165
    // ----------------------------------------------------------------
    function supportsInterface(bytes4 interfaceId) public pure returns (bool) {
        return interfaceId == 0x80ac58cd  // ERC721
            || interfaceId == 0x5b5e139f  // ERC721Metadata
            || interfaceId == 0x01ffc9a7; // ERC165
    }

    // ----------------------------------------------------------------
    // ERC-721 Metadata
    // ----------------------------------------------------------------
    string public name     = "LoveMatcherToken";
    string public symbol   = "LMT";

    // ----------------------------------------------------------------
    // Storage
    // ----------------------------------------------------------------
    address public owner;
    uint256 public mintPrice;
    uint256 private _nextTokenId;

    mapping(uint256 => address) private _owners;
    mapping(address => uint256) private _balances;

    // ----------------------------------------------------------------
    // Events
    // ----------------------------------------------------------------
    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Minted(address indexed to, uint256 tokenId);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    // ----------------------------------------------------------------
    // Constructor
    // ----------------------------------------------------------------
    constructor(uint256 _mintPrice) {
        owner = msg.sender;
        mintPrice = _mintPrice;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    // ----------------------------------------------------------------
    // ERC-721 view
    // ----------------------------------------------------------------
    function balanceOf(address addr) public view returns (uint256) {
        require(addr != address(0), "Zero address");
        return _balances[addr];
    }

    function ownerOf(uint256 tokenId) public view returns (address) {
        address addr = _owners[tokenId];
        require(addr != address(0), "Token does not exist");
        return addr;
    }

    // ----------------------------------------------------------------
    // Soulbound: block all transfers
    // ----------------------------------------------------------------
    function transferFrom(address, address, uint256) public pure {
        revert("Soulbound: non-transferable");
    }

    function safeTransferFrom(address, address, uint256) public pure {
        revert("Soulbound: non-transferable");
    }

    function safeTransferFrom(address, address, uint256, bytes calldata) public pure {
        revert("Soulbound: non-transferable");
    }

    function approve(address, uint256) public pure {
        revert("Soulbound: non-transferable");
    }

    function setApprovalForAll(address, bool) public pure {
        revert("Soulbound: non-transferable");
    }

    function getApproved(uint256) public pure returns (address) { return address(0); }
    function isApprovedForAll(address, address) public pure returns (bool) { return false; }

    // ----------------------------------------------------------------
    // Mint
    // ----------------------------------------------------------------
    function mint() external payable {
        require(msg.value >= mintPrice, "Insufficient payment");
        require(_balances[msg.sender] == 0, "Already has token");

        uint256 tokenId = _nextTokenId++;
        _owners[tokenId] = msg.sender;
        _balances[msg.sender] = 1;

        emit Transfer(address(0), msg.sender, tokenId);
        emit Minted(msg.sender, tokenId);

        if (msg.value > mintPrice) {
            payable(msg.sender).transfer(msg.value - mintPrice);
        }
    }

    // ----------------------------------------------------------------
    // Owner controls
    // ----------------------------------------------------------------
    function setMintPrice(uint256 _price) external onlyOwner {
        mintPrice = _price;
    }

    function withdraw() external onlyOwner {
        payable(owner).transfer(address(this).balance);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    // ----------------------------------------------------------------
    // View helpers
    // ----------------------------------------------------------------
    function hasToken(address addr) external view returns (bool) {
        return _balances[addr] > 0;
    }

    function totalMinted() external view returns (uint256) {
        return _nextTokenId;
    }
}
