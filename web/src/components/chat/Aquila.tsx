interface AquilaProps {
  className?: string;
}

/** 双头鹰简化剪影（自绘，非 GW 资产；上线前按红线再抽象一版） */
export function Aquila({ className = "" }: AquilaProps) {
  return (
    <svg
      className={className}
      width="86"
      height="40"
      viewBox="0 0 172 80"
      aria-hidden="true"
    >
      <g fill="#c7ccc2">
        <path d="M86 34 L78 26 L70 30 L62 22 L54 27 L46 18 L38 24 L28 14 L22 21 L10 10 L16 26 L6 24 L18 38 L8 40 L22 48 L14 54 L30 56 L24 64 L40 60 L38 70 L52 62 L54 72 L64 60 L70 68 L76 54 L86 62 Z" />
        <path d="M86 34 L94 26 L102 30 L110 22 L118 27 L126 18 L134 24 L144 14 L150 21 L162 10 L156 26 L166 24 L154 38 L164 40 L150 48 L158 54 L142 56 L148 64 L132 60 L134 70 L120 62 L118 72 L108 60 L102 68 L96 54 L86 62 Z" />
        <circle cx="79" cy="20" r="6" />
        <circle cx="93" cy="20" r="6" />
        <path d="M74 16 L66 12 L76 24 Z" />
        <path d="M98 16 L106 12 L96 24 Z" />
        <path d="M80 28 L92 28 L90 52 L86 58 L82 52 Z" fill="#a31317" />
      </g>
    </svg>
  );
}
