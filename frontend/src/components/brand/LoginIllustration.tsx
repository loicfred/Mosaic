import type { ReactNode } from 'react'

/**
 * Original flat illustration for the sign-in screens: people building a
 * business's numbers - dashboards on stands, donut charts on masts, a bar
 * chart sculpture - in Valora's colours. Decorative (aria-hidden): it shows
 * shapes, not figures.
 */
const K = {
  l1: '#2F4677',
  l2: '#3F5A8F',
  l3: '#5B7FC7',
  l4: '#9AB8E6',
  pale: '#DCE8F7',
  dark: '#22345C',
  deep: '#14213D',
  bg: '#1B2A4E',
  white: '#FFFFFF',
  sage: '#7DB356',
  gold: '#F5B82E',
  coral: '#FF6B45',
  ink: '#2C2C2C',
}

type PersonProps = {
  x: number
  y: number
  shirt: string
  skin: string
  hair: string
  pants?: string
  /** Arm end points relative to the shoulders. */
  reachL?: [number, number]
  reachR?: [number, number]
  flip?: boolean
}

/** A simple standing figure; (x, y) is the point between the feet. */
function Person({ x, y, shirt, skin, hair, pants = K.deep, reachL = [-18, 40], reachR = [18, 40], flip }: PersonProps) {
  return (
    <g transform={`translate(${x} ${y}) scale(${flip ? -1 : 1} 1)`}>
      <rect x="-15" y="-62" width="12" height="62" rx="5" fill={pants} />
      <rect x="3" y="-62" width="12" height="62" rx="5" fill={pants} />
      <rect x="-20" y="-6" width="18" height="8" rx="4" fill={K.ink} />
      <rect x="2" y="-6" width="18" height="8" rx="4" fill={K.ink} />
      <rect x="-19" y="-128" width="38" height="74" rx="15" fill={shirt} />
      <path d={`M-13 -116 l${reachL[0]} ${reachL[1]}`} stroke={shirt} strokeWidth="11" strokeLinecap="round" />
      <circle cx={-13 + reachL[0]} cy={-116 + reachL[1]} r="5.5" fill={skin} />
      <path d={`M13 -116 l${reachR[0]} ${reachR[1]}`} stroke={shirt} strokeWidth="11" strokeLinecap="round" />
      <circle cx={13 + reachR[0]} cy={-116 + reachR[1]} r="5.5" fill={skin} />
      <rect x="-5" y="-138" width="10" height="14" rx="4" fill={skin} />
      <circle cx="0" cy="-150" r="15" fill={skin} />
      <path d="M-15 -150 C -16 -168, 2 -172, 12 -164 C 16 -160, 16 -154, 15 -150 C 8 -158, -6 -160, -15 -150 Z" fill={hair} />
    </g>
  )
}

/** A dashboard screen drawn as a tilted panel on a pole, with small charts inside. */
function Screen({ pts, pole, children }: { pts: [number, number][]; pole: [number, number, number]; children: ReactNode }) {
  const [px, top, bottom] = pole
  return (
    <g>
      <rect x={px - 5} y={top} width="10" height={bottom - top} fill={K.l2} />
      <rect x={px - 26} y={bottom - 6} width="52" height="8" rx="4" fill={K.l2} />
      <polygon points={pts.map((p) => p.join(',')).join(' ')} fill={K.l3} />
      {children}
    </g>
  )
}

export function LoginIllustration({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 980 540" className={className} preserveAspectRatio="xMaxYMax meet" aria-hidden fill="none">
      {/* sky: a trend line drawn across it, and clouds */}
      <path
        d="M34 330 C 50 170, 110 70, 170 92 C 230 114, 196 214, 262 204 C 320 196, 318 96, 382 70"
        stroke={K.l3}
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <circle cx="170" cy="92" r="6" fill={K.white} />
      <circle cx="262" cy="204" r="6" fill={K.gold} />
      <circle cx="382" cy="70" r="6" fill={K.white} />
      <rect x="420" y="40" width="130" height="32" rx="16" fill={K.l1} />
      <rect x="452" y="22" width="70" height="32" rx="16" fill={K.l1} />
      <rect x="770" y="70" width="120" height="28" rx="14" fill={K.l1} />
      <rect x="800" y="54" width="60" height="28" rx="14" fill={K.l1} />

      {/* ground shadows */}
      <ellipse cx="200" cy="528" rx="190" ry="12" fill={K.dark} />
      <ellipse cx="560" cy="528" rx="110" ry="12" fill={K.dark} />
      <ellipse cx="820" cy="528" rx="150" ry="12" fill={K.dark} />

      {/* LEFT: two dashboard screens on stands */}
      <Screen
        pts={[
          [196, 170],
          [372, 138],
          [400, 280],
          [224, 312],
        ]}
        pole={[300, 290, 522]}
      >
        <polygon points="210,182 282,169 294,232 222,245" fill={K.pale} />
        <path d="M226 230 L244 214 L258 222 L280 196" stroke={K.coral} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <polygon points="292,165 364,152 376,215 304,228" fill={K.pale} />
        <polygon points="312,220 322,218 318,196 308,198" fill={K.sage} />
        <polygon points="328,217 338,215 332,184 322,186" fill={K.gold} />
        <polygon points="344,214 354,212 346,172 336,174" fill={K.l2} />
        <polygon points="226,256 298,243 308,292 236,305" fill={K.pale} />
        <circle cx="266" cy="274" r="16" fill={K.gold} />
        <path d="M266 274 L266 258 A16 16 0 0 1 282 276 Z" fill={K.coral} />
        <polygon points="308,240 380,227 390,276 318,289" fill={K.pale} />
        <path d="M324 262 L372 253 M326 276 L364 269" stroke={K.l3} strokeWidth="5" strokeLinecap="round" />
      </Screen>
      <Screen
        pts={[
          [70, 300],
          [226, 276],
          [248, 396],
          [92, 420],
        ]}
        pole={[160, 405, 522]}
      >
        <polygon points="84,312 150,302 160,356 94,366" fill={K.pale} />
        <polygon points="102,360 111,359 108,344 99,345" fill={K.sage} />
        <polygon points="116,358 125,357 120,334 111,335" fill={K.coral} />
        <polygon points="130,356 139,355 132,324 123,325" fill={K.gold} />
        <polygon points="160,300 214,292 224,346 170,354" fill={K.pale} />
        <path d="M176 336 L190 322 L204 330 L216 312" stroke={K.l1} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <polygon points="96,374 226,354 234,396 104,416" fill={K.pale} />
        <path d="M116 398 L190 387" stroke={K.sage} strokeWidth="6" strokeLinecap="round" />
      </Screen>
      {/* person holding the front screen */}
      <Person x={52} y={522} shirt={K.coral} skin="#8D5A3B" hair={K.ink} reachL={[10, 34]} reachR={[34, -30]} />

      {/* ladder and a person placing a chart on the top screen */}
      <path d="M396 520 L360 300 M428 520 L392 300" stroke={K.l4} strokeWidth="6" strokeLinecap="round" />
      {[330, 362, 394, 426, 458, 490].map((y) => {
        const t = (520 - y) / 220
        return <path key={y} d={`M${396 - 36 * t} ${y} H${428 - 36 * t}`} stroke={K.l4} strokeWidth="5" strokeLinecap="round" />
      })}
      <Person x={392} y={430} shirt={K.gold} skin="#C98E6A" hair="#5A3A28" reachL={[-30, -44]} reachR={[-6, 30]} />
      <g transform="rotate(-10 353 247)">
        <rect x="338" y="236" width="30" height="22" rx="4" fill={K.white} />
        <path d="M344 252 L352 244 L358 248 L364 240" stroke={K.sage} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </g>

      {/* CENTRE: donut charts on masts, standing in for the turbines */}
      <path d="M488 522 L494 250 H502 L508 522 Z" fill={K.l3} />
      <g transform="translate(470 250)">
        <circle r="50" fill={K.l2} />
        <path d="M0 -50 A50 50 0 0 1 47.5 15.5 L28.5 9.3 A30 30 0 0 0 0 -30 Z" fill={K.l4} />
        <circle r="30" fill={K.bg} />
      </g>
      <path d="M576 522 L584 196 H594 L602 522 Z" fill={K.pale} />
      <g transform="translate(589 180)">
        <circle r="92" fill={K.white} />
        <path d="M0 -92 A92 92 0 0 1 87.5 28.4 L0 0 Z" fill={K.coral} />
        <path d="M87.5 28.4 A92 92 0 0 1 -30 87 L0 0 Z" fill={K.gold} />
        <path d="M-30 87 A92 92 0 0 1 -80 -45 L0 0 Z" fill={K.sage} />
        <path d="M-80 -45 A92 92 0 0 1 0 -92 L0 0 Z" fill={K.l2} />
        <circle r="50" fill={K.bg} />
        <circle r="18" fill={K.pale} />
      </g>

      {/* RIGHT: a bar chart sculpture and a person reviewing it on a tablet */}
      <rect x="690" y="430" width="36" height="92" rx="6" fill={K.sage} />
      <rect x="738" y="376" width="36" height="146" rx="6" fill={K.gold} />
      <rect x="786" y="318" width="36" height="204" rx="6" fill={K.l3} />
      <rect x="834" y="254" width="36" height="268" rx="6" fill={K.coral} />
      <path d="M700 400 L756 348 L804 290 L850 224" stroke={K.white} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M836 222 L852 222 L852 238" stroke={K.white} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      <Person x={930} y={522} shirt={K.l4} skin="#E2B08C" hair={K.ink} pants={K.ink} flip reachL={[26, 22]} reachR={[30, 18]} />
      <g transform="rotate(-8 890 408)">
        <rect x="868" y="386" width="44" height="32" rx="5" fill={K.white} />
        <rect x="875" y="404" width="6" height="9" rx="1.5" fill={K.sage} />
        <rect x="885" y="398" width="6" height="15" rx="1.5" fill={K.gold} />
        <rect x="895" y="392" width="6" height="21" rx="1.5" fill={K.coral} />
      </g>
    </svg>
  )
}
