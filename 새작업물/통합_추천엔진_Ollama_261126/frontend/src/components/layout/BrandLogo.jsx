import { useId } from 'react';
import logo from '../../assets/brand/recomengine-logo.png';

export default function BrandLogo({
  collapsed = false
}) {
  const id = useId();

  return (
    <svg
      className="logo"
      viewBox={collapsed ? '195 285 895 480' : '75 282 1110 705'}
      role="img"
      aria-label="RecomEngine"
      overflow="hidden"
    >
      <defs>
        <filter
          id={id}
          filterUnits="userSpaceOnUse"
          x="0"
          y="0"
          width="1254"
          height="1254"
          colorInterpolationFilters="sRGB"
        >
          <feColorMatrix
            type="matrix"
            values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 -1 -1 -1 0 3"
          />
        </filter>
      </defs>
      <image
        href={logo}
        width="1254"
        height="1254"
        filter={`url(#${id})`}
      />
    </svg>
  );
}
