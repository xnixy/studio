import assert from "node:assert/strict";
import { keyboardOverlap } from "./keyboardOverlap";

assert.equal(keyboardOverlap({ screenY: 500, height: 336 }, 852), 352);
assert.equal(keyboardOverlap({ screenY: 852, height: 0 }, 852), 0);
assert.equal(keyboardOverlap({ screenY: 900, height: 300 }, 852), 300);
assert.equal(keyboardOverlap({ screenY: Number.NaN, height: 280 }, 800), 280);

console.log("keyboardOverlap ok");
