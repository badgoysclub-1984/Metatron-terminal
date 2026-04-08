package com.metatron.sdk.core

/**
 * Fibonacci Noise Canceller for Android sensor / task robustness.
 */
object FibonacciNoise {
    fun generateSequence(n: Int): List<Long> {
        val seq = mutableListOf(1L, 1L)
        while (seq.size < n) {
            seq.add(seq[seq.size - 1] + seq[seq.size - 2])
        }
        return seq.take(n)
    }

    fun applyNoise(tensorValue: Float, step: Int): Float {
        val seq = generateSequence(step + 1)
        val phi = 1.6180339887f // Golden ratio approx
        val noise = seq[step] % phi
        return tensorValue + (noise * Z9Constants.EPSILON.toFloat())
    }
}
