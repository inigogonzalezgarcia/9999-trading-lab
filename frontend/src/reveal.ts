import { useEffect } from 'react';

/** Reveal-on-scroll for sections marked with `data-reveal`: a short fade + 12 px rise the first time they enter the
 *  viewport. Content is visible by default; the hidden state is only applied by JS, and never under reduced motion. */
export function useReveal(): void {
  useEffect(() => {
    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const nodes = Array.from(document.querySelectorAll<HTMLElement>('[data-reveal]'));
    if (!nodes.length) return;
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) { entry.target.classList.add('in'); observer.unobserve(entry.target); }
      }
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    for (const node of nodes) {
      const rect = node.getBoundingClientRect();
      if (rect.top < window.innerHeight * 0.9) { node.classList.add('in'); continue; } // already on screen: no animation
      node.classList.add('reveal');
      observer.observe(node);
    }
    return () => observer.disconnect();
  }, []);
}
