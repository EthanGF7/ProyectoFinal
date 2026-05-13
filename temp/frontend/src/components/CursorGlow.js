import { useEffect, useRef } from 'react';

export default function CursorGlow() {
  const glowRef = useRef(null);
  const rafRef = useRef(null);

  useEffect(() => {
    const glow = glowRef.current;
    if (!glow || typeof window === 'undefined') {
      return undefined;
    }

    const handlePointerMove = (event) => {
      if (event.pointerType === 'touch') {
        glow.style.opacity = '0';
        return;
      }

      const { clientX, clientY } = event;

      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }

      rafRef.current = requestAnimationFrame(() => {
        glow.style.opacity = '0.35';
        glow.style.transform = `translate3d(${clientX}px, ${clientY}px, 0)`;
      });
    };

    const handlePointerLeave = () => {
      glow.style.opacity = '0';
    };

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerdown', handlePointerMove);
    window.addEventListener('pointerleave', handlePointerLeave);

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerdown', handlePointerMove);
      window.removeEventListener('pointerleave', handlePointerLeave);
    };
  }, []);

  return <div ref={glowRef} className="cursor-glow" aria-hidden="true" />;
}
