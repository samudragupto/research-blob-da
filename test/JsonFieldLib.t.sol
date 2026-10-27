// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {JsonFieldLib} from "../contracts/libraries/JsonFieldLib.sol";
import {Test} from "forge-std/Test.sol";

contract JsonFieldLibTest is Test {
    function test_isValidKey() public pure {
        assertTrue(JsonFieldLib.isValidKey("loss"));
        assertTrue(JsonFieldLib.isValidKey("epoch_01"));
        assertTrue(JsonFieldLib.isValidKey("val.metric-score"));
        assertTrue(JsonFieldLib.isValidKey("X"));

        // Invalid keys
        assertFalse(JsonFieldLib.isValidKey("")); // empty
        assertFalse(JsonFieldLib.isValidKey('key"with_quote')); // quote
        assertFalse(JsonFieldLib.isValidKey("key:with_colon")); // colon
        assertFalse(JsonFieldLib.isValidKey("key with space")); // space
        assertFalse(JsonFieldLib.isValidKey("{brace}")); // brace
    }

    function readFixedExternal(bytes calldata json, bytes memory key, uint8 decimals)
        external
        pure
        returns (bool ok, int256 value)
    {
        return JsonFieldLib.readFixed(json, key, decimals);
    }

    function test_readFixed_integers() public view {
        bytes memory json = '{"step":42,"epoch":3}';
        (bool ok1, int256 v1) = this.readFixedExternal(json, "step", 0);
        assertTrue(ok1);
        assertEq(v1, 42);

        (bool ok2, int256 v2) = this.readFixedExternal(json, "epoch", 2);
        assertTrue(ok2);
        assertEq(v2, 300); // 3 scaled by 10^2
    }

    function test_readFixed_decimals() public view {
        bytes memory json = '{"loss":0.0452,"acc":98.5}';
        (bool ok1, int256 v1) = this.readFixedExternal(json, "loss", 4);
        assertTrue(ok1);
        assertEq(v1, 452); // 0.0452 * 10^4

        (bool ok2, int256 v2) = this.readFixedExternal(json, "acc", 2);
        assertTrue(ok2);
        assertEq(v2, 9850); // 98.5 * 10^2
    }

    function test_readFixed_negative() public view {
        bytes memory json = '{"temp_c":-14.75,"delta":-2}';
        (bool ok1, int256 v1) = this.readFixedExternal(json, "temp_c", 2);
        assertTrue(ok1);
        assertEq(v1, -1475);

        (bool ok2, int256 v2) = this.readFixedExternal(json, "delta", 0);
        assertTrue(ok2);
        assertEq(v2, -2);
    }

    function test_readFixed_ignores_nested_with_same_name() public view {
        // "val" inside nested object is 99, but top-level "val" is 42
        bytes memory json = '{"sub":{"val":99},"val":42}';
        (bool ok, int256 v) = this.readFixedExternal(json, "val", 0);
        assertTrue(ok);
        assertEq(v, 42);

        // When top-level key comes before nested
        bytes memory json2 = '{"val":55,"sub":{"val":99}}';
        (bool ok2, int256 v2) = this.readFixedExternal(json2, "val", 0);
        assertTrue(ok2);
        assertEq(v2, 55);
    }

    function test_readFixed_ignores_key_inside_string_value() public view {
        bytes memory json = '{"description":"loss: 0.01 is good","loss":0.04}';
        (bool ok, int256 v) = this.readFixedExternal(json, "loss", 2);
        assertTrue(ok);
        assertEq(v, 4); // 0.04 * 10^2
    }

    function test_readFixed_escaped_quote_in_string() public view {
        bytes memory json = '{"desc":"he said \\"loss\\":99","loss":1.5}';
        (bool ok, int256 v) = this.readFixedExternal(json, "loss", 1);
        assertTrue(ok);
        assertEq(v, 15);
    }

    function test_readFixed_rejects_duplicate_top_level_keys() public view {
        // Ambiguous duplicate keys must return false
        bytes memory json = '{"metric":10,"metric":20}';
        (bool ok,) = this.readFixedExternal(json, "metric", 0);
        assertFalse(ok);
    }

    function test_readFixed_missing_key() public view {
        bytes memory json = '{"foo":1,"bar":2}';
        (bool ok,) = this.readFixedExternal(json, "baz", 0);
        assertFalse(ok);
    }

    function test_readFixed_scientific_notation_rejected() public view {
        // Scientific notation like 1e-4 is rejected by design because canonical JSON uses fixed decimals
        bytes memory json = '{"loss":1e-4}';
        (bool ok,) = this.readFixedExternal(json, "loss", 4);
        assertFalse(ok);
    }

    function test_fuzz_readFixed_integers(int64 rawVal) public view {
        // Format integer as string
        string memory s = _int64ToString(rawVal);
        bytes memory json = abi.encodePacked('{"id":1,"target":', s, ',"flag":true}');
        (bool ok, int256 v) = this.readFixedExternal(json, "target", 0);
        assertTrue(ok);
        assertEq(v, int256(rawVal));
    }

    function _int64ToString(int64 v) private pure returns (string memory) {
        if (v == 0) return "0";
        bool neg = v < 0;
        uint64 u = neg ? (v == type(int64).min ? uint64(type(int64).max) + 1 : uint64(-v)) : uint64(v);
        uint256 len;
        uint64 temp = u;
        while (temp != 0) {
            len++;
            temp /= 10;
        }
        if (neg) len++;
        bytes memory b = new bytes(len);
        uint256 idx = len;
        while (u != 0) {
            idx--;
            b[idx] = bytes1(uint8(48 + (u % 10)));
            u /= 10;
        }
        if (neg) {
            b[0] = "-";
        }
        return string(b);
    }
}
