/** Boston-themed status icons for Chahlie UI states */

type IconProps = { className?: string; size?: number };

export function GreenMonsterIcon({ className = "", size = 20 }: IconProps) {
  return (
    <svg
      className={`boston-icon ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden
    >
      <rect x="2" y="4" width="20" height="16" rx="2" fill="#007A33" />
      <rect x="2" y="4" width="20" height="3" fill="#008348" />
      <circle cx="8" cy="12" r="2.5" fill="#FFB81C" />
      <circle cx="16" cy="12" r="2.5" fill="#FFB81C" />
      <path d="M10 16 Q12 18 14 16" stroke="#0C2340" strokeWidth="1.5" fill="none" />
    </svg>
  );
}

export function MassAveSignIcon({ className = "", size = 20 }: IconProps) {
  return (
    <svg
      className={`boston-icon ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden
    >
      <polygon points="12,2 22,12 12,22 2,12" fill="#FFB81C" stroke="#0C2340" strokeWidth="1.5" />
      <text
        x="12"
        y="11"
        textAnchor="middle"
        fontSize="4.5"
        fontWeight="700"
        fill="#0C2340"
        fontFamily="Oswald, sans-serif"
      >
        MASS
      </text>
      <text
        x="12"
        y="15.5"
        textAnchor="middle"
        fontSize="4.5"
        fontWeight="700"
        fill="#0C2340"
        fontFamily="Oswald, sans-serif"
      >
        AVE
      </text>
    </svg>
  );
}

export function BeerMugIcon({ className = "", size = 20 }: IconProps) {
  return (
    <svg
      className={`boston-icon beer-mug ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden
    >
      <rect x="6" y="8" width="10" height="12" rx="1" fill="#FFB81C" opacity="0.9" />
      <rect x="7" y="9" width="8" height="8" rx="0.5" fill="#C49200" />
      <path d="M16 10 L19 9 L19 16 L16 15 Z" fill="#9CA3AF" />
      <ellipse cx="11" cy="8" rx="5" ry="1.5" fill="#FAFAFA" opacity="0.5" />
    </svg>
  );
}

export function ThinkingCapIcon({ className = "", size = 20 }: IconProps) {
  return (
    <svg
      className={`boston-icon thinking-cap ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden
    >
      <path d="M4 14 L12 8 L20 14 L20 17 L4 17 Z" fill="#0C2340" stroke="#007A33" strokeWidth="1" />
      <rect x="3" y="16" width="18" height="3" rx="1" fill="#007A33" />
      <circle cx="20" cy="11" r="2" fill="#FFB81C" />
      <path d="M20 9 L20 7 M19 8 L21 8" stroke="#FFB81C" strokeWidth="0.8" />
      <text x="12" y="14.5" textAnchor="middle" fontSize="3" fill="#FFB81C" fontWeight="700">
        ★
      </text>
    </svg>
  );
}

export function ChahlieLogoMark({ className = "", size = 48 }: IconProps) {
  return (
    <svg
      className={`chahlie-logo ${className}`}
      width={size}
      height={size}
      viewBox="0 0 64 64"
      aria-label="Chahlie"
    >
      <circle cx="32" cy="32" r="30" fill="#0C2340" stroke="#007A33" strokeWidth="3" />
      <path
        d="M32 10 C32 10 18 18 18 32 C18 42 24 48 32 50 C40 48 46 42 46 32 C46 18 32 10 32 10"
        fill="none"
        stroke="#BD3039"
        strokeWidth="2"
        strokeDasharray="4 3"
      />
      <text
        x="32"
        y="38"
        textAnchor="middle"
        fontSize="22"
        fontWeight="700"
        fill="#FFB81C"
        fontFamily="Oswald, sans-serif"
      >
        C
      </text>
    </svg>
  );
}
