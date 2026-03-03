import React from 'react'
import Header from './Header'
import ChatContainer from '../Chat/ChatContainer'
import StatusLog from '../Status/StatusLog'
import LetterGlitch from '../common/LetterGlitch'
import styles from './AppLayout.module.css'

interface AppLayoutProps {
  /** Override the main content area (defaults to ChatContainer + StatusLog) */
  centerContent?: React.ReactNode
}

const AppLayout: React.FC<AppLayoutProps> = ({ centerContent }) => (
  <div className={styles.layout}>
    {/* Left glitch panel */}
    <div className={styles.sidebar}>
      <LetterGlitch
        glitchColors={['#2c1a0e', '#7c4a1e', '#c8956c']}
        glitchSpeed={50}
        centerVignette={true}
        outerVignette={false}
        smooth={true}
      />
    </div>

    {/* Main pane */}
    <div className={styles.pane}>
      <Header />
      {centerContent ?? (
        <>
          <ChatContainer />
          <StatusLog />
        </>
      )}
    </div>

    {/* Right glitch panel */}
    <div className={styles.sidebar}>
      <LetterGlitch
        glitchColors={['#2c1a0e', '#7c4a1e', '#c8956c']}
        glitchSpeed={50}
        centerVignette={true}
        outerVignette={false}
        smooth={true}
      />
    </div>
  </div>
)

export default AppLayout
