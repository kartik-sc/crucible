/**
 * Shared motion vocabulary. One easing/spring set so the arena breathes as one
 * thing. Weighted Jakub (production polish) — springs with bounce 0, enter =
 * opacity + translateY + blur, exits subtler than enters. Reduced motion is
 * handled globally by <MotionConfig reducedMotion="user"> at the app root, which
 * collapses transform/layout animation to opacity for users who ask for it.
 */

import type { Transition } from "framer-motion";

export const EASE_OUT: [number, number, number, number] = [0.16, 1, 0.3, 1];
export const EASE_IN: [number, number, number, number] = [0.4, 0, 1, 1];

/** Smooth professional settle — entrances, patches. */
export const SPRING_SETTLE: Transition = { type: "spring", duration: 0.45, bounce: 0 };
/** A verdict stamp hitting paper — one small bit of life, nothing bouncy. */
export const SPRING_PRESS: Transition = { type: "spring", duration: 0.4, bounce: 0.18 };

/** Row / content entrance: materialize into focus (Jakub). */
export const ENTER = {
  initial: { opacity: 0, y: 8, filter: "blur(4px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
};

/** Subtler exit than enter — attention is already moving on. */
export const EXIT = { opacity: 0, y: -10, filter: "blur(4px)" };
