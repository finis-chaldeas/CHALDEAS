/**
 * MainLayout - 3-column layout for CHALDEAS
 *
 * Structure:
 * - Navigator (280px): Entity tabs and lists
 * - Globe (flex): 3D globe with timeline
 * - StoryPanel (400px): Story/detail view
 */
import { ReactNode } from 'react'

interface MainLayoutProps {
  header: ReactNode
  navigator: ReactNode
  globe: ReactNode
  timeline: ReactNode
  storyPanel: ReactNode
  chat?: ReactNode
}

export function MainLayout({
  header,
  navigator,
  globe,
  timeline,
  storyPanel,
  chat
}: MainLayoutProps) {
  return (
    <div className="main-layout">
      {/* Header */}
      <header className="main-header">
        {header}
      </header>

      {/* Main Content Area */}
      <div className="main-content">
        {/* Left: Navigator */}
        <aside className="navigator-panel">
          {navigator}
        </aside>

        {/* Center: Globe + Timeline */}
        <main className="globe-panel">
          <div className="globe-container">
            {globe}
          </div>
          <div className="timeline-container">
            {timeline}
          </div>
        </main>

        {/* Right: Story Panel */}
        <aside className="story-panel">
          {storyPanel}
        </aside>
      </div>

      {/* Floating Chat */}
      {chat}
    </div>
  )
}

export default MainLayout
