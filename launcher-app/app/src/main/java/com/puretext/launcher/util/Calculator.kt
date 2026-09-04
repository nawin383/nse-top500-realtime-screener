package com.puretext.launcher.util

import kotlin.math.pow
import kotlin.math.sqrt

/**
 * A small hand-written recursive-descent evaluator -- no external math
 * library needed for +,-,*,/,%,^,sqrt(),parentheses. [evaluate] never
 * throws: any parse or math error (divide by zero, unbalanced parens,
 * garbage input) just returns null, which callers treat as "not a
 * calculator query."
 */
object Calculator {
    private val VALID_CHARS = "0123456789+-*/%^(). "

    /** True only for input that's plausibly a calculator expression (has an operator or sqrt), not e.g. a bare number or phone-number-shaped search. */
    fun looksLikeExpression(input: String): Boolean {
        val trimmed = input.trim()
        if (trimmed.isEmpty()) return false
        val withoutSqrt = trimmed.replace("sqrt", "")
        if (!withoutSqrt.all { it in VALID_CHARS }) return false
        return trimmed.any { it in "+-*/%^" } || trimmed.contains("sqrt")
    }

    fun evaluate(input: String): Double? = try {
        val parser = Parser(input.trim())
        val result = parser.parseExpression()
        parser.expectEnd()
        if (result.isFinite()) result else null
    } catch (e: Exception) {
        null
    }

    private class Parser(private val text: String) {
        private var pos = 0

        fun expectEnd() {
            skipSpaces()
            if (pos != text.length) throw IllegalArgumentException("Unexpected trailing input")
        }

        fun parseExpression(): Double {
            var value = parseTerm()
            while (true) {
                skipSpaces()
                when (peek()) {
                    '+' -> { pos++; value += parseTerm() }
                    '-' -> { pos++; value -= parseTerm() }
                    else -> return value
                }
            }
        }

        private fun parseTerm(): Double {
            var value = parsePower()
            while (true) {
                skipSpaces()
                when (peek()) {
                    '*' -> { pos++; value *= parsePower() }
                    '/' -> {
                        pos++
                        val divisor = parsePower()
                        if (divisor == 0.0) throw ArithmeticException("Division by zero")
                        value /= divisor
                    }
                    '%' -> { pos++; value %= parsePower() }
                    else -> return value
                }
            }
        }

        private fun parsePower(): Double {
            val base = parseUnary()
            skipSpaces()
            if (peek() == '^') {
                pos++
                return base.pow(parsePower())
            }
            return base
        }

        private fun parseUnary(): Double {
            skipSpaces()
            if (peek() == '-') {
                pos++
                return -parseUnary()
            }
            if (peek() == '+') {
                pos++
                return parseUnary()
            }
            return parsePrimary()
        }

        private fun parsePrimary(): Double {
            skipSpaces()
            if (text.startsWith("sqrt", pos)) {
                pos += 4
                skipSpaces()
                expect('(')
                val inner = parseExpression()
                skipSpaces()
                expect(')')
                if (inner < 0) throw ArithmeticException("Square root of negative number")
                return sqrt(inner)
            }
            if (peek() == '(') {
                pos++
                val value = parseExpression()
                skipSpaces()
                expect(')')
                return value
            }
            val start = pos
            while (pos < text.length && (text[pos].isDigit() || text[pos] == '.')) pos++
            if (pos == start) throw IllegalArgumentException("Expected a number at position $pos")
            return text.substring(start, pos).toDouble()
        }

        private fun peek(): Char? = if (pos < text.length) text[pos] else null

        private fun skipSpaces() {
            while (pos < text.length && text[pos].isWhitespace()) pos++
        }

        private fun expect(c: Char) {
            if (peek() != c) throw IllegalArgumentException("Expected '$c' at position $pos")
            pos++
        }
    }

    /** Trims trailing ".0" and excess decimals for a clean display string. */
    fun formatResult(value: Double): String {
        if (value == value.toLong().toDouble()) return value.toLong().toString()
        return "%.6f".format(value).trimEnd('0').trimEnd('.')
    }
}
