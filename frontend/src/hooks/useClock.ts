import { useCallback, useEffect, useState } from 'react';

/** 值班时钟：每 30 秒刷新，用于挂板顶部的当前时刻与"是否已过期望就绪时刻"。 */
export function useClock(intervalMs = 30000) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);

  const pad = useCallback((value: number) => String(value).padStart(2, '0'), []);
  return {
    now,
    clock: `${pad(now.getHours())}:${pad(now.getMinutes())}`,
    date: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
    seconds: `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`,
  };
}

/** 当前是否已过某个 HH:MM（用于看板提示"应到未到"）。 */
export function hasPassed(clock: string, now: Date): boolean {
  const [hour, minute] = clock.split(':').map((part) => Number(part));
  if (Number.isNaN(hour) || Number.isNaN(minute)) return false;
  return now.getHours() * 60 + now.getMinutes() >= hour * 60 + minute;
}
