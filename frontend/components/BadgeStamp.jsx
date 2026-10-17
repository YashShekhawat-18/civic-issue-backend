import { IconAward } from "./icons";

// A round "stamp" for a badge. Locked badges are drawn faded.
export default function BadgeStamp({ badge, earned = true }) {
  const showIcon = badge.icon && [...badge.icon].length <= 3; // emoji, not a long icon name
  return (
    <div className={`flex w-24 flex-col items-center text-center ${earned ? "" : "opacity-45"}`}>
      <span
        className={`flex h-16 w-16 items-center justify-center rounded-full border-4 text-2xl ${
          earned ? "border-signal bg-signal-tint text-asphalt" : "border-line bg-white text-asphalt-soft"
        }`}
      >
        {showIcon ? badge.icon : <IconAward size={26} />}
      </span>
      <span className="mt-1.5 text-xs font-bold leading-tight">{badge.name}</span>
      <span className="text-[11px] text-asphalt-soft">{earned ? "Earned" : `${badge.pointsRequired} points`}</span>
    </div>
  );
}
