import React from 'react'
import { useLocation } from 'react-router-dom'
import { useChatStore } from '../../store'
import Badge from '../common/Badge'
import Button from '../common/Button'
import NavTabs from './NavTabs'
import styles from './Header.module.css'

// C-shaped tech gear icon — matches the project logo
const TechGearIcon = () => (
  <svg viewBox="0 0 100 100" width="28" height="28" aria-hidden="true" className={styles.logoIcon}>
    {/* C-shaped gear: partial annulus (300°) with 9 teeth on the outer edge */}
    {/* Gap opens to the right (~60°) mimicking the classic C-gear logo */}
    <path
      fill="#e04f35"
      d="
        M50 8
        a42 42 0 1 1 -29.7 71.7
        l5.6-5.6
        a34 34 0 1 0 24.1-58.1
        Z

        M50 16
        a34 34 0 1 1 -24.1 58.1
        l-5.6 5.6
        A42 42 0 1 0 50 8
        Z
      "
      fillRule="evenodd"
    />
    {/* Teeth — 9 rectangular bumps along the outer edge, spanning ~300° */}
    {/* Using rotated rectangles around center (50,50), skipping the right 60° gap */}
    {[45, 77, 109, 141, 173, 205, 237, 269, 301].map((deg) => {
      const rad = (deg * Math.PI) / 180
      const cx = 50 + 42 * Math.cos(rad)
      const cy = 50 + 42 * Math.sin(rad)
      return (
        <rect
          key={deg}
          x={cx - 5}
          y={cy - 5}
          width="10"
          height="14"
          rx="2"
          fill="#e04f35"
          transform={`rotate(${deg + 90}, ${cx}, ${cy})`}
        />
      )
    })}
    {/* Inner circle cutout */}
    <circle cx="50" cy="50" r="18" fill="var(--bg)" />
  </svg>
)

const Header: React.FC = () => {
  const { messages, isBusy, cancelJob, clearMessages } = useChatStore()
  const location = useLocation()
  const isChatPage = location.pathname === '/'

  return (
    <div className={styles.header}>
      <div className={styles.left}>
        <TechGearIcon />
        <span className={styles.title}>News Digest</span>
        {isChatPage && isBusy && <Badge label="live" variant="live" pulse />}
      </div>

      <div className={styles.center}>
        <NavTabs />
      </div>

      <div className={styles.right}>
        {isChatPage && isBusy && (
          <Button variant="danger" size="sm" onClick={cancelJob} title="Cancel current job">
            ⏹ Stop
          </Button>
        )}
        {isChatPage && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearMessages}
            disabled={messages.length === 0 || isBusy}
            title="Clear chat"
          >
            Clear
          </Button>
        )}
      </div>
    </div>
  )
}

export default Header
