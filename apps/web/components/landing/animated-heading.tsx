"use client";

import React, { useEffect, useState } from "react";

/**
 * Heading that enters one character at a time. `text` is split into lines at "\n" and each
 * line into characters; every character slides in from the left and fades in, with a delay of
 * (lineIndex * lineLength * charDelay) + (charIndex * charDelay).
 *
 * Characters of one word are kept together so a narrow screen wraps between words, never inside
 * one. Screen readers get the plain text from `aria-label`. With reduced motion the heading is
 * simply shown.
 */
export function AnimatedHeading({
  text,
  className = "",
  style,
  initialDelay = 200,
  charDelay = 30,
  duration = 500,
}: {
  text: string;
  className?: string;
  style?: React.CSSProperties;
  initialDelay?: number;
  charDelay?: number;
  duration?: number;
}) {
  const [shown, setShown] = useState(false);
  const [instant, setInstant] = useState(false);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setInstant(true);
      setShown(true);
      return;
    }
    const timer = window.setTimeout(() => setShown(true), initialDelay);
    return () => window.clearTimeout(timer);
  }, [initialDelay]);

  const lines = text.split("\n");

  const char = (c: string, key: string, delay: number) => (
    <span
      key={key}
      className="inline-block"
      style={{
        opacity: shown ? 1 : 0,
        transform: shown ? "translateX(0)" : "translateX(-18px)",
        transitionProperty: "opacity, transform",
        transitionDuration: instant ? "0ms" : `${duration}ms`,
        transitionDelay: instant ? "0ms" : `${delay}ms`,
      }}
    >
      {c === " " ? " " : c}
    </span>
  );

  return (
    <h1 className={className} style={style} aria-label={text.replace(/\n/g, " ")}>
      {lines.map((line, lineIndex) => {
        const lineDelay = lineIndex * line.length * charDelay;
        // Words (with the space that follows them) are the unbreakable units.
        const words = line.match(/\S+\s*/g) ?? [];
        let charIndex = 0;
        return (
          <span key={lineIndex} aria-hidden className="block">
            {words.map((word, wordIndex) => (
              <span key={wordIndex} className="inline-block whitespace-nowrap">
                {word.split("").map((c) => {
                  const i = charIndex++;
                  return char(c, `${lineIndex}-${i}`, lineDelay + i * charDelay);
                })}
              </span>
            ))}
          </span>
        );
      })}
    </h1>
  );
}
