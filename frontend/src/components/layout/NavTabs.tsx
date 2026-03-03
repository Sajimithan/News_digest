import React from 'react'
import { NavLink } from 'react-router-dom'
import styles from './NavTabs.module.css'

// Tech-news icon (gear outline)
const TechIcon = () => (
  <svg viewBox="0 0 18 18" width="13" height="13" fill="none" stroke="currentColor"
       strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="9" cy="9" r="2.5" />
    <path d="M9 1v2m0 12v2M1 9h2m12 0h2M3.22 3.22l1.42 1.42m8.72 8.72 1.42 1.42M3.22 14.78l1.42-1.42m8.72-8.72 1.42-1.42" />
  </svg>
)

// Market/chart icon
const MarketIcon = () => (
  <svg viewBox="0 0 18 18" width="13" height="13" fill="none" stroke="currentColor"
       strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <polyline points="1,14 6,8 10,11 17,3" />
    <polyline points="13,3 17,3 17,7" />
  </svg>
)

const NavTabs: React.FC = () => (
  <nav className={styles.nav} aria-label="Section navigation">
    <NavLink
      to="/"
      end
      className={({ isActive }) => `${styles.tab} ${isActive ? styles.active : ''}`}
    >
      <TechIcon />
      Tech News
    </NavLink>
    <NavLink
      to="/market"
      className={({ isActive }) => `${styles.tab} ${isActive ? styles.active : ''}`}
    >
      <MarketIcon />
      Market Intel
    </NavLink>
  </nav>
)

export default NavTabs
