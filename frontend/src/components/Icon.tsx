import type { CSSProperties } from 'react';

type IconName = 'orbit' | 'search' | 'arrow-up' | 'arrow-down' | 'arrow-right' | 'news' | 'signal' | 'layers' | 'chevron' | 'clock';

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
  style?: CSSProperties;
}

export default function Icon({ name, size = 18, className, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={className} style={style}>
      {name === 'orbit' && <><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(-38 12 12)" /><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(38 12 12)" /><circle cx="12" cy="12" r="2" fill="currentColor" stroke="none" /></>}
      {name === 'search' && <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4.5 4.5" /></>}
      {name === 'arrow-up' && <path d="M12 19V5m-5 5 5-5 5 5" />}
      {name === 'arrow-down' && <path d="M12 5v14m-5-5 5 5 5-5" />}
      {name === 'arrow-right' && <path d="M5 12h14m-5-5 5 5-5 5" />}
      {name === 'news' && <><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M8 8h8M8 12h8M8 16h4" /></>}
      {name === 'signal' && <><path d="M8.5 8.5a5 5 0 0 0 0 7m7-7a5 5 0 0 1 0 7M5 5a10 10 0 0 0 0 14M19 5a10 10 0 0 1 0 14" /><circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none" /></>}
      {name === 'layers' && <><path d="m12 3 10 5-10 5L2 8l10-5Zm-9 9 9 5 9-5M3 16l9 5 9-5" /></>}
      {name === 'chevron' && <path d="m9 5 7 7-7 7" />}
      {name === 'clock' && <><circle cx="12" cy="12" r="8" /><path d="M12 7v5l3 2" /></>}
    </svg>
  );
}
