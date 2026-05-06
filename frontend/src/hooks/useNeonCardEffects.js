import { useCallback } from 'react';

/**
 * Reusable handlers for neon card hover/click effects.
 */
export function useNeonCardEffects() {
  const handleCardMouseMove = useCallback((event) => {
    const card = event.currentTarget;
    const rect = card.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;

    card.style.setProperty('--pointer-x', `${x}%`);
    card.style.setProperty('--pointer-y', `${y}%`);
  }, []);

  const handleCardMouseLeave = useCallback((event) => {
    const card = event.currentTarget;
    card.style.removeProperty('--pointer-x');
    card.style.removeProperty('--pointer-y');
    card.classList.remove('card-tilt');
  }, []);

  const handleCardMouseEnter = useCallback((event) => {
    event.currentTarget.classList.add('card-tilt');
  }, []);

  const handleCardClick = useCallback((event) => {
    const card = event.currentTarget;
    const rect = card.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;

    card.style.setProperty('--click-x', `${x}%`);
    card.style.setProperty('--click-y', `${y}%`);
    card.classList.remove('card-pulse');
    void card.offsetWidth;
    card.classList.add('card-pulse');

    setTimeout(() => {
      card.classList.remove('card-pulse');
    }, 450);
  }, []);

  return {
    handleCardMouseMove,
    handleCardMouseLeave,
    handleCardMouseEnter,
    handleCardClick,
  };
}
