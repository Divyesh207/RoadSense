"use client";

import React from "react";
import Link from "next/link";
import { AnimatedHeading } from "@/components/landing/animated-heading";
import { FadeIn } from "@/components/landing/fade-in";
import { Magnetic } from "@/components/landing/cursor-effects";
import { RoadScene } from "@/components/landing/road-scene";

const focusRing = "focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-black";

/**
 * Landing hero: a full-viewport 3D road scene (see RoadScene) with the heading, actions and a
 * glass tag resting at the bottom of the viewport. The navigation bar (LandingNav) floats above
 * it. Only the buttons and the tag take pointer events, so the scene behind stays clickable.
 */
export function Hero() {
  return (
    <section className="relative h-[100svh] min-h-[560px] flex flex-col overflow-hidden bg-[#6f7f8e] text-white">
      <RoadScene />

      {/* Space taken by the fixed navigation bar */}
      <div aria-hidden className="pt-6 h-[72px] shrink-0" />

      <div className="pointer-events-none relative z-10 px-6 md:px-12 lg:px-16 flex-1 flex flex-col justify-end pb-12 lg:pb-16">
        <div className="lg:grid lg:grid-cols-2 lg:items-end">
          <div data-scene-avoid className="w-fit max-w-full">
            <AnimatedHeading
              text={"Know every road.\nRepair what matters."}
              className="text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-normal mb-4"
              style={{ letterSpacing: "-0.04em", textShadow: "0 2px 4px rgba(0,0,0,.55), 0 6px 34px rgba(0,0,0,.6)" }}
            />
            <FadeIn delay={800} duration={1000}>
              <p className="text-base md:text-lg text-gray-100 mb-5 [text-shadow:0_1px_3px_rgba(0,0,0,.75),0_2px_16px_rgba(0,0,0,.7)]">
                Field inspections, AI-assisted damage detection, mapping and verified repairs in one platform.
              </p>
            </FadeIn>
            <FadeIn delay={1200} duration={1000}>
              <div className="pointer-events-auto flex w-fit flex-wrap gap-4">
                <Magnetic>
                  <Link
                    href="/login"
                    className={`bg-white text-black px-8 py-3 rounded-lg font-medium transition-colors hover:bg-gray-100 ${focusRing}`}
                  >
                    Login
                  </Link>
                </Magnetic>
                <Magnetic>
                  <a
                    href="#request-demo"
                    className={`liquid-glass border border-white/20 text-white px-8 py-3 rounded-lg font-medium transition-colors hover:bg-white hover:text-black ${focusRing}`}
                  >
                    Request Demo
                  </a>
                </Magnetic>
              </div>
            </FadeIn>
          </div>

          <div className="flex items-end justify-start lg:justify-end mt-8 lg:mt-0">
            <FadeIn delay={1400} duration={1000}>
              <div data-parallax="6" data-scene-avoid className="pointer-events-auto liquid-glass border border-white/20 px-6 py-3 rounded-xl">
                <p className="text-lg md:text-xl lg:text-2xl font-light">Inspect. Detect. Repair.</p>
              </div>
            </FadeIn>
          </div>
        </div>
      </div>
    </section>
  );
}
