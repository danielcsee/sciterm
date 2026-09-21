/** A square with an arrow leaving its top-right corner: "go to this". */
export default function OutgoingArrowIcon() {
  return (
    <svg
      viewBox="0 0 16 16"
      width="13"
      height="13"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {/* Square, open at the top-right where the arrow leaves it. */}
      <path d="M9 3.5H4.5A1.5 1.5 0 0 0 3 5v6.5A1.5 1.5 0 0 0 4.5 13H11a1.5 1.5 0 0 0 1.5-1.5V7" />
      {/* Arrow, tip past the square's top-right corner. */}
      <path d="M7.6 8.4 14.5 1.5" />
      <path d="M10.4 1.5h4.1v4.1" />
    </svg>
  )
}
