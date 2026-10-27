// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title JsonFieldLib
/// @author research-blob-da
/// @notice Minimal, allocation-free extractor for a numeric top-level field of a canonical JSON record.
/// @dev Research rationale. Optimistic property claims ("every value of column `temperature_c` lies in
///      [min, max]") are only meaningful if a challenger can show, *on-chain*, that a committed record
///      violates the claim. That requires reading the value out of the committed record bytes. Records produced
///      by `python/canonical.py` are canonical JSON objects (sorted keys, no whitespace, fixed-point decimals,
///      no exponents), so a single linear scan suffices. The scanner:
///
///      - tracks nesting depth and string state (including backslash escapes) so that a key match is only
///        accepted for keys of the top-level object, never inside strings or nested objects;
///      - treats duplicate top-level keys as malformed, because different JSON parsers disagree on which
///        duplicate wins and a publisher could otherwise hide a violating value behind a benign first copy;
///      - parses `-?digits(.digits)?` into a fixed-point integer with `decimals` fractional digits and rejects
///        exponents, excess precision, and any terminator other than `,` or `}`.
///
///      Returning `ok = false` for missing or malformed fields is deliberate: the registry treats such records
///      as violations of a range claim, which prevents a publisher from evading a refutation by omitting the
///      field in offending rows.
library JsonFieldLib {
    uint8 private constant QUOTE = 0x22; // "
    uint8 private constant BACKSLASH = 0x5c; // \
    uint8 private constant LBRACE = 0x7b; // {
    uint8 private constant RBRACE = 0x7d; // }
    uint8 private constant LBRACKET = 0x5b; // [
    uint8 private constant RBRACKET = 0x5d; // ]
    uint8 private constant COMMA = 0x2c; // ,
    uint8 private constant COLON = 0x3a; // :
    uint8 private constant MINUS = 0x2d; // -
    uint8 private constant DOT = 0x2e; // .
    uint8 private constant ZERO = 0x30; // 0
    uint8 private constant NINE = 0x39; // 9

    /// @notice Maximum number of supported fractional digits.
    uint8 internal constant MAX_DECIMALS = 18;
    /// @dev Maximum number of integer digits; with 18 decimals the value stays far below 2**255.
    uint256 private constant MAX_INT_DIGITS = 40;

    /// @notice Returns true if `key` only contains `[A-Za-z0-9_.-]` and is between 1 and 64 bytes long.
    /// @dev Restricting the alphabet removes every character that would need escaping in JSON, so a byte-wise
    ///      comparison against the raw record is equivalent to a semantic key comparison.
    /// @param key Candidate key.
    /// @return True if the key is acceptable.
    function isValidKey(bytes memory key) internal pure returns (bool) {
        uint256 len = key.length;
        if (len == 0 || len > 64) return false;
        for (uint256 i; i < len;) {
            uint8 c = uint8(key[i]);
            bool ok = (c >= 0x30 && c <= 0x39) || (c >= 0x41 && c <= 0x5a) || (c >= 0x61 && c <= 0x7a)
                || c == 0x5f || c == DOT || c == MINUS;
            if (!ok) return false;
            unchecked {
                ++i;
            }
        }
        return true;
    }

    /// @notice Reads the top-level numeric field `key` from a canonical JSON object.
    /// @param json Record bytes.
    /// @param key Field name (see {isValidKey}).
    /// @param decimals Fixed-point scale of the returned value.
    /// @return ok True if the field occurs exactly once at top level and is a well-formed number.
    /// @return value The value scaled by `10**decimals`.
    function readFixed(bytes calldata json, bytes memory key, uint8 decimals)
        internal
        pure
        returns (bool ok, int256 value)
    {
        if (decimals > MAX_DECIMALS) return (false, 0);
        uint256 len = json.length;
        uint256 klen = key.length;
        bytes32 keyHash = keccak256(key);
        uint256 depth;
        bool inStr;
        bool esc;
        bool found;
        for (uint256 i; i < len;) {
            uint8 c = uint8(json[i]);
            if (inStr) {
                if (esc) esc = false;
                else if (c == BACKSLASH) esc = true;
                else if (c == QUOTE) inStr = false;
            } else if (c == QUOTE) {
                bool isTopKey =
                    depth == 1 && i > 0 && (uint8(json[i - 1]) == LBRACE || uint8(json[i - 1]) == COMMA);
                uint256 end = i + 1 + klen;
                if (
                    isTopKey && end + 1 < len && uint8(json[end]) == QUOTE && uint8(json[end + 1]) == COLON
                        && keccak256(json[i + 1:end]) == keyHash
                ) {
                    if (found) return (false, 0);
                    (bool numOk, int256 v, uint256 next) = _parseNumber(json, end + 2, decimals);
                    if (!numOk) return (false, 0);
                    found = true;
                    value = v;
                    // `next` points at the terminator; resume scanning there so it is processed normally.
                    i = next;
                    continue;
                }
                inStr = true;
            } else if (c == LBRACE || c == LBRACKET) {
                unchecked {
                    ++depth;
                }
            } else if (c == RBRACE || c == RBRACKET) {
                if (depth == 0) return (false, 0);
                unchecked {
                    --depth;
                }
            }
            unchecked {
                ++i;
            }
        }
        return (found, found ? value : int256(0));
    }

    /// @dev Parses `-?[0-9]+(\.[0-9]+)?` starting at `p` and checks the terminator.
    /// @return ok Whether parsing succeeded.
    /// @return v Parsed fixed-point value.
    /// @return next Index of the terminator character.
    function _parseNumber(bytes calldata s, uint256 p, uint8 decimals)
        private
        pure
        returns (bool ok, int256 v, uint256 next)
    {
        uint256 len = s.length;
        bool neg;
        if (p < len && uint8(s[p]) == MINUS) {
            neg = true;
            unchecked {
                ++p;
            }
        }
        uint256 acc;
        uint256 intDigits;
        while (p < len) {
            uint8 c = uint8(s[p]);
            if (c < ZERO || c > NINE) break;
            acc = acc * 10 + (c - ZERO);
            unchecked {
                ++intDigits;
                ++p;
            }
            if (intDigits > MAX_INT_DIGITS) return (false, 0, p);
        }
        if (intDigits == 0) return (false, 0, p);
        uint256 fracDigits;
        if (p < len && uint8(s[p]) == DOT) {
            unchecked {
                ++p;
            }
            while (p < len) {
                uint8 c = uint8(s[p]);
                if (c < ZERO || c > NINE) break;
                if (fracDigits == decimals) return (false, 0, p);
                acc = acc * 10 + (c - ZERO);
                unchecked {
                    ++fracDigits;
                    ++p;
                }
            }
            if (fracDigits == 0) return (false, 0, p);
        }
        if (p >= len) return (false, 0, p);
        uint8 term = uint8(s[p]);
        if (term != COMMA && term != RBRACE) return (false, 0, p);
        acc *= 10 ** (decimals - fracDigits);
        if (acc > uint256(type(int256).max)) return (false, 0, p);
        v = neg ? -int256(acc) : int256(acc);
        return (true, v, p);
    }
}
