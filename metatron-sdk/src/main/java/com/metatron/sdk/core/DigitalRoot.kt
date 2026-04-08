package com.metatron.sdk.core

import kotlin.math.abs

/**
 * ℤ₉ Charge-Neutral Consensus engine.
 */
object DigitalRoot {
    fun calculate(value: Int): Int {
        if (value == 0) return 0
        val v = abs(value)
        return 1 + (v - 1) % 9
    }

    fun isChargeNeutral(charges: List<Int>): Boolean {
        return calculate(charges.sum()) == 0
    }
}
